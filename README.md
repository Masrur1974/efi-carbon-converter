# EFI Carbon Converter Engine — Prototype

A small FastAPI prototype that converts a positive contribution amount in a provider-supported currency into an **estimated** carbon-equivalent mass using an exchange rate and a fixed, illustrative carbon price.

> **Prototype limitations:** This repository does not receive or hold money, purchase carbon credits, retire credits in a registry, write to a blockchain, or connect to UNFCCC, UNICC, The Atrium, Verra, Gold Standard, or any other carbon registry or marketplace. A calculated value is an estimate only; it is not evidence that emissions were reduced, removed, compensated, or that a carbon credit was purchased or retired.

## What the code currently does

- Exposes a FastAPI application with two endpoints:
  - `GET /api/v1/currencies` fetches supported currency codes from the configured exchange-rate provider.
  - `POST /api/v1/verify-contribution` validates a contribution request, converts its amount to EUR, estimates a CO₂-equivalent mass, calculates a SHA-256 digest, and returns a JSON response.
- Fetches USD-based foreign-exchange rates from `FX_RATES_URL` (default: `https://open.er-api.com/v6/latest/USD`) and caches them for `FX_CACHE_TTL_SECONDS` (default: 3600 seconds).
- Uses `86.00 EUR per tonne` as a fixed illustrative input (`EUA_QUOTA_PRICE_EUR`). This is **not** a live carbon-market quote and is not connected to a specific offset project or supplier.
- Rounds the internal mass value to six decimal places and the API's displayed `physical_impact_kg` value to two decimal places.
- Rejects a transaction ID already seen by the current application process with HTTP 409.

The conversion is:

```text
estimated_kg = (contribution_amount × EUR_per_currency_unit / 86.00 EUR_per_tonne) × 1,000 kg_per_tonne
```

This calculation is only a price-based estimate. It does not measure a project's climate impact or prove that the corresponding quantity exists as a credit.

## API

### `GET /api/v1/currencies`

Returns the currency codes in the configured provider response, with USD as the base currency. If the provider is unavailable, the endpoint returns HTTP 503.

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

`contribution_amount` must be greater than zero. `currency` is a three-character code and must be supported by the configured exchange-rate provider. `transaction_id`, `merchant_category_code`, and `timestamp` are required strings. The timestamp is accepted but is not used to determine the exchange rate or carbon estimate.

A successful request returns a response shaped like:

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
  "user_notification": "..."
}
```

**Important:** Several response fields above are constants in the current code, not verified facts. In particular, `verified_and_retired`, `allocated_project`, `verification_node`, `un_atrium_mirror_status`, and the accounting metadata do not represent a registry operation, project allocation, institutional verification, blockchain transaction, or demonstrated compliance. `physical_impact_kg` is a formula-based estimate, not a measured physical impact. Do not use this response as proof of offsetting or retirement.

The notification threshold is based on an in-memory cumulative estimate keyed by `merchant_category_code`, not by an individual user. The request model does not include a user identifier.

## Current storage and security limitations

- Transaction records and cumulative buffers are held in process memory only. They are lost when the process restarts and are not shared across multiple application workers or instances.
- The duplicate-ID check is not backed by a durable database or a distributed idempotency mechanism.
- The cumulative buffer is grouped by merchant category code (MCC), not by customer.
- The SHA-256 digest is generated locally from the transaction ID, MCC, internally rounded estimate, and a time-based nonce. It is not submitted to a blockchain or external ledger and does not prove a purchase, retirement, or climate outcome.
- The transaction ID is included directly in the hash input; this implementation does not anonymize it.
- This prototype is not production-ready for handling customer funds or making environmental claims.

## Not implemented

The following are goals that would require additional design, integrations, and validation; they are not implemented in this repository:

- Payment collection, custody, escrow, refunds, or customer-specific money balances.
- Durable customer and transaction ledgers.
- Live project-specific carbon-credit quotes, supplier selection, purchase orders, or settlement.
- Registry issuance, transfer, cancellation, or retirement of credits.
- Fractional allocation of a retired batch to individual customers.
- UNFCCC Article 6.2 or Article 6.4 authorization, corresponding adjustments, or registry integration.
- Blockchain transactions, smart contracts, Merkle proofs, or public audit records.
- UNICC or The Atrium integrations.
- EFI Eco-Points, SDG priority coefficients, IFC behavioral scoring, or automated project routing.
- Verification of IFRS S2, ESG, or other regulatory compliance.

Any future integration should distinguish clearly between an estimate, a contribution recorded, credits purchased, registry retirement confirmed, and a customer's share allocated. Avoid claiming UNFCCC or other institutional endorsement unless formally established and verifiable.

## Run locally

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the API:

```bash
uvicorn main:app --reload
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

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
