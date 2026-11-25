import pytest
import database
import app as app_module

@pytest.fixture
def client(db_file):
    app_module.app.config["DB_FILE"] = db_file
    test_client = app_module.app.test_client()
    with test_client.session_transaction() as session:
        session["user_id"] = 1
    return test_client

def post_convert(client, amount, from_code="GBP", to_code="USD"):
    return client.post("/api/convert", json={"amount": amount, "from": from_code, "to": to_code})

def test_currencies_route_lists_six(client):
    response = client.get("/api/currencies")
    assert response.status_code == 200
    assert len(response.get_json()) == 6

def test_convert_300_gbp_to_usd(client):
    response = post_convert(client, "300")
    data = response.get_json()
    assert response.status_code == 200
    assert data["converted"] == "390.00"
    assert data["fee_percent"] == "3.5"
    assert data["fee_usd"] == "13.65"

def test_convert_2501_gbp_to_usd(client):
    data = post_convert(client, "2501").get_json()
    assert data["converted"] == "3251.30"
    assert data["fee_usd"] == "48.77"

def test_convert_saves_a_transaction(client, db_file):
    post_convert(client, "500")
    connection = database.get_connection(db_file)
    rows = connection.execute("SELECT amount, fee_usd FROM conversion_transaction").fetchall()
    connection.close()
    assert len(rows) == 1
    assert rows[0]["fee_usd"] == 22.75

def test_below_minimum_is_rejected_with_message(client):
    response = post_convert(client, "299")
    assert response.status_code == 400
    assert "between 300 and 5,000" in response.get_json()["error"]

def test_same_currency_is_rejected(client):
    response = post_convert(client, "500", "GBP", "GBP")
    assert response.status_code == 400

def test_unknown_currency_is_rejected(client):
    response = post_convert(client, "500", "GBP", "XYZ")
    assert response.status_code == 400

def test_missing_body_is_rejected(client):
    response = client.post("/api/convert")
    assert response.status_code == 400

def post_quote(client, lump, monthly, plan_id=2):
    return client.post("/api/quote", json={"lump_sum": lump, "monthly": monthly, "plan_id": plan_id})

def test_quote_route_returns_all_plans_and_recommendation(client):
    response = post_quote(client, "1000", "200", 2)
    data = response.get_json()
    assert response.status_code == 200
    assert len(data["plans"]) == 3
    assert data["recommended_plan_id"] == 3
    chosen = next(p for p in data["plans"] if p["plan_id"] == 2)
    assert len(chosen["results"]) == 6
    assert chosen["results"][0]["final_value"].count(".") == 1

def test_quote_route_rejects_plan_rule_breaks(client):
    response = post_quote(client, "100", "50", 2)
    assert response.status_code == 400
    assert "300.00" in response.get_json()["error"]

def test_quote_route_rejects_bad_numbers(client):
    assert post_quote(client, "abc", "50", 1).status_code == 400
    assert post_quote(client, "0", "-5", 1).status_code == 400

def test_quote_is_stored_with_six_results(client, db_file):
    post_quote(client, "1000", "200", 3)
    connection = database.get_connection(db_file)
    quotes_count = connection.execute("SELECT COUNT(*) FROM quote").fetchone()[0]
    results_count = connection.execute("SELECT COUNT(*) FROM quote_result").fetchone()[0]
    connection.close()
    assert (quotes_count, results_count) == (1, 6)

def test_save_quote_marks_it_saved(client):
    quote_id = post_quote(client, "1000", "200", 3).get_json()["quote_id"]
    response = client.post("/api/quotes/" + str(quote_id) + "/save")
    assert response.status_code == 200
    assert client.post("/api/quotes/999/save").status_code == 404