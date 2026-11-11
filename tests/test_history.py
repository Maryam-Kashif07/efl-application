import pytest                                                           # For the fixture
import app as app_module                                                # Our Flask app

@pytest.fixture                                                         # Set-up code the tests can ask for
def client(db_file):                                                    # A signed-in fake browser
    app_module.app.config["DB_FILE"] = db_file                          # Point the app at the test database
    test_client = app_module.app.test_client()                          # Flask's fake browser
    with test_client.session_transaction() as session:                  # Open its login cookie
        session["user_id"] = 1                                          # Sign in as the demo user
    return test_client                                                  # Hand it to the test

def test_history_lists_transactions_and_only_saved_quotes(client):      # What the history page shows
    client.post("/api/convert", json={"amount": "500", "from": "GBP", "to": "USD"})  # One conversion
    saved = client.post("/api/quote", json={"lump_sum": "1000", "monthly": "200", "plan_id": 3}).get_json()["quote_id"]  # A quote we will save
    client.post("/api/quote", json={"lump_sum": "1000", "monthly": "200", "plan_id": 2})  # A quote we will not save
    client.post("/api/quotes/" + str(saved) + "/save")                  # Save the first one
    data = client.get("/api/history").get_json()                        # Ask for the history
    assert len(data["transactions"]) == 1                               # One conversion
    assert data["transactions"][0]["fee_usd"] == "22.75"                # Money has two decimal places
    assert len(data["quotes"]) == 1                                     # Only the saved quote
    assert len(data["quotes"][0]["results"]) == 6                       # With its six results
    assert data["quotes"][0]["plan_name"] == "Managed Stock Investments"  # And the plan name

def test_draft_round_trip(client):                                      # Save and load a draft
    draft_id = client.post("/api/drafts", json={"lump_sum": "500"}).get_json()["draft_id"]  # Save it
    assert client.get("/api/drafts/" + str(draft_id)).get_json() == {"lump_sum": "500"}  # Load it back
    assert client.get("/api/drafts/999").status_code == 404             # An unknown draft is Not Found
    assert client.post("/api/drafts", json={}).status_code == 400       # Nothing to save