import pytest

import app as app_module


@pytest.fixture
def client(db_file):
    app_module.app.config["DB_FILE"] = db_file
    test_client = app_module.app.test_client()
    with test_client.session_transaction() as session:
        session["user_id"] = 1
    return test_client


def test_empty_dashboard(client):
    data = client.get("/api/dashboard").get_json()
    assert data["name"] == "Demo user"
    assert data["recent"] == []
    assert data["saved_quotes"] == 0
    assert data["recommended_plan"] is None


def test_dashboard_shows_recent_conversions_newest_first(client):
    client.post("/api/convert", json={"amount": "500", "from": "GBP", "to": "USD"})
    client.post("/api/convert", json={"amount": "1500", "from": "GBP", "to": "USD"})
    recent = client.get("/api/dashboard").get_json()["recent"]
    assert [t["amount"] for t in recent] == ["1500.00", "500.00"]
    assert recent[0]["converted_amount"] == "1950.00"


def test_dashboard_shows_only_five_recent_conversions(client):
    for _ in range(7):
        client.post("/api/convert", json={"amount": "300", "from": "GBP", "to": "USD"})
    assert len(client.get("/api/dashboard").get_json()["recent"]) == 5


def test_dashboard_counts_saved_quotes_and_shows_the_recommended_plan(client):
    first = client.post("/api/quote", json={"lump_sum": "1000", "monthly": "200", "plan_id": 2}).get_json()["quote_id"]
    client.post("/api/quote", json={"lump_sum": "1000", "monthly": "200", "plan_id": 2})
    client.post("/api/quotes/" + str(first) + "/save")
    data = client.get("/api/dashboard").get_json()
    assert data["saved_quotes"] == 1
    assert data["recommended_plan"] == "Managed Stock Investments"


def test_convert_returns_fee_in_original_currency_total_cost_and_rate_details(client):
    data = client.post("/api/convert", json={"amount": "1500", "from": "GBP", "to": "USD"}).get_json()
    assert data["converted"] == "1950.00"
    assert data["fee_usd"] == "52.65"
    assert data["fee_original"] == "40.50"
    assert data["total_cost_usd"] == "2002.65"
    assert data["rates_updated"] is not None
    assert data["rate_source"] == "saved"


def test_total_cost_is_in_us_dollars_for_other_currency_pairs(client):
    data = client.post("/api/convert", json={"amount": "300", "from": "GBP", "to": "EUR"}).get_json()
    assert data["fee_usd"] == "13.65"
    assert data["total_cost_usd"] == "403.65"
