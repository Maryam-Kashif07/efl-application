import json                                                             # To read the cached file
import urllib.error                                                     # The error a failed download raises
from decimal import Decimal                                             # Exact numbers

import pytest                                                           # For the fixture
import app as app_module                                                # Our Flask app
import config                                                           # Settings
import currency                                                         # The rate functions
import database                                                         # To read the test database
import diagnostics                                                      # The failure behaviours

@pytest.fixture                                                         # Set-up code the tests can ask for
def client(db_file):                                                    # A signed-in fake browser
    app_module.app.config["DB_FILE"] = db_file                          # Point the app at the test database
    test_client = app_module.app.test_client()                          # Flask's fake browser
    with test_client.session_transaction() as session:                  # Open its login cookie
        session["user_id"] = 1                                          # Sign in as the demo user
    return test_client                                                  # Hand it to the test

def rows(db_file, sql):                                                 # Helper: run a SELECT and return the rows
    connection = database.get_connection(db_file)                       # Open the test database
    result = connection.execute(sql).fetchall()                         # Run the query
    connection.close()                                                  # Release the file
    return result                                                       # Give the rows back

# ---- 1. Internal error: fail gracefully, log to the database ----

def test_internal_error_fails_gracefully_and_logs_to_database(client, db_file, monkeypatch):  # A crash inside a route
    def boom(*args, **kwargs):                                          # A fake function that always crashes
        raise RuntimeError("deliberate test failure")                   # The crash
    monkeypatch.setattr("currency.convert", boom)                       # Make currency.convert crash
    response = client.post("/api/convert", json={"amount": "500", "from": "GBP", "to": "USD"})  # Convert as normal
    assert response.status_code == 500                                  # A clean 500, not a crash page
    assert "deliberate test failure" not in response.get_data(as_text=True)  # No technical details shown to the user
    logged = rows(db_file, "SELECT source, message FROM error_log")     # Read the error log
    assert len(logged) == 1                                             # One row logged
    assert logged[0]["source"] == "/api/convert"                        # It says where it failed
    assert "deliberate test failure" in logged[0]["message"]            # It holds the diagnostic data

# ---- 2. System failure: cache the user's data immediately ----

def test_system_failure_caches_user_data(client, db_file, monkeypatch, tmp_path):  # The data typed must not be lost
    def boom(*args, **kwargs):                                          # A fake function that always crashes
        raise RuntimeError("deliberate test failure")                   # The crash
    monkeypatch.setattr("currency.convert", boom)                       # Make currency.convert crash
    body = {"amount": "750.00", "from": "GBP", "to": "EUR"}             # What the user typed
    response = client.post("/api/convert", json=body)                   # Send it
    files = list((tmp_path / "cache").glob("user_1_*.json"))            # Look in the cache folder
    assert len(files) == 1                                              # One cache file
    assert json.loads(files[0].read_text(encoding="utf-8")) == body     # It holds exactly what was typed
    draft_id = response.get_json()["draft_id"]                          # The reply names a draft
    assert client.get("/api/drafts/" + str(draft_id)).get_json() == body  # The data can be loaded back from the database

# ---- 3. Network failure: diagnostic data to the local file system ----

def test_network_failure_logs_to_file_and_uses_saved_rates(client, db_file, monkeypatch, tmp_path):  # The rate service is down
    monkeypatch.setattr(config, "USE_LIVE_RATES", True)                 # Switch live rates on for this test
    def offline():                                                      # A fake download that fails
        raise urllib.error.URLError("no network")                       # The failure
    monkeypatch.setattr(currency, "fetch_live_rates", offline)          # Use the fake
    response = client.post("/api/convert", json={"amount": "300", "from": "GBP", "to": "USD"})  # Convert as normal
    data = response.get_json()                                          # Read the reply
    assert response.status_code == 200                                  # The conversion still works
    assert data["converted"] == "390.00"                                # It used the saved sample rate
    assert "unavailable" in data["warning"]                             # The user is warned
    log_text = (tmp_path / "logs" / "network.log").read_text(encoding="utf-8")  # Read the log file
    assert "Network failure" in log_text and "no network" in log_text   # The diagnostic data is in the file

def test_live_rates_are_stored_and_reused_while_fresh(db_file, monkeypatch):  # The service works
    monkeypatch.setattr(config, "USE_LIVE_RATES", True)                 # Switch live rates on
    calls = []                                                          # We count how often the service is called
    def fake_download():                                                # A fake download that succeeds
        calls.append(1)                                                 # Count the call
        return {code: Decimal("2") for code in config.CURRENCIES}       # Every currency is worth 2 dollars
    monkeypatch.setattr(currency, "fetch_live_rates", fake_download)    # Use the fake
    assert currency.refresh_rates(db_file) is None                      # No warning
    assert currency.get_rate("GBP", "USD", db_file) == Decimal("1.000000")  # 2 divided by 2: the new rates are used
    currency.refresh_rates(db_file)                                     # Ask again straight away
    assert len(calls) == 1                                              # The service was not called a second time

def test_log_error_to_db_falls_back_to_a_file(monkeypatch, tmp_path):   # Even logging can fail
    def broken(*args, **kwargs):                                        # A fake logger that fails
        raise RuntimeError("database down")                             # The failure
    monkeypatch.setattr(database, "log_error", broken)                  # Use the fake
    assert diagnostics.log_error_to_db("test", "original problem") is False  # Reports the failure
    text = (tmp_path / "logs" / "internal.log").read_text(encoding="utf-8")  # The file fallback
    assert "original problem" in text and "database down" in text       # Both messages are kept