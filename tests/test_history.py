import pytest
import app as app_module

@pytest.fixture
def client(db_file):
    app_module.app.config["DB_FILE"] = db_file
    test_client = app_module.app.test_client()
    with test_client.session_transaction() as session:
        session["user_id"] = 1
    return test_client

def test_history_lists_transactions_and_only_saved_quotes(client):
    client.post("/api/convert", json={"amount": "500", "from": "GBP", "to": "USD"})
    saved = client.post("/api/quote", json={"lump_sum": "1000", "monthly": "200", "plan_id": 3}).get_json()["quote_id"]
    client.post("/api/quote", json={"lump_sum": "1000", "monthly": "200", "plan_id": 2})
    client.post("/api/quotes/" + str(saved) + "/save")
    data = client.get("/api/history").get_json()
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["fee_usd"] == "22.75"
    assert len(data["quotes"]) == 1
    assert len(data["quotes"][0]["results"]) == 6
    assert data["quotes"][0]["plan_name"] == "Managed Stock Investments"

def test_draft_round_trip(client):
    draft_id = client.post("/api/drafts", json={"lump_sum": "500"}).get_json()["draft_id"]
    assert client.get("/api/drafts/" + str(draft_id)).get_json() == {"lump_sum": "500"}
    assert client.get("/api/drafts/999").status_code == 404
    assert client.post("/api/drafts", json={}).status_code == 400