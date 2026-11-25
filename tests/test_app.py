import app as app_module


def signed_in_client():
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
    return client


def test_home_page_loads():
    response = app_module.app.test_client().get("/")
    assert response.status_code == 200
    assert b"Savings and currency, made clear." in response.data
    assert b"What the website gives you" in response.data


def test_home_page_offers_log_in_and_sign_up_when_signed_out():
    page = app_module.app.test_client().get("/").data
    assert b"Log in" in page and b"Sign up" in page


def test_home_page_offers_services_when_signed_in():
    page = signed_in_client().get("/").data
    assert b"Open converter" in page and b"Sign out" in page


def test_services_send_signed_out_users_to_login_and_remember_the_page():
    client = app_module.app.test_client()
    for path in ["/dashboard", "/converter", "/quote-page", "/history-page"]:
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login?next=" + path)


def test_login_page_sends_signed_in_users_to_the_dashboard():
    response = signed_in_client().get("/login")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_unknown_page_is_not_found_and_not_a_login_redirect():
    assert app_module.app.test_client().get("/nowhere").status_code == 404


def test_sign_up_button_goes_to_the_create_account_page():
    page = app_module.app.test_client().get("/").data
    assert b'href="/register"' in page


def test_login_page_has_only_the_login_form_and_a_link_to_create_an_account():
    page = app_module.app.test_client().get("/login").data
    assert b"login-form" in page and b"register-form" not in page
    assert b"Don't have an account?" in page and b"Create an account" in page


def test_register_page_has_the_form_and_a_link_back_to_login():
    response = app_module.app.test_client().get("/register")
    assert response.status_code == 200
    assert b"register-form" in response.data
    assert b"Already have an account?" in response.data


def test_register_page_sends_signed_in_users_to_the_dashboard():
    response = signed_in_client().get("/register")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_converter_page_loads_when_signed_in():
    response = signed_in_client().get("/converter")
    assert response.status_code == 200
    assert b"convert-form" in response.data
    assert b"result-card" in response.data
    assert b'data-fee="2.7"' in response.data


def test_quote_and_history_pages_load_when_signed_in():
    client = signed_in_client()
    assert b"quote-form" in client.get("/quote-page").data
    assert b"history-table" in client.get("/history-page").data


def test_font_host_is_allowed_by_the_policy():
    policy = app_module.app.test_client().get("/").headers["Content-Security-Policy"]
    assert "default-src 'self'" in policy
    assert "fonts.googleapis.com" in policy and "fonts.gstatic.com" in policy


def test_menu_has_home_dashboard_converter_quote_history_and_sign_in():
    page = app_module.app.test_client().get("/").data
    for word in [b"Home", b"Dashboard", b"Converter", b"Quote", b"History", b"Sign in"]:
        assert word in page


def test_menu_shows_sign_out_when_signed_in():
    page = signed_in_client().get("/").data
    assert b"Sign out" in page and b"Sign in" not in page


def test_login_page_has_a_forgot_password_link():
    page = app_module.app.test_client().get("/login").data
    assert b"Forgot your password?" in page and b'href="/forgot-password"' in page


def test_forgot_and_reset_pages_are_public():
    client = app_module.app.test_client()
    forgot = client.get("/forgot-password")
    reset = client.get("/reset-password?token=abc")
    assert forgot.status_code == 200 and b"forgot-form" in forgot.data
    assert reset.status_code == 200 and b"Reset Password" in reset.data and b"Confirm new password" in reset.data


def test_dashboard_page_loads_when_signed_in():
    page = signed_in_client().get("/dashboard").data
    assert b"Recent activity" in page and b"Open converter" in page


def test_history_page_has_tiles_and_filters():
    page = signed_in_client().get("/history-page").data
    for word in [b"Total fees paid", b"filter-currency", b"filter-dates", b"filter-sort"]:
        assert word in page


def test_converter_page_has_total_cost_and_rates_updated_lines():
    page = signed_in_client().get("/converter").data
    assert b"Total cost" in page and b"result-updated" in page


def test_history_page_has_one_table_with_converter_and_quote_tabs():
    page = signed_in_client().get("/history-page").data
    assert b"tab-converter" in page and b"tab-quote" in page
    assert b'id="history-table"' in page
    assert b"transactions-table" not in page and b"quotes-table" not in page
    assert b"table-scroll" in page


def test_forgot_password_page_asks_only_for_an_email():
    page = app_module.app.test_client().get("/forgot-password").data
    assert b"forgot-email" in page and b"Demo link" not in page
