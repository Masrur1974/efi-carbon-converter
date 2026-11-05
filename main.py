import asyncio
import hashlib
import json
import os
import re
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="EFI Carbon Fractionator Protocol API",
    version="1.1.0",
    description=(
        "Simulation API for recording contributions, estimating carbon-offset amounts, "
        "and creating a local hash-chained audit trail. No real purchase or blockchain write occurs."
    ),
)

# Illustrative simulation price only, not a live quote or an executed market purchase.
EUA_QUOTA_PRICE_EUR = Decimal("86.00")  # EUR per tonne of CO2e
PURCHASE_THRESHOLD_KG = Decimal("1.000000")
SIX_PLACES = Decimal("0.000001")
FX_RATES_URL = os.getenv("FX_RATES_URL", "https://open.er-api.com/v6/latest/USD")
FX_CACHE_TTL_SECONDS = int(os.getenv("FX_CACHE_TTL_SECONDS", "3600"))
_fx_rates_cache: Optional[Tuple[float, Dict[str, Decimal]]] = None
_fx_rates_lock = asyncio.Lock()


def six_places(value: Decimal) -> Decimal:
    """Quantize ledger values to six decimal places using round-half-up."""
    return value.quantize(SIX_PLACES, rounding=ROUND_HALF_UP)


class InMemoryAppendOnlyRepository:
    """Process-local simulation ledger; data disappears when the process restarts."""

    def __init__(self):
        self._transactions: Dict[str, dict] = {}
        self._pools: Dict[Tuple[str, str], dict] = {}
        self._batches: List[dict] = []
        self._chain: List[dict] = []
        self._lock = asyncio.Lock()

    async def record_contribution(self, tx_id: str, record: dict, threshold_kg: Decimal) -> dict:
        # Atomic duplicate protection and ledger/pool update within this process.
        async with self._lock:
            if tx_id in self._transactions:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Duplicate transaction ID; contribution was not recorded again.",
                )

            pool_key = (record["region"], record["offset_category"])
            pool = self._pools.setdefault(
                pool_key,
                {"kg": Decimal("0.000000"), "donor_allocations": {}, "contribution_count": 0},
            )
            pool["kg"] = six_places(pool["kg"] + record["estimated_offset_kg"])
            donor_id = record["donor_id"]
            pool["donor_allocations"][donor_id] = six_places(
                pool["donor_allocations"].get(donor_id, Decimal("0.000000"))
                + record["estimated_offset_kg"]
            )
            pool["contribution_count"] += 1

            purchase_batch = None
            if pool["kg"] >= threshold_kg:
                purchase_batch = {
                    "batch_id": f"SIM-BATCH-{len(self._batches) + 1:06d}",
                    "region": pool_key[0],
                    "offset_category": pool_key[1],
                    "simulated_purchase_kg": pool["kg"],
                    "donor_allocations_kg": dict(pool["donor_allocations"]),
                    "contribution_count": pool["contribution_count"],
                    "status": "SIMULATED_ONLY_NOT_A_REAL_PURCHASE",
                }
                self._batches.append(purchase_batch)
                pool["kg"] = Decimal("0.000000")
                pool["donor_allocations"] = {}
                pool["contribution_count"] = 0

            chain_record = {
                **record,
                "simulated_purchase_batch_id": purchase_batch["batch_id"] if purchase_batch else None,
                "previous_hash": self._chain[-1]["record_hash"] if self._chain else None,
            }
            canonical = json.dumps(chain_record, sort_keys=True, separators=(",", ":"))
            chain_record["record_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            chain_record["ledger_index"] = len(self._chain) + 1
            self._chain.append(chain_record)

            result = {
                "record_hash": chain_record["record_hash"],
                "ledger_index": chain_record["ledger_index"],
                "pool_kg_remaining": pool["kg"],
                "purchase_batch": purchase_batch,
            }
            self._transactions[tx_id] = {**record, **result}
            return result


db_repository = InMemoryAppendOnlyRepository()


class ContributionRequest(BaseModel):
    transaction_id: str = Field(..., min_length=1, example="TX-2026-9913-AF")
    # Decimal input avoids binary floating-point arithmetic for monetary values.
    contribution_amount: Decimal = Field(..., gt=0, example="0.45")
    currency: str = Field("TJS", min_length=3, max_length=3, example="TJS")
    merchant_category_code: str = Field(..., example="5411")
    timestamp: str = Field(..., example="2026-10-22T04:15:00Z")
    donor_id: str = Field("anonymous", min_length=1, max_length=128, example="donor-001")
    region: str = Field("GLOBAL", min_length=2, max_length=32, example="TJ")
    offset_category: str = Field("GENERAL", min_length=2, max_length=64, example="RENEWABLE_ENERGY")


class MetadataBlock(BaseModel):
    accounting_protocol: str = "Illustrative simulation; no compliance claim"
    operation_type: str = "Simulated carbon-offset allocation"


class ContributionResponse(BaseModel):
    status: str
    transaction_id: str
    allocated_project: str
    physical_impact_kg: Decimal
    blockchain_hash: str
    verification_node: str
    un_atrium_mirror_status: str
    metadata: MetadataBlock
    user_notification: str
    simulation_only: bool
    simulated_purchase_batch_id: Optional[str] = None
    simulated_purchase_kg: Decimal = Decimal("0.000000")
    pool_kg_remaining: Decimal
    amount_eur: Decimal
    currency: str
    region: str
    offset_category: str
    donor_id: str


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
            rates.setdefault("USD", Decimal("1"))
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
    summary="Simulate a contribution, offset accumulation, purchase threshold, and hash-chained record",
)
async def verify_contribution(request: ContributionRequest):
    currency_code = request.currency.upper()
    eur_per_unit = await get_eur_per_unit(currency_code)

    # Monetary values and carbon estimates are quantized to six decimal places.
    amount = six_places(request.contribution_amount)
    amount_eur = six_places(amount * eur_per_unit)
    # kg CO2e = EUR / (EUR per tonne) * 1,000 kg per tonne.
    estimated_offset_kg = six_places((amount_eur / EUA_QUOTA_PRICE_EUR) * Decimal("1000"))

    record = {
        "transaction_id": request.transaction_id,
        "donor_id": request.donor_id,
        "merchant_category_code": request.merchant_category_code,
        "contribution_amount": amount,
        "currency": currency_code,
        "amount_eur": amount_eur,
        "region": request.region.upper(),
        "offset_category": request.offset_category.upper(),
        "timestamp": request.timestamp,
        "estimated_offset_kg": estimated_offset_kg,
        "reference_price_eur_per_tonne": EUA_QUOTA_PRICE_EUR,
        "simulation_only": True,
    }
    ledger_result = await db_repository.record_contribution(
        request.transaction_id, record, PURCHASE_THRESHOLD_KG
    )

    batch = ledger_result["purchase_batch"]
    if batch:
        status_text = "simulated_purchase_threshold_reached"
        notification = (
            f"Simulation only: the {request.region.upper()}/{request.offset_category.upper()} pool reached "
            f"{batch['simulated_purchase_kg']:.6f} kg CO2e. A simulated batch was recorded; "
            "no money was spent and no real offset was purchased or retired."
        )
        batch_id = batch["batch_id"]
        batch_kg = batch["simulated_purchase_kg"]
    else:
        status_text = "simulated_contribution_recorded"
        notification = (
            f"Simulation only: {amount:.6f} {currency_code} was recorded as EUR {amount_eur:.6f}, "
            f"equivalent to an estimated {estimated_offset_kg:.6f} kg CO2e at the illustrative price. "
            f"The {request.region.upper()}/{request.offset_category.upper()} pool has "
            f"{ledger_result['pool_kg_remaining']:.6f} kg toward the {PURCHASE_THRESHOLD_KG:.6f} kg threshold. "
            "No money was spent and no real offset was purchased or retired."
        )
        batch_id = None
        batch_kg = Decimal("0.000000")

    return ContributionResponse(
        status=status_text,
        transaction_id=request.transaction_id,
        allocated_project=f"SIMULATED:{request.region.upper()}:{request.offset_category.upper()}",
        physical_impact_kg=estimated_offset_kg,
        blockchain_hash=ledger_result["record_hash"],
        verification_node="EFI-LOCAL-SIMULATION-NODE",
        un_atrium_mirror_status="NOT_CONNECTED_SIMULATION_ONLY",
        metadata=MetadataBlock(),
        user_notification=notification,
        simulation_only=True,
        simulated_purchase_batch_id=batch_id,
        simulated_purchase_kg=batch_kg,
        pool_kg_remaining=ledger_result["pool_kg_remaining"],
        amount_eur=amount_eur,
        currency=currency_code,
        region=request.region.upper(),
        offset_category=request.offset_category.upper(),
        donor_id=request.donor_id,
    )


__all__ = ["app"]
