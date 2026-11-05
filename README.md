# EFI Carbon Converter Engine — Prototype

A small FastAPI prototype that converts a positive contribution amount in a currency supported by an exchange-rate provider into a **price-based estimate** of carbon-equivalent mass.

> **Important — prototype only:** This application does not receive or hold money, simulate or execute an offset purchase, retire a credit, establish ownership for a donor, write to a blockchain, or connect to UNFCCC, UNICC, The Atrium, or an external carbon registry. The API calculates an estimate, stores transaction data temporarily in process memory, and creates a local SHA-256 digest. The digest is not a blockchain transaction or proof of a real-world purchase.

## What the code currently does

- Exposes exactly two HTTP endpoints:
  - `GET /api/v1/currencies` — fetches currency codes from the configured exchange-rate provider.
  - `POST /api/v1/verify-contribution` — validates a contribution request, converts its amount to EUR, estimates a CO2-equivalent mass, calculates a local SHA-256 digest, stores the result in process memory, and returns JSON.
- Fetches USD-based foreign-exchange rates from `FX_RATES_URL` (default: `https://open.er-api.com/v6/latest/USD`) and caches them for `FX_CACHE_TTL_SECONDS` (default: `3600` seconds).
- Uses `86.00 EUR per tonne` as a fixed illustrative input. It is not a live carbon-market quote and is not connected to a specific offset project or supplier.
- Uses `Decimal` for the conversion after parsing the request amount, rounds stored estimated mass to six decimal places, and returns the displayed `physical_impact_kg` rounded to two decimal places.
- Rejects a transaction ID already seen by the current application process with HTTP 409.

The estimate is calculated as:

```text
estimated_kg = (contribution_amount × EUR_per_currency_unit / 86.00 EUR_per_tonne) × 1,000 kg_per_tonne
```

This is only a price-based estimate. It does not measure a project's climate impact or prove that the corresponding quantity exists as a credit.

## API endpoints and exact response shapes

Interactive OpenAPI documentation is available at `/docs` when the service is running.

### `GET /api/v1/currencies`

Returns currencies listed by the configured provider (plus USD and EUR where applicable):

```json
{
  "base": "USD",
  "currencies": ["EUR", "TJS", "USD"]
}
```

If the rate provider is unavailable or returns invalid data, the API responds with HTTP 503:

```json
{
  "detail": "Exchange rates are temporarily unavailable. Please try again."
}
```

### `POST /api/v1/verify-contribution`

Example request:

```json
{
  "transaction_id": "TX-EXAMPLE-001",
  "contribution_amount": 0.45,
  "currency": "TJS",
  "merchant_category_code": "5411",
  "timestamp": "2026-10-22T04:15:00Z"
}
```

`contribution_amount` must be greater than zero. `currency` must be a three-letter code supported by the configured exchange-rate provider. `transaction_id`, `merchant_category_code`, and `timestamp` are required strings. The timestamp is accepted but is not used to calculate the result. The request has no donor/customer identifier, region, or offset-category selection.

Successful responses have this shape. The values below are illustrative; the hash is newly computed for each request and the exchange rate may change:

```json
{
  "status": "verified_and_retired",
  "transaction_id": "TX-EXAMPLE-001",
  "allocated_project": "ICE_EUA_Compliance_Dec2026",
  "physical_impact_kg": 0.46,
  "blockchain_hash": "<64-character SHA-256 digest>",
  "verification_node": "EFI-Local-Core-Node-01",
  "un_atrium_mirror_status": "ready_for_sync",
  "metadata": {
    "accounting_protocol": "IFRS S2 / ESG Compliant",
    "operation_type": "Carbon Removal"
  },
  "user_notification": "Your transaction change of 0.45 TJS has been recorded. Capital is accumulating toward the target threshold of 1.00 kg CO2. Progress updated in-app."
}
```

**The response fields `status`, `allocated_project`, `verification_node`, `un_atrium_mirror_status`, and `metadata` are hard-coded labels, not verified facts.** In particular, `verified_and_retired` does not mean that a credit was verified or retired, and `ready_for_sync` does not mean that any Atrium sync is configured. The generated `blockchain_hash` is a local digest only.

Possible error responses:

- **409 Conflict** — duplicate transaction ID encountered in this running process:

  ```json
  {"detail": "Transaction double-counting prevented. Duplicate ID detected."}
  ```

- **422 Unprocessable Entity** — invalid request data, invalid currency code, or a currency unsupported by the provider. FastAPI/Pydantic validation errors may have FastAPI's standard validation-error response shape.
- **503 Service Unavailable** — exchange-rate provider unavailable or response invalid:

  ```json
  {"detail": "Exchange rates are temporarily unavailable. Please try again."}
  ```

## Current storage and security limitations

- Transaction records and cumulative buffers are held in process memory only. They are lost when the process restarts and are not shared across multiple application workers or instances.
- Duplicate-ID checking is not backed by a durable database or distributed idempotency mechanism; it is not production-grade protection against concurrent or cross-instance duplicates.
- The cumulative buffer is keyed by `merchant_category_code`, not by a donor/customer.
- The SHA-256 digest is generated locally from the transaction ID, merchant category code, internally rounded estimate, and a time-based nonce. It is not submitted to a blockchain or external ledger and does not prove a payment, purchase, or climate outcome.
- The transaction ID is included directly in the hash input; this implementation does not anonymize it.
- This prototype is not production-ready for handling customer funds or making environmental claims.

## Not implemented

The following are not implemented in this repository:

- Payment collection, custody, escrow, refunds, or customer-specific money balances.
- Durable customer and transaction ledgers.
- Region- or offset-category-specific pricing and configurable regional/category pools.
- Live project-specific carbon-credit quotes, supplier selection, purchase orders, payment, or settlement.
- Registry issuance, transfer, cancellation, or retirement of credits.
- Fractional allocation of a purchased/retired batch to individual customers.
- Blockchain transactions, smart contracts, Merkle proofs, or public audit records.
- UNICC or The Atrium integrations.
- UNFCCC Article 6.2 or Article 6.4 authorization, corresponding adjustments, or registry integration.
- Verification of IFRS S2, ESG, or other regulatory compliance.

A future implementation should clearly distinguish an estimate, a contribution actually received, credits actually purchased, registry retirement confirmed, and a customer's share allocated. Do not claim UN, IFC, FAO, World Bank, EBRD, Atrium, or blockchain participation unless it is formally documented and independently verifiable.

## Run locally

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the API:

```bash
uvicorn main:app --reload
```

Interactive API documentation: `http://127.0.0.1:8000/docs`.

Run tests:

```bash
pytest -q
```

The tests mock exchange rates for deterministic conversion checks; they do not test live offset-market pricing, carbon-credit purchases, registry retirement, or blockchain behavior.

## Configuration

- `FX_RATES_URL`: exchange-rate provider URL (default: `https://open.er-api.com/v6/latest/USD`).
- `FX_CACHE_TTL_SECONDS`: exchange-rate cache duration in seconds (default: `3600`).

## Repository contents

- `main.py` — FastAPI application and prototype calculations.
- `test_main.py` — API tests using mocked exchange rates.
- `requirements.txt` — Python dependencies.

## License

MIT. See [`LICENSE`](LICENSE).
