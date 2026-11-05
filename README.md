# EFI Carbon Converter Engine — Prototype

A small FastAPI **simulation prototype** for modeling small charitable contributions, currency conversion, estimated carbon-offset allocation, threshold batching, and a local hash-chained audit trail.

> **Simulation only:** The application does not receive or hold money, execute a real carbon-credit purchase or retirement, establish legal ownership, write to a public or permissioned blockchain, or connect to UNFCCC, UNICC, The Atrium, or an external carbon registry. A simulated batch and local SHA-256 hash are demonstrations, not proof of a real-world transaction or climate outcome.

## What the prototype does

- `GET /api/v1/currencies` lists the currency codes supplied by the configured exchange-rate provider.
- `POST /api/v1/verify-contribution` accepts a contribution and donor, region, and offset-category identifiers; converts the amount to EUR; estimates a CO2-equivalent amount; adds it to the matching in-memory region/category pool; and creates a local hash-chained ledger record.
- When a region/category pool reaches the illustrative `1.000000 kg CO2e` threshold, the prototype creates a simulated batch, reports donor-level estimated allocations, and resets that pool's pending amount.
- Uses `Decimal` for monetary and mass calculations and rounds accounting values to six decimal places using `ROUND_HALF_UP`. A user interface can independently display currencies at their normal minor-unit precision (often two decimals).
- Uses a fixed illustrative price of `86.00 EUR per tonne CO2e`. This is not a live quote and is not associated with a real supplier, project, credit, or market purchase.
- Rejects duplicate transaction IDs within the current running process with HTTP 409.

### Calculation

```text
amount_eur = contribution_amount × EUR_per_currency_unit
estimated_kg = (amount_eur / 86.00 EUR_per_tonne) × 1,000 kg_per_tonne
```

The amount in EUR and estimated mass are each rounded to six decimal places before the pool is updated. The result is a price-based estimate, not a measurement or proof that an offset credit exists.

## API

Interactive OpenAPI documentation is available at `/docs` when the service is running.

### `GET /api/v1/currencies`

Example response:

```json
{
  "base": "USD",
  "currencies": ["EUR", "TJS", "USD"]
}
```

The exact currency list depends on the configured provider. This does not support every currency in the world; a currency must be present in the provider response. Provider failure returns HTTP 503.

### `POST /api/v1/verify-contribution`

Example request:

```json
{
  "transaction_id": "TX-EXAMPLE-001",
  "contribution_amount": "0.45",
  "currency": "TJS",
  "merchant_category_code": "5411",
  "timestamp": "2026-10-22T04:15:00Z",
  "donor_id": "donor-001",
  "region": "TJ",
  "offset_category": "RENEWABLE_ENERGY"
}
```

Required fields are `transaction_id`, positive `contribution_amount`, three-letter `currency`, `merchant_category_code`, and `timestamp`. `donor_id`, `region`, and `offset_category` have defaults, but should be supplied for a meaningful demonstration. Regions and offset categories are accepted as labels; the prototype does not validate them against an authoritative catalog or apply different prices by region/category.

Example successful response (values are illustrative; numeric `Decimal` values are serialized as strings):

```json
{
  "status": "simulated_contribution_recorded",
  "transaction_id": "TX-EXAMPLE-001",
  "allocated_project": "SIMULATED:TJ:RENEWABLE_ENERGY",
  "physical_impact_kg": "0.457012",
  "blockchain_hash": "<64-character local SHA-256 digest>",
  "verification_node": "EFI-LOCAL-SIMULATION-NODE",
  "un_atrium_mirror_status": "NOT_CONNECTED_SIMULATION_ONLY",
  "metadata": {
    "accounting_protocol": "Illustrative simulation; no compliance claim",
    "operation_type": "Simulated carbon-offset allocation"
  },
  "user_notification": "Simulation only: ... No money was spent and no real offset was purchased or retired.",
  "simulation_only": true,
  "simulated_purchase_batch_id": null,
  "simulated_purchase_kg": "0.000000",
  "pool_kg_remaining": "0.457012",
  "amount_eur": "0.039303",
  "currency": "TJS",
  "region": "TJ",
  "offset_category": "RENEWABLE_ENERGY",
  "donor_id": "donor-001"
}
```

If a pool reaches the threshold, `status` becomes `simulated_purchase_threshold_reached`, `simulated_purchase_batch_id` is populated (for example, `SIM-BATCH-000001`), and `simulated_purchase_kg` reports the batch amount. This is still only a simulated batch: no money is spent and no credit is purchased or retired. The batch groups estimates by region and category and includes donor allocation data internally; it does not create legal ownership.

Error responses:

- **409 Conflict** — duplicate transaction ID in this running process:

  ```json
  {"detail": "Duplicate transaction ID; contribution was not recorded again."}
  ```
- **422 Unprocessable Entity** — invalid request or unsupported currency.
- **503 Service Unavailable** — exchange-rate provider unavailable or response invalid:

  ```json
  {"detail": "Exchange rates are temporarily unavailable. Please try again."}
  ```

## Hash-chain behavior and limitations

Each simulated contribution is serialized in a stable form and hashed with SHA-256. A record includes the previous record's hash, creating a **local hash chain** for demonstration. It is not a blockchain: it has no network consensus, external validators, independent permanence, or public transaction ID. Records and pools are held in process memory, so they disappear on restart and are not shared by multiple workers or instances. The in-process lock and duplicate check are not production-grade, durable idempotency controls.

The hash is an integrity-oriented demonstration, not proof that the submitted contribution was paid, that an offset was bought, or that a climate claim is valid. Do not describe the simulated batch as an actual purchase, retirement, verified impact, or customer-owned financial asset.

## Not implemented

- Real donations, payment collection, custody, escrow, refunds, or customer balances.
- Persistent database storage, production idempotency, authentication, or access control.
- Live market quotes, supplier selection, orders, settlement, or purchase of credits.
- External registries, issuance, transfer, retirement/cancellation, or legal ownership allocation.
- Blockchain transactions, smart contracts, Merkle proofs, or Atrium/UNICC integration.
- Verified project-specific impact, IFRS S2/ESG compliance, or regulatory approvals.
- Region/category catalogs or region/category-specific market prices.

## Run locally

```bash
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` to explore the API. Run tests with:

```bash
pytest -q
```

## Configuration

- `FX_RATES_URL`: exchange-rate provider URL (default: `https://open.er-api.com/v6/latest/USD`).
- `FX_CACHE_TTL_SECONDS`: rate-cache lifetime in seconds (default: `3600`).

## License

MIT. See [`LICENSE`](LICENSE).
