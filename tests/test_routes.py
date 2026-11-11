import pytest                                                           # For the fixture
import database                                                         # To read the test database
import app as app_module                                                # Our Flask app, under a nickname so it does not clash with the app name

@pytest.fixture                                                         # Set-up code the tests can ask for
def client(db_file):                                    # A fake browser connected to a temporary database
    app_module.app.config["DB_FILE"] = db_file          # Point the app at the test database
    test_client = app_module.app.test_client()          # Flask's built-in fake browser
    with test_client.session_transaction() as session:  # NEW: open the fake browser's login cookie
        session["user_id"] = 1                          # NEW: sign in as the demo user, because every route is private now
    return test_client

def post_convert(client, amount, from_code="GBP", to_code="USD"):       # Helper: send one conversion request
    return client.post("/api/convert", json={"amount": amount, "from": from_code, "to": to_code})  # json= sets the body and the header for us

def test_currencies_route_lists_six(client):                            # GET /api/currencies
    response = client.get("/api/currencies")                            # Ask for the list
    assert response.status_code == 200                                  # OK
    assert len(response.get_json()) == 6                                # Six currencies

def test_convert_300_gbp_to_usd(client):                                # The first check value
    response = post_convert(client, "300")                              # Convert 300 GBP to USD
    data = response.get_json()                                          # Read the JSON reply
    assert response.status_code == 200                                  # OK
    assert data["converted"] == "390.00"                                # 300 x 1.30
    assert data["fee_percent"] == "3.5"                                 # Lowest band
    assert data["fee_usd"] == "13.65"                                   # 10.50 GBP in dollars

def test_convert_2501_gbp_to_usd(client):                               # The top fee band
    data = post_convert(client, "2501").get_json()                      # Convert 2,501
    assert data["converted"] == "3251.30"                               # 2,501 x 1.30
    assert data["fee_usd"] == "48.77"                                   # 1.5% band

def test_convert_saves_a_transaction(client, db_file):                  # The row must reach the database
    post_convert(client, "500")                                         # Convert once
    connection = database.get_connection(db_file)                       # Open the test database
    rows = connection.execute("SELECT amount, fee_usd FROM conversion_transaction").fetchall()  # Read what was saved
    connection.close()                                                  # Release the file
    assert len(rows) == 1                                               # Exactly one row
    assert rows[0]["fee_usd"] == 22.75                                  # 3.5% of 500 in dollars

def test_below_minimum_is_rejected_with_message(client):                # Validation reaches the user
    response = post_convert(client, "299")                              # One below the minimum
    assert response.status_code == 400                                  # Bad Request
    assert "between 300 and 5,000" in response.get_json()["error"]      # The message states the limits

def test_same_currency_is_rejected(client):                             # GBP to GBP
    response = post_convert(client, "500", "GBP", "GBP")                # Same both sides
    assert response.status_code == 400                                  # Bad Request

def test_unknown_currency_is_rejected(client):                          # A code we do not support
    response = post_convert(client, "500", "GBP", "XYZ")                # XYZ is not offered
    assert response.status_code == 400                                  # Bad Request

def test_missing_body_is_rejected(client):                              # A request with no JSON at all
    response = client.post("/api/convert")                              # No body
    assert response.status_code == 400                                  # Bad Request, not a crash

def post_quote(client, lump, monthly, plan_id=2):                       # NEW helper: send one quote request
    return client.post("/api/quote", json={"lump_sum": lump, "monthly": monthly, "plan_id": plan_id})  # json= sets the body and header

def test_quote_route_returns_all_plans_and_recommendation(client):      # NEW: the quote route works
    response = post_quote(client, "1000", "200", 2)                     # Chosen plan 2
    data = response.get_json()                                          # Read the reply
    assert response.status_code == 200                                  # OK
    assert len(data["plans"]) == 3                                      # Three plans
    assert data["recommended_plan_id"] == 3                             # Plan 3 wins
    chosen = next(p for p in data["plans"] if p["plan_id"] == 2)        # The chosen plan
    assert len(chosen["results"]) == 6                                  # Six result rows
    assert chosen["results"][0]["final_value"].count(".") == 1          # Text with a decimal point

def test_quote_route_rejects_plan_rule_breaks(client):                  # NEW: plan rules reach the user
    response = post_quote(client, "100", "50", 2)                       # Plan 2 needs a 300 lump sum
    assert response.status_code == 400                                  # Bad Request
    assert "300.00" in response.get_json()["error"]                     # The message names the limit

def test_quote_route_rejects_bad_numbers(client):                       # NEW: junk is rejected
    assert post_quote(client, "abc", "50", 1).status_code == 400        # Not a number
    assert post_quote(client, "0", "-5", 1).status_code == 400          # Negative

def test_quote_is_stored_with_six_results(client, db_file):             # NEW: the quote reaches the database
    post_quote(client, "1000", "200", 3)                                # Make a quote
    connection = database.get_connection(db_file)                       # Open the test database
    quotes_count = connection.execute("SELECT COUNT(*) FROM quote").fetchone()[0]  # Count quotes
    results_count = connection.execute("SELECT COUNT(*) FROM quote_result").fetchone()[0]  # Count results
    connection.close()                                                  # Release the file
    assert (quotes_count, results_count) == (1, 6)                      # One quote, six results

def test_save_quote_marks_it_saved(client):                             # NEW: the Save button route
    quote_id = post_quote(client, "1000", "200", 3).get_json()["quote_id"]  # Make a quote
    response = client.post("/api/quotes/" + str(quote_id) + "/save")    # Save it
    assert response.status_code == 200                                  # OK
    assert client.post("/api/quotes/999/save").status_code == 404       # An unknown quote is Not Found