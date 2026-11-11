"""Tests for login, passwords and access control."""                    # Docstring: what is tested
import pytest                                                           # For the fixture
import app as app_module                                                # Our Flask app
import auth                                                             # Password hashing
import database                                                         # To read the test database

@pytest.fixture                                                         # Set-up code the tests can ask for
def browser(db_file):                                                   # A fake browser that is NOT signed in
    app_module.app.config["DB_FILE"] = db_file                          # Point the app at the test database
    return app_module.app.test_client()                                 # Flask's fake browser

REGISTRATION = {"name": "Sam Lee", "email": "Sam@Example.com", "phone": "+971 50 123 4567", "password": "Secret123"}  # A valid registration

def test_hash_is_not_the_password_and_verifies():                       # Passwords are never stored plain
    hashed = auth.hash_password("Secret123")                            # Hash it
    assert hashed != "Secret123"                                        # Not the password itself
    assert auth.check_password("Secret123", hashed)                     # The right password matches
    assert not auth.check_password("secret123", hashed)                 # A wrong password does not
    assert auth.hash_password("Secret123") != hashed                    # A new salt each time

@pytest.mark.parametrize("method, path", [("post", "/api/convert"), ("post", "/api/quote"), ("get", "/api/history"), ("post", "/api/drafts"), ("get", "/api/drafts/1"), ("post", "/api/quotes/1/save")])  # Private API routes and the method each one uses
def test_private_api_routes_need_login(browser, method, path):          # Not signed in
    assert getattr(browser, method)(path).status_code == 401            # Unauthorised; getattr picks browser.post or browser.get

@pytest.mark.parametrize("path", ["/converter", "/quote-page", "/history-page"])  # Private pages
def test_private_pages_redirect_to_login(browser, path):                # Not signed in
    response = browser.get(path)                                        # Ask for the page
    assert response.status_code == 302 and response.headers["Location"].endswith("/login")  # Redirected to the login page

def test_public_pages_open_without_login(browser):                      # Home and login are public
    assert browser.get("/").status_code == 200                          # Home
    assert browser.get("/login").status_code == 200                     # Login

def test_register_stores_contact_details_and_hashed_password(browser, db_file):  # Contact information is kept
    response = browser.post("/api/register", json=REGISTRATION)         # Register
    assert response.status_code == 200                                  # OK
    user = database.get_user_by_email("sam@example.com", db_file)       # The email was lower-cased
    assert user["name"] == "Sam Lee"                                    # Name stored
    assert user["password_hash"] != "Secret123"                         # Only the hash is stored
    assert browser.get("/converter").status_code == 200                 # Registering signs the user in

def test_duplicate_email_is_rejected(browser):                          # UNIQUE email
    browser.post("/api/register", json=REGISTRATION)                    # First account
    response = browser.post("/api/register", json=REGISTRATION)         # Same email again
    assert response.status_code == 400                                  # Rejected
    assert "already exists" in response.get_json()["error"]             # Clear message

@pytest.mark.parametrize("field, value", [("email", "not-an-email"), ("password", "short1"), ("password", "allletters"), ("password", "12345678"), ("name", ""), ("phone", "abc")])  # Bad registrations
def test_bad_registration_is_rejected(browser, field, value):           # One run per bad value
    data = {**REGISTRATION, field: value}                               # Break one field
    assert browser.post("/api/register", json=data).status_code == 400  # Rejected

def test_login_and_logout(browser):                                     # The full cycle
    browser.post("/api/register", json=REGISTRATION)                    # Create the account
    browser.post("/api/logout")                                         # Sign out
    assert browser.get("/converter").status_code == 302                 # Signed out: redirected
    ok = browser.post("/api/login", json={"email": "sam@example.com", "password": "Secret123"})  # Sign in
    assert ok.status_code == 200                                        # OK
    assert browser.get("/converter").status_code == 200                 # The page opens

def test_wrong_password_and_unknown_email_give_the_same_message(browser):  # No account enumeration
    browser.post("/api/register", json=REGISTRATION)                    # Create the account
    wrong = browser.post("/api/login", json={"email": "sam@example.com", "password": "Wrong123"})  # Wrong password
    unknown = browser.post("/api/login", json={"email": "nobody@example.com", "password": "Wrong123"})  # Unknown email
    assert wrong.status_code == unknown.status_code == 401              # Both 401
    assert wrong.get_json() == unknown.get_json()                       # Identical message

def test_users_cannot_see_each_others_history(browser):                 # Data is separated by user
    browser.post("/api/register", json=REGISTRATION)                    # User A
    browser.post("/api/convert", json={"amount": "500", "from": "GBP", "to": "USD"})  # A converts
    browser.post("/api/logout")                                         # Sign out
    browser.post("/api/register", json={**REGISTRATION, "email": "b@example.com"})  # User B
    assert browser.get("/api/history").get_json()["transactions"] == []  # B sees nothing of A's

def test_security_headers_are_present(browser):                         # Safe defaults
    headers = browser.get("/").headers                                  # Any response
    assert headers["X-Content-Type-Options"] == "nosniff"               # No sniffing
    assert headers["X-Frame-Options"] == "DENY"                         # No framing
    assert "default-src 'self'" in headers["Content-Security-Policy"]   # Own-site content only

def test_sql_injection_text_is_just_text(browser):                      # Parameterised queries
    response = browser.post("/api/login", json={"email": "x' OR '1'='1", "password": "x"})  # A classic attack string
    assert response.status_code == 401                                  # Treated as an unknown email