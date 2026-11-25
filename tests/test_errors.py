import json
import urllib.error
from decimal import Decimal

import pytest
import app as app_module
import config
import currency
import database
import diagnostics

@pytest.fixture
def client(db_file):
    app_module.app.config["DB_FILE"] = db_file
    test_client = app_module.app.test_client()
    with test_client.session_transaction() as session:
        session["user_id"] = 1
    return test_client

def rows(db_file, sql):
    connection = database.get_connection(db_file)
    result = connection.execute(sql).fetchall()
    connection.close()
    return result

#1. Internal error: fail gracefully, log to the database
def test_internal_error_fails_gracefully_and_logs_to_database(client, db_file, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("deliberate test failure")
    monkeypatch.setattr("currency.convert", boom)
    response = client.post("/api/convert", json={"amount": "500", "from": "GBP", "to": "USD"})
    assert response.status_code == 500
    assert "deliberate test failure" not in response.get_data(as_text=True)
    logged = rows(db_file, "SELECT source, message FROM error_log")
    assert len(logged) == 1
    assert logged[0]["source"] == "/api/convert"
    assert "deliberate test failure" in logged[0]["message"]

#2. System failure: cache the user's data immediately
def test_system_failure_caches_user_data(client, db_file, monkeypatch, tmp_path):
    def boom(*args, **kwargs):
        raise RuntimeError("deliberate test failure")
    monkeypatch.setattr("currency.convert", boom)
    body = {"amount": "750.00", "from": "GBP", "to": "EUR"}
    response = client.post("/api/convert", json=body)
    files = list((tmp_path / "cache").glob("user_1_*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text(encoding="utf-8")) == body
    draft_id = response.get_json()["draft_id"]
    assert client.get("/api/drafts/" + str(draft_id)).get_json() == body

#3. Network failure: diagnostic data to the local file system
def test_network_failure_logs_to_file_and_uses_saved_rates(client, db_file, monkeypatch, tmp_path):
    monkeypatch.setattr(config, "USE_LIVE_RATES", True)

    def offline():
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(currency, "fetch_live_rates", offline)
    response = client.post("/api/convert", json={"amount": "300", "from": "GBP", "to": "USD"})
    data = response.get_json()
    assert response.status_code == 200
    assert data["converted"] == "390.00"
    assert "unavailable" in data["warning"]
    log_text = (tmp_path / "logs" / "network.log").read_text(encoding="utf-8")
    assert "Network failure" in log_text and "no network" in log_text

def test_live_rates_are_stored_and_reused_while_fresh(db_file, monkeypatch):
    monkeypatch.setattr(config, "USE_LIVE_RATES", True)
    calls = []

    def fake_download():
        calls.append(1)
        return {code: Decimal("2") for code in config.CURRENCIES}

    monkeypatch.setattr(currency, "fetch_live_rates", fake_download)
    assert currency.refresh_rates(db_file) is None
    assert currency.get_rate("GBP", "USD", db_file) == Decimal("1.000000")
    currency.refresh_rates(db_file)
    assert len(calls) == 1

def test_log_error_to_db_falls_back_to_a_file(monkeypatch, tmp_path):
    def broken(*args, **kwargs):
        raise RuntimeError("database down")

    monkeypatch.setattr(database, "log_error", broken)
    assert diagnostics.log_error_to_db("test", "original problem") is False
    text = (tmp_path / "logs" / "internal.log").read_text(encoding="utf-8")
    assert "original problem" in text and "database down" in text