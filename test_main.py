from decimal import Decimal
from uuid import uuid4

import main
from fastapi.testclient import TestClient

client = TestClient(main.app)


def set_fx_rates(monkeypatch, eur_per_unit):
    async def fake_get_eur_per_unit(currency_code):
        return eur_per_unit[currency_code.upper()]

    monkeypatch.setattr(main, "get_eur_per_unit", fake_get_eur_per_unit)


def contribution_payload(currency, amount=1.0):
    return {
        "transaction_id": f"TX-TEST-{currency}-{uuid4()}",
        "contribution_amount": amount,
        "currency": currency,
        "merchant_category_code": "5411",
        "timestamp": "2026-10-22T04:15:00Z",
    }


def test_tjs_rounding_scenario_a(monkeypatch):
    # 0.63 TJS * test rate 0.08734 EUR/TJS rounds to 0.64 kg.
    set_fx_rates(monkeypatch, {"TJS": Decimal("0.08734")})
    response = client.post(
        "/api/v1/verify-contribution",
        json=contribution_payload("TJS", 0.63),
    )

    assert response.status_code == 200
    assert response.json()["physical_impact_kg"] == 0.64


def test_tjs_rounding_scenario_b(monkeypatch):
    # 0.45 TJS * test rate 0.08734 EUR/TJS rounds to 0.46 kg.
    set_fx_rates(monkeypatch, {"TJS": Decimal("0.08734")})
    response = client.post(
        "/api/v1/verify-contribution",
        json=contribution_payload("TJS", 0.45),
    )

    assert response.status_code == 200
    assert response.json()["physical_impact_kg"] == 0.46


def test_selected_usd_currency_uses_its_conversion_rate(monkeypatch):
    set_fx_rates(monkeypatch, {"USD": Decimal("0.92")})
    response = client.post(
        "/api/v1/verify-contribution",
        json=contribution_payload("USD"),
    )

    assert response.status_code == 200
    assert response.json()["physical_impact_kg"] == 10.7
    assert "USD" in response.json()["user_notification"]


def test_selected_eur_currency_uses_one_to_one_rate(monkeypatch):
    set_fx_rates(monkeypatch, {"EUR": Decimal("1")})
    response = client.post(
        "/api/v1/verify-contribution",
        json=contribution_payload("EUR"),
    )

    assert response.status_code == 200
    assert response.json()["physical_impact_kg"] == 11.63


def test_currency_list_endpoint_returns_provider_supported_codes(monkeypatch):
    async def fake_provider_rates():
        return {"USD": Decimal("1"), "EUR": Decimal("0.92"), "TJS": Decimal("10.5")}

    monkeypatch.setattr(main, "_get_provider_rates", fake_provider_rates)
    response = client.get("/api/v1/currencies")

    assert response.status_code == 200
    assert response.json()["base"] == "USD"
    assert response.json()["currencies"] == ["EUR", "TJS", "USD"]


def test_repeated_transaction_id_returns_conflict(monkeypatch):
    set_fx_rates(monkeypatch, {"TJS": Decimal("0.08734")})
    payload = contribution_payload("TJS", 0.50)

    first_response = client.post("/api/v1/verify-contribution", json=payload)
    second_response = client.post("/api/v1/verify-contribution", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 409
