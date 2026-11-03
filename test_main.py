from uuid import uuid4

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_scenario_a_round_up_63_dirams():
    # 0.63 TJS should round to 0.64 kg in the UI.
    payload = {
        "transaction_id": f"TX-TEST-A-{uuid4()}",
        "contribution_amount": 0.63,
        "currency": "TJS",
        "merchant_category_code": "5411",
        "timestamp": "2026-10-22T04:15:00Z",
    }
    response = client.post("/api/v1/verify-contribution", json=payload)

    assert response.status_code == 200
    assert response.json()["physical_impact_kg"] == 0.64


def test_scenario_b_round_up_45_dirams():
    # 0.45 TJS should round to 0.46 kg in the UI.
    payload = {
        "transaction_id": f"TX-TEST-B-{uuid4()}",
        "contribution_amount": 0.45,
        "currency": "TJS",
        "merchant_category_code": "5412",
        "timestamp": "2026-10-22T04:15:00Z",
    }
    response = client.post("/api/v1/verify-contribution", json=payload)

    assert response.status_code == 200
    assert response.json()["physical_impact_kg"] == 0.46


def test_idempotency_conflict_protection():
    # Repeating the same transaction must return HTTP 409 on the second request.
    payload = {
        "transaction_id": f"TX-DUPLICATE-{uuid4()}",
        "contribution_amount": 0.50,
        "currency": "TJS",
        "merchant_category_code": "5413",
        "timestamp": "2026-10-22T04:15:00Z",
    }

    first_response = client.post("/api/v1/verify-contribution", json=payload)
    assert first_response.status_code == 200

    second_response = client.post("/api/v1/verify-contribution", json=payload)
    assert second_response.status_code == 409
