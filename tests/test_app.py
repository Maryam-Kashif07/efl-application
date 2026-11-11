import app as app_module

def test_home_page_loads():
    client = app_module.app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"EFL application" in response.data

def test_converter_page_needs_login():             # CHANGED: the page is private now
    client = app_module.app.test_client()          # Fake browser that is not signed in
    response = client.get("/converter")            # Ask for the page
    assert response.status_code == 302             # Redirected to the login page

def test_converter_page_loads_when_signed_in():    # NEW: the page opens for a signed-in user
    client = app_module.app.test_client()          # Fake browser
    with client.session_transaction() as session:  # Open its login cookie
        session["user_id"] = 1                     # Sign in as the demo user
    response = client.get("/converter")            # Ask for the page
    assert response.status_code == 200             # OK
    assert b"convert-form" in response.data        # The form is on the page