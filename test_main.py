from decimal import Decimal
from uuid import uuid4

import main
from fastapi.testclient import TestClient

client = TestClient(main.app)


def set_fx_rates(monkeypatch, eur_per_unit):
    async def fake_get_eur_per_unit(currency_code):
        return eur_per_unit[currency_code.upper()]

    monkeypatch.setattr(main, "get_eur_per_unit", fake_get_eur_per_unit)


def reset_repository(monkeypatch):
    monkeypatch.setattr(main, "db_repository", main.InMemoryAppendOnlyRepository())


def contribution_payload(currency="EUR", amount="1.00", **overrides):
    payload = {
        "transaction_id": f"TX-TEST-{currency}-{uuid4()}",
        "contribution_amount": amount,
        "currency": currency,
        "merchant_category_code": "5411",
        "timestamp": "2026-10-22T04:15:00Z",
        "donor_id": "donor-test",
        "region": "TJ",
        "offset_category": "RENEWABLE_ENERGY",
    }
    payload.update(overrides)
    return payload


def test_tjs_calculation_uses_six_decimal_places(monkeypatch):
    reset_repository(monkeypatch)
    set_fx_rates(monkeypatch, {"TJS": Decimal("0.08734")})
    response = client.post(
        "/api/v1/verify-contribution",
        json=contribution_payload("TJS", "0.63"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["amount_eur"] == "0.055024"
    assert data["physical_impact_kg"] == "0.639814"
    assert data["simulation_only"] is True
    assert data["un_atrium_mirror_status"] == "NOT_CONNECTED_SIMULATION_ONLY"
    assert "no money was spent" in data["user_notification"]
    assert len(data["blockchain_hash"]) == 64


def test_decimal_input_and_conversion_are_not_binary_float_math(monkeypatch):
    reset_repository(monkeypatch)
    set_fx_rates(monkeypatch, {"TJS": Decimal("0.08734")})
    response = client.post(
        "/api/v1/verify-contribution",
        json=contribution_payload("TJS", "0.45"),
    )

    assert response.status_code == 200
    assert response.json()["amount_eur"] == "0.039303"
    assert response.json()["physical_impact_kg"] == "0.457012"


def test_usd_conversion(monkeypatch):
    reset_repository(monkeypatch)
    set_fx_rates(monkeypatch, {"USD": Decimal("0.92")})
    response = client.post(
        "/api/v1/verify-contribution",
        json=contribution_payload("USD", "1.000000"),
    )

    assert response.status_code == 200
    assert response.json()["physical_impact_kg"] == "10.697674"


def test_eur_uses_one_to_one_conversion_rate(monkeypatch):
    reset_repository(monkeypatch)
    set_fx_rates(monkeypatch, {"EUR": Decimal("1")})
    response = client.post(
        "/api/v1/verify-contribution",
        json=contribution_payload("EUR", "1.000000"),
    )

    assert response.status_code == 200
    assert response.json()["physical_impact_kg"] == "11.627907"


def test_currency_list_endpoint_returns_provider_supported_codes(monkeypatch):
    async def fake_provider_rates():
        return {"USD": Decimal("1"), "EUR": Decimal("0.92"), "TJS": Decimal("10.5")}

    monkeypatch.setattr(main, "_get_provider_rates", fake_provider_rates)
    response = client.get("/api/v1/currencies")

    assert response.status_code == 200
    assert response.json()["base"] == "USD"
    assert response.json()["currencies"] == ["EUR", "TJS", "USD"]


def test_one_kg_threshold_creates_simulated_batch(monkeypatch):
    reset_repository(monkeypatch)
    set_fx_rates(monkeypatch, {"EUR": Decimal("1")})
    response = client.post(
        "/api/v1/verify-contribution",
        json=contribution_payload("EUR", "0.086000"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["physical_impact_kg"] == "1.000000"
    assert data["simulated_purchase_kg"] == "1.000000"
    assert data["simulated_purchase_batch_id"] == "SIM-BATCH-000001"
    assert data["pool_kg_remaining"] == "0.000000"
    assert data["status"] == "simulated_purchase_threshold_reached"
    assert "no real offset was purchased" in data["user_notification"]


def test_pools_are_separated_by_region_and_offset_category(monkeypatch):
    reset_repository(monkeypatch)
    set_fx_rates(monkeypatch, {"EUR": Decimal("1")})
    first = client.post(
        "/api/v1/verify-contribution",
        json=contribution_payload("EUR", "0.043000", region="TJ", offset_category="WIND"),
    )
    other_pool = client.post(
        "/api/v1/verify-contribution",
        json=contribution_payload("EUR", "0.043000", region="UZ", offset_category="WIND"),
    )

    assert first.status_code == other_pool.status_code == 200
    assert first.json()["pool_kg_remaining"] == "0.500000"
    assert other_pool.json()["pool_kg_remaining"] == "0.500000"
    assert first.json()["simulated_purchase_batch_id"] is None
    assert other_pool.json()["simulated_purchase_batch_id"] is None


def test_repeated_transaction_id_returns_conflict(monkeypatch):
    reset_repository(monkeypatch)
    set_fx_rates(monkeypatch, {"EUR": Decimal("1")})
    payload = contribution_payload("EUR", "0.050000")

    first_response = client.post("/api/v1/verify-contribution", json=payload)
    second_response = client.post("/api/v1/verify-contribution", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 409
