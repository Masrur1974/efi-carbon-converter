from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_scenario_a_round_up_63_dirams():
    # TS Section 3.4: Round-up verification for 0.63 TJS -> Must output exactly 0.64 kg in UI layout
    payload = {
        "transaction_id": "TX-TEST-A-2026",
        "contribution_amount": 0.63,
        "currency": "TJS",
        "merchant_category_code": "5411",
        "timestamp": "2026-10-22T04:15:00Z"
    }
    response = client.post("/api/v1/verify-contribution", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["physical_impact_kg"] == 0.64  # Enforcement of strict user interface mathematical rounding

def test_scenario_b_round_up_45_dirams():
    # TS Section 3.4: Round-up verification for 0.45 TJS -> Must output exactly 0.46 kg in UI layout
    payload = {
        "transaction_id": "TX-TEST-B-2026",
        "contribution_amount": 0.45,
        "currency": "TJS",
        "merchant_category_code": "5412",
        "timestamp": "2026-10-22T04:15:00Z"
    }
    response = client.post("/api/v1/verify-contribution", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["physical_impact_kg"] == 0.46  # Enforcement of strict user interface mathematical rounding

def test_idempotency_conflict_protection():
    # TS Section 4.2: Resubmitting identical transaction payloads must prompt an HTTP 409 Conflict rejection
    payload = {
        "transaction_id": "TX-DUPLICATE-ID",
        "contribution_amount": 0.50,
        "merchant_category_code": "5413",
        "timestamp": "2026-10-22T04:15:00Z"
    }
    # Initial request pipeline must accept transaction parameters successfully
    res1 = client.post("/api/v1/verify-contribution", json=payload)
    assert res1.status_code == 200
    
    # Identical second request sequence must prompt asset duplicate tracking prevention algorithms
    res2 = client.post("/api/v1/verify-contribution", json=payload)
    assert res2.status_code == 409  # Verify anti-double-counting ledger block is operational
