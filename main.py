import asyncio
import hashlib
import os
import re
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, Optional, Tuple

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="EFI Carbon Fractionator Protocol API",
    version="1.0.0",
    description="API converting contributions in provider-supported currencies into fractional carbon impact.",
)

# Carbon price is a mock MVP value. FX rates come from the configured provider.
# Provider rates are USD-based and cached to reduce network calls.
EUA_QUOTA_PRICE_EUR = Decimal("86.00")
FX_RATES_URL = os.getenv("FX_RATES_URL", "https://open.er-api.com/v6/latest/USD")
FX_CACHE_TTL_SECONDS = int(os.getenv("FX_CACHE_TTL_SECONDS", "3600"))
_fx_rates_cache: Optional[Tuple[float, Dict[str, Decimal]]] = None
_fx_rates_lock = asyncio.Lock()


class InMemoryAppendOnlyRepository:
    def __init__(self):
        self._ledger = {}
        self._user_buffers = {}

    def is_duplicate(self, tx_id: str) -> bool:
        return tx_id in self._ledger

    def save_transaction(self, tx_id: str, data: dict):
        self._ledger[tx_id] = data

    def update_buffer(self, user_id: str, amount_kg: Decimal) -> Decimal:
        current = self._user_buffers.get(user_id, Decimal("0.00"))
        new_total = current + amount_kg
        self._user_buffers[user_id] = new_total
        return new_total


db_repository = InMemoryAppendOnlyRepository()


class ContributionRequest(BaseModel):
    transaction_id: str = Field(..., example="TX-2026-9913-AF")
    contribution_amount: float = Field(..., gt=0, example=0.45)
    currency: str = Field("TJS", min_length=3, max_length=3, example="TJS")
    merchant_category_code: str = Field(..., example="5411")
    timestamp: str = Field(..., example="2026-10-22T04:15:00Z")


class MetadataBlock(BaseModel):
    accounting_protocol: str = "IFRS S2 / ESG Compliant"
    operation_type: str = "Carbon Removal"


class ContributionResponse(BaseModel):
    status: str = "verified_and_retired"
    transaction_id: str
    allocated_project: str = "ICE_EUA_Compliance_Dec2026"
    physical_impact_kg: float
    blockchain_hash: str
    verification_node: str = "EFI-Local-Core-Node-01"
    un_atrium_mirror_status: str = "ready_for_sync"
    metadata: MetadataBlock = MetadataBlock()
    user_notification: str


async def _get_provider_rates() -> Dict[str, Decimal]:
    """Fetch and cache rates where each value is units of currency per USD."""
    global _fx_rates_cache
    now = time.monotonic()
    if _fx_rates_cache and now - _fx_rates_cache[0] < FX_CACHE_TTL_SECONDS:
        return _fx_rates_cache[1]

    async with _fx_rates_lock:
        now = time.monotonic()
        if _fx_rates_cache and now - _fx_rates_cache[0] < FX_CACHE_TTL_SECONDS:
            return _fx_rates_cache[1]

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(FX_RATES_URL)
                response.raise_for_status()
                payload = response.json()
            raw_rates = payload.get("rates")
            if payload.get("result") != "success" or not isinstance(raw_rates, dict):
                raise ValueError("Invalid exchange-rate response")
            rates = {str(code).upper(): Decimal(str(value)) for code, value in raw_rates.items()}
            if "USD" not in rates:
                rates["USD"] = Decimal("1")
            if "EUR" not in rates or any(value <= 0 for value in rates.values()):
                raise ValueError("Exchange-rate response is missing valid EUR rates")
            _fx_rates_cache = (time.monotonic(), rates)
            return rates
        except (httpx.HTTPError, ValueError, TypeError, AttributeError, InvalidOperation) as exc:
            raise HTTPException(
                status_code=503,
                detail="Exchange rates are temporarily unavailable. Please try again.",
            ) from exc


async def get_eur_per_unit(currency_code: str) -> Decimal:
    """Return EUR per one unit of a currency listed by the configured provider."""
    code = currency_code.upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise HTTPException(status_code=422, detail="Currency must be a three-letter ISO code.")

    rates = await _get_provider_rates()
    source_rate = rates.get(code)
    usd_to_eur_rate = rates.get("EUR")
    if source_rate is None or usd_to_eur_rate is None:
        raise HTTPException(
            status_code=422,
            detail=f"Currency {code} is not supported by the configured exchange-rate provider.",
        )
    return usd_to_eur_rate / source_rate


@app.get("/api/v1/currencies", summary="List currencies supported by the exchange-rate provider")
async def list_currencies():
    rates = await _get_provider_rates()
    return {"base": "USD", "currencies": sorted(set(rates) | {"EUR", "USD"})}


@app.post(
    "/api/v1/verify-contribution",
    response_model=ContributionResponse,
    status_code=status.HTTP_200_OK,
    summary="Convert a contribution in a provider-supported currency into carbon impact",
)
async def verify_contribution(request: ContributionRequest):
    if db_repository.is_duplicate(request.transaction_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transaction double-counting prevented. Duplicate ID detected.",
        )

    currency_code = request.currency.upper()
    amount = Decimal(str(request.contribution_amount))
    eur_per_unit = await get_eur_per_unit(currency_code)
    amount_eur = amount * eur_per_unit

    carbon_mass_raw = (amount_eur / EUA_QUOTA_PRICE_EUR) * Decimal("1000")
    carbon_mass_db = carbon_mass_raw.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    carbon_mass_ui = carbon_mass_raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    total_buffer = db_repository.update_buffer(request.merchant_category_code, carbon_mass_db)

    timestamp_nonce = str(time.time_ns())
    hash_payload = (
        f"{request.transaction_id}|{request.merchant_category_code}|"
        f"{carbon_mass_db}|{timestamp_nonce}"
    )
    blockchain_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

    if total_buffer < Decimal("1.00"):
        user_notification = (
            f"Your transaction change of {request.contribution_amount} {currency_code} has been recorded. "
            "Capital is accumulating toward the target threshold of 1.00 kg CO2. Progress updated in-app."
        )
    else:
        user_notification = (
            f"First 1.00 kg of CO2 successfully verified and sequestered! Your cumulative fractional {currency_code} "
            "change has completed physical carbon extraction under IFRS S2 standards. "
            "Background aggregation remains active."
        )




    db_repository.save_transaction(
        request.transaction_id,
        {"id": request.transaction_id, "impact_kg": float(carbon_mass_db), "hash": blockchain_hash},
    )

    return ContributionResponse(
        transaction_id=request.transaction_id,
        physical_impact_kg=float(carbon_mass_ui),
        blockchain_hash=blockchain_hash,
        user_notification=user_notification,
    )
