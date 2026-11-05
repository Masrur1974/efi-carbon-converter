# EFI Carbon Converter Engine — Prototype

A small FastAPI prototype that converts a positive contribution amount in a provider-supported currency into an estimated carbon-equivalent mass using an exchange rate and a fixed, illustrative baseline.

> **Prototype limitations:** This repository does not receive or hold money, purchase carbon credits, retire credits in a registry, write to a blockchain, or connect to UNFCCC, UNICC, The Atrium, VCS registries, or to any live institutional partner.

## Conceptual status and governance note

The repository includes a methodological note describing a broader ecosystem architecture for climate-finance participation, eco-point accounting, and funding allocation. That document is a conceptual design proposal rather than evidence of an existing implementation, partnership, or regulatory authorization.

The referenced organizations and frameworks (including UNFCCC, IFC, FAO, UN agencies, IFIs, and blockchain-related infrastructure) are discussed as potential governance, auditing, or operational reference points for a future system. At present, this repository alone does not establish any legal, institutional, financial, or audit relationship with those institutions.

Any future production deployment should be preceded by:

- signed and documented agreements with regulators, banks, and counterparties;
- independent environmental and financial auditing;
- explicit custody, escrow, and allocation controls for funds;
- verifiable carbon-credit procurement, retirement, and registry procedures;
- a clear separation between estimates, verified impacts, purchased credits, and customer-level allocations.

This distinction is essential to avoid greenwashing claims, double counting, or overstating the maturity of the system.

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

`contribution_amount` must be greater than zero. `currency` is a three-character code and must be supported by the configured exchange-rate provider. `transaction_id`, `merchant_category_code`, and `timestamp` are validated in the request model.

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

**Important:** Several response fields above are constants in the current code, not verified facts. In particular, `verified_and_retired`, `allocated_project`, `verification_node`, `un_atrium_mirror_status`, and the metadata fields are illustrative and not validated against a real registry or external system.

The notification threshold is based on an in-memory cumulative estimate keyed by `merchant_category_code`, not by an individual user. The request model does not include a user identifier.

## Current storage and security limitations

- Transaction records and cumulative buffers are held in process memory only. They are lost when the process restarts and are not shared across multiple application workers or instances.
- The duplicate-ID check is not backed by a durable database or a distributed idempotency mechanism.
- The cumulative buffer is grouped by merchant category code (MCC), not by customer.
- The SHA-256 digest is generated locally from the transaction ID, MCC, internally rounded estimate, and a time-based nonce. It is not submitted to a blockchain or external ledger and does not provide proof of a real transaction or external registry action.
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

Any future integration should distinguish clearly between an estimate, a contribution recorded, credits purchased, registry retirement confirmed, and a customer's share allocated. Avoid claiming UN, IFC, FAO, World Bank, EBRD, or blockchain participation unless such participation is formally documented and independently verifiable.

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
