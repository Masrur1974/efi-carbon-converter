### Eco-Finance Infrastructure (EFI) Carbon Converter Engine

An open-source, production-grade microservice executing real-time fiat-to-carbon liquidation, asset normalization, and SHA-256 cryptographic fractional locking. This repository functions as a validated Digital Public Good blueprint ready for cross-border institutional scaling. 

### Strategic Overview

The EFI Carbon Converter Engine solves a structural bottleneck within the global Voluntary Carbon Market. Traditional climate registries process carbon credits exclusively in bulk wholesale lots (1 tCO2e), effectively locking out retail consumers and commercial banking micro-liquidity due to severe micro-accounting barriers. 

This protocol operates as a secure API infrastructure overlay. It aggregates fragmented retail residual change (such as financial round-ups) from day-to-day transactions and immediately fractionalizes it into verified physical climate mitigation metrics (kilograms of CO2) based on real-time spot pricing. 

### Core SDGs Aligned

* **SDG 2 (Zero Hunger) & SDG 15 (Life on Land):** Dynamic financial routing to glacier preservation, desertification mitigation, and smallholder farmer support.
* **SDG 11 (Sustainable Cities and Communities):** Automated retail-driven liquidity distribution for urban greening and eco-infrastructure overlays.
* **SDG 13 (Climate Action):** Mitigating cross-border environmental levies (such as EU CBAM compliance) via transparent, localized origin offsetting matrices.

### Mathematical Core & Methodology

The engine calculates physical environmental impacts and alternative ESG consumer points using verified intergovernmental data frameworks, aligning natively with UNFCCC baselines, Article 6.4 of the Paris Agreement, and IFC Performance Standards. 

### 1. Carbon Mass Fractionalization (M)

Aggregated fiat change is normalized into Euro equivalents (VCM baseline currency) and evaluated against clearing spot market metrics to allocate an exact multi-decimal sub-unit mass of carbon: 

M = (Fiat Amount in EUR / Spot Market Carbon Price per Tonne in EUR) * 1000 kg 

### 2. IFC-Compliant Eco-Points Formulation

To convert charity friction into a personal financial asset, the system generates non-inflationary EFI Eco-Points to optimize individual consumer alternative credit scoring matrices: 

Eco-Point = (M * K) * S 

* **M (Carbon Mass):** Calculated fractional weight of sequestered CO2 in kilograms.
* **K (UN SDG Priority Coefficient):** Dynamic weight mapped to localized urgent environmental crises (e.g., 1.5 for the Pamir Glaciers Preservation Program under FAO indicators).
* **S (IFC Behavioral Stability Index):** Value multiplier set to 1.2 for automated, recurring background round-up activities, confirming long-term user retention.

### Security & Anti-Double-Counting Architecture

To prevent greenwashing, asset duplication, and settlement manipulation, the engine runs a strict three-tier verification mechanism: 

1. **Wholesale Retirement Automation:** Micro-liquidity is aggregated within automated escrow accounts until it reaches wholesale thresholds, triggering a permanent "Retired" state within international carbon registries (Verra / Gold Standard).
2. **Cryptographic Fractional Locking (Layer-2):** Every fractionated retail transaction is hashed via SHA-256 alongside the anonymized Transaction ID, a Merchant Category Code (MCC), and a high-precision timestamp nonce, blocking asset reuse at the database level.
3. **Sovereign Node Mirroring:** The state machine routes transaction ledger logs via secure API gateways directly to the United Nations International Computing Centre nodes, anchoring finalized cryptographic blocks onto The Atrium Blockchain Network under the direct administration of UN DESA (New York). Host financial integrations maintain zero write-privileges over central validation layers.

### Repository Structure & Code Architecture

This repository contains a fully working prototype of the core mathematical framework, structured as an asynchronous microservice: 

* **main.py:** Built on FastAPI, handling high-throughput, multi-currency routing (TJS to EUR mapping), automated computing matrices, and structural metadata attachment for IFRS S2 compliance.
* **test_main.py:** Automated end-to-end pytest scenarios enforcing validation of precise micro-monetary rounding rules (Decimal typing layers) and validating duplicate mitigation filters (HTTP 409 Conflict triggers).

### API Endpoint Verification (FastAPI Pipeline)

### POST /api/v1/verify-contribution

Executes real-time token fractionation and updates cumulative user metadata buffers. 

**Request Payload:** 

json

{
  "transaction_id": "TX-2026-9913-AF",
  "contribution_amount": 0.45,
  "currency": "TJS",
  "merchant_category_code": "5411",
  "timestamp": "2026-10-22T04:15:00Z"
}

Используйте код с осторожностью.

**Response Output (200 OK):** 

json

{
  "status": "verified_and_retired",
  "transaction_id": "TX-2026-9913-AF",
  "allocated_project": "ICE_EUA_Compliance_Dec2026",
  "physical_impact_kg": 0.46,
  "blockchain_hash": "8f32b7a3a9b1c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b9",
  "verification_node": "EFI-Local-Core-Node-01",
  "un_atrium_mirror_status": "ready_for_sync",
  "metadata": {
    "accounting_protocol": "IFRS S2 / ESG Compliant",
    "operation_type": "Carbon Removal"
  },
  "user_notification": "Your transaction change of 0.45 TJS has been recorded. Capital is accumulating toward the target threshold of 1.00 kg CO2. Progress updated in-app."
}

Используйте код с осторожностью.

### Governance & License

* **Status:** Active Global Digital Public Good Review.
* **Licensing:** This repository is licensed under the terms of the MIT License.

### Contact & Collaboration

For sovereign onboarding inquiries, technical validation requests, or sandbox API keys, please contact the Lead Architect: 

* **Project Founder:** Masrur Azizov
* **Email:** masrur.azizov@gmail.com
* **Location:** Dushanbe, Republic of Tajikistan
* **Status:** Open for International Advisory Board Engagement & Institutional Pilots.
