import pytest
import app as app_module
import auth
import database


@pytest.fixture
def browser(db_file):
    app_module.app.config["DB_FILE"] = db_file
    return app_module.app.test_client()


REGISTRATION = {"name": "Sam Lee", "email": "Sam@Example.com", "phone": "+971 50 123 4567", "password": "Secret123"}


def test_hash_is_not_the_password_and_verifies():
    hashed = auth.hash_password("Secret123")
    assert hashed != "Secret123"
    assert auth.check_password("Secret123", hashed)
    assert not auth.check_password("secret123", hashed)
    assert auth.hash_password("Secret123") != hashed


@pytest.mark.parametrize("method, path", [("post", "/api/convert"), ("post", "/api/quote"), ("get", "/api/history"), ("post", "/api/drafts"), ("get", "/api/drafts/1"), ("post", "/api/quotes/1/save"), ("get", "/api/dashboard"), ("delete", "/api/transactions/1")])
def test_private_api_routes_need_login(browser, method, path):
    assert getattr(browser, method)(path).status_code == 401


@pytest.mark.parametrize("path", ["/dashboard", "/converter", "/quote-page", "/history-page"])
def test_private_pages_redirect_to_login(browser, path):
    response = browser.get(path)
    assert response.status_code == 302
    assert "/login?next=" + path in response.headers["Location"]


def test_public_pages_open_without_login(browser):
    assert browser.get("/").status_code == 200
    assert browser.get("/login").status_code == 200
    assert browser.get("/register").status_code == 200
    assert browser.get("/forgot-password").status_code == 200
    assert browser.get("/reset-password").status_code == 200


def test_register_stores_contact_details_and_hashed_password(browser, db_file):
    response = browser.post("/api/register", json=REGISTRATION)
    assert response.status_code == 200
    user = database.get_user_by_email("sam@example.com", db_file)
    assert user["name"] == "Sam Lee"
    assert user["password_hash"] != "Secret123"
    assert browser.get("/converter").status_code == 200


def test_duplicate_email_is_rejected(browser):
    browser.post("/api/register", json=REGISTRATION)
    response = browser.post("/api/register", json=REGISTRATION)
    assert response.status_code == 400
    assert "already exists" in response.get_json()["error"]


@pytest.mark.parametrize("field, value", [("email", "not-an-email"), ("password", "short1"), ("password", "allletters"), ("password", "12345678"), ("name", ""), ("phone", "abc")])
def test_bad_registration_is_rejected(browser, field, value):
    data = {**REGISTRATION, field: value}
    assert browser.post("/api/register", json=data).status_code == 400


def test_login_and_logout(browser):
    browser.post("/api/register", json=REGISTRATION)
    browser.post("/api/logout")
    assert browser.get("/converter").status_code == 302
    ok = browser.post("/api/login", json={"email": "sam@example.com", "password": "Secret123"})
    assert ok.status_code == 200
    assert browser.get("/converter").status_code == 200


def test_wrong_password_and_unknown_email_give_the_same_message(browser):
    browser.post("/api/register", json=REGISTRATION)
    wrong = browser.post("/api/login", json={"email": "sam@example.com", "password": "Wrong123"})
    unknown = browser.post("/api/login", json={"email": "nobody@example.com", "password": "Wrong123"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.get_json() == unknown.get_json()


def test_users_cannot_see_each_others_history(browser):
    browser.post("/api/register", json=REGISTRATION)
    browser.post("/api/convert", json={"amount": "500", "from": "GBP", "to": "USD"})
    browser.post("/api/logout")
    browser.post("/api/register", json={**REGISTRATION, "email": "b@example.com"})
    assert browser.get("/api/history").get_json()["transactions"] == []


def test_security_headers_are_present(browser):
    headers = browser.get("/").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_sql_injection_text_is_just_text(browser):
    response = browser.post("/api/login", json={"email": "x' OR '1'='1", "password": "x"})
    assert response.status_code == 401
