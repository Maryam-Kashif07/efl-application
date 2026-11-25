import time

import pytest

import app as app_module
import config

REGISTRATION = {"name": "Sam Lee", "email": "sam@example.com", "phone": "+971 50 123 4567", "password": "Secret123"}


@pytest.fixture
def browser(db_file):
    app_module.app.config["DB_FILE"] = db_file
    client = app_module.app.test_client()
    client.post("/api/register", json=REGISTRATION)
    client.post("/api/logout")
    return client


def log_in(client, password="Secret123"):
    return client.post("/api/login", json={"email": "sam@example.com", "password": password})


def test_account_is_locked_after_too_many_wrong_passwords(browser):
    for _ in range(config.MAX_LOGIN_FAILURES):
        assert log_in(browser, "Wrong123").status_code == 401
    locked = log_in(browser, "Wrong123")
    assert locked.status_code == 429
    assert "Too many failed attempts" in locked.get_json()["error"]
    assert "5 minutes" in locked.get_json()["error"]
    assert log_in(browser).status_code == 429


def test_a_successful_login_clears_the_failed_attempts(browser):
    for _ in range(config.MAX_LOGIN_FAILURES - 1):
        log_in(browser, "Wrong123")
    assert log_in(browser).status_code == 200
    browser.post("/api/logout")
    for _ in range(config.MAX_LOGIN_FAILURES - 1):
        assert log_in(browser, "Wrong123").status_code == 401
    assert log_in(browser).status_code == 200


def test_locking_does_not_affect_other_accounts(browser):
    for _ in range(config.MAX_LOGIN_FAILURES + 1):
        log_in(browser, "Wrong123")
    other = {**REGISTRATION, "email": "other@example.com"}
    assert browser.post("/api/register", json=other).status_code == 200


def test_forgot_password_gives_the_same_answer_for_any_email(browser, monkeypatch):
    monkeypatch.setattr(config, "SHOW_RESET_LINK", False)
    known = browser.post("/api/forgot-password", json={"email": "sam@example.com"})
    unknown = browser.post("/api/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.get_json() == unknown.get_json()


def test_forgot_password_writes_the_link_to_the_log_file(browser, tmp_path):
    browser.post("/api/forgot-password", json={"email": "sam@example.com"})
    text = (tmp_path / "logs" / "reset_links.log").read_text(encoding="utf-8")
    assert "sam@example.com" in text and "reset-password?token=" in text


def get_token(browser):
    link = browser.post("/api/forgot-password", json={"email": "sam@example.com"}).get_json()["reset_link"]
    return link.split("token=")[1]


def test_full_reset_flow(browser):
    token = get_token(browser)
    done = browser.post("/api/reset-password", json={"token": token, "password": "Newpass123", "confirm": "Newpass123"})
    assert done.status_code == 200
    assert log_in(browser, "Secret123").status_code == 401
    assert log_in(browser, "Newpass123").status_code == 200


def test_a_reset_link_works_only_once(browser):
    token = get_token(browser)
    body = {"token": token, "password": "Newpass123", "confirm": "Newpass123"}
    assert browser.post("/api/reset-password", json=body).status_code == 200
    again = browser.post("/api/reset-password", json={**body, "password": "Another123", "confirm": "Another123"})
    assert again.status_code == 400
    assert "invalid or has expired" in again.get_json()["error"]


@pytest.mark.parametrize("password, confirm", [("Newpass123", "Different123"), ("short1", "short1"), ("allletters", "allletters"), ("12345678", "12345678")])
def test_reset_rejects_bad_passwords(browser, password, confirm):
    token = get_token(browser)
    response = browser.post("/api/reset-password", json={"token": token, "password": password, "confirm": confirm})
    assert response.status_code == 400
    assert log_in(browser).status_code == 200


def test_reset_rejects_an_unknown_token(browser):
    response = browser.post("/api/reset-password", json={"token": "not-a-real-token", "password": "Newpass123", "confirm": "Newpass123"})
    assert response.status_code == 400


def test_reset_unlocks_a_locked_account(browser):
    token = get_token(browser)
    for _ in range(config.MAX_LOGIN_FAILURES):
        log_in(browser, "Wrong123")
    assert log_in(browser).status_code == 429
    browser.post("/api/reset-password", json={"token": token, "password": "Newpass123", "confirm": "Newpass123"})
    assert log_in(browser, "Newpass123").status_code == 200


def test_inactive_user_is_signed_out_and_told_why(browser):
    log_in(browser)
    with browser.session_transaction() as session:
        session["last_seen"] = time.time() - (config.SESSION_IDLE_MINUTES + 1) * 60
    page = browser.get("/converter")
    assert page.status_code == 302
    assert "/login?expired=1" in page.headers["Location"]
    assert browser.get("/converter").status_code == 302


def test_inactive_user_gets_a_clear_message_from_the_api(browser):
    log_in(browser)
    with browser.session_transaction() as session:
        session["last_seen"] = time.time() - (config.SESSION_IDLE_MINUTES + 1) * 60
    response = browser.get("/api/history")
    assert response.status_code == 401
    assert response.get_json()["expired"] is True
    assert "inactive" in response.get_json()["error"]


def test_active_user_stays_signed_in(browser):
    log_in(browser)
    with browser.session_transaction() as session:
        session["last_seen"] = time.time() - 60
    assert browser.get("/converter").status_code == 200
