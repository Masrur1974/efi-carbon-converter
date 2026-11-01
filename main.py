import hashlib
import time
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="EFI Carbon Fractionator Protocol API",
    version="1.0.0",
    description="Asynchronous Microservice MVP for real-time fiat-to-CO2 fractional conversion under IFRS S2 compliance frameworks."
)

# 1. FIXED MOCK COEFFICIENTS FOR MVP VALIDATION (TS Section 3.4)
EUA_QUOTA_PRICE_EUR = Decimal("86.00")
TJS_TO_EUR_CROSS_RATE = Decimal("0.08734")

# 2. IMMUTABLE APPEND-ONLY DATABASE LEDGER LAYER (TS Section 4.2)
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

# 3. DATA SCHEMA VALIDATION MODELS (TS Section 5.1)
class ContributionRequest(BaseModel):
    transaction_id: str = Field(..., example="TX-2026-9913-AF")
    contribution_amount: float = Field(..., gt=0, example=0.45)
    currency: str = Field("TJS", example="TJS")
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

# 4. CORE COMPUTATIONAL ROUTING ENGINE
@app.post(
    "/api/v1/verify-contribution",
    response_model=ContributionResponse,
    status_code=status.HTTP_200_OK,
    summary="Process Fiat Micro-Liquidity into Fractionated CO2 Mass"
)
async def verify_contribution(request: ContributionRequest):
    # Idempotency Verification to block double-counting (TS Section 4.2)
    if db_repository.is_duplicate(request.transaction_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transaction double-counting prevented. Duplicate ID detected."
        )

    # Convert floating primitive inputs into high-precision Decimal types
    amount_tjs = Decimal(str(request.contribution_amount))
    
    # Multi-Currency Routing: TJS -> EUR (TS Section 3.2)
    amount_eur = amount_tjs * TJS_TO_EUR_CROSS_RATE
    
    # Fractional Carbon Mass Calculation: (EUR / Spot Price) * 1000 kg (TS Section 3.3)
    carbon_mass_raw = (amount_eur / EUA_QUOTA_PRICE_EUR) * Decimal("1000")
    
    # High-precision database ledger rounding (6 decimals)
    carbon_mass_db = carbon_mass_raw.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    
    # Clean user interface rounding layout (2 decimals)
    carbon_mass_ui = carbon_mass_raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Simulated Redis cumulative accounting buffer tracked by MCC codes
    user_id = request.merchant_category_code
    total_buffer = db_repository.update_buffer(user_id, carbon_mass_db)

    # SHA-256 Audit Trail Cryptographic Hash Generation (TS Section 4.1)
    timestamp_nonce = str(int(time.time_ns()))
    hash_payload = f"{request.transaction_id}|{request.merchant_category_code}|{carbon_mass_db}|{timestamp_nonce}"
    blockchain_hash = hashlib.sha256(hash_payload.encode('utf-8')).hexdigest()

    # Audit-compliant Localized Interface Notification Generation (TS Section 5.2)
    if total_buffer < Decimal("1.00"):
        user_notification = f"Your transaction change of {request.contribution_amount} TJS has been recorded. Capital is accumulating toward the target threshold of 1.00 kg CO2. Progress updated in-app."
    else:
        user_notification = "First 1.00 kg of CO2 successfully verified and sequestered! Your cumulative fractional change has completed physical carbon extraction under IFRS S2 standards. Background aggregation remains active."

    # Commit record to Append-Only localized engine memory
    tx_record = {
        "id": request.transaction_id,
        "impact_kg": float(carbon_mass_db),
        "hash": blockchain_hash
    }
    db_repository.save_transaction(request.transaction_id, tx_record)

    return ContributionResponse(
        transaction_id=request.transaction_id,
        physical_impact_kg=float(carbon_mass_ui),
        blockchain_hash=blockchain_hash,
        user_notification=user_notification
    )
