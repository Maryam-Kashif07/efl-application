import pytest

import app as app_module


def sign_in(client, user_id):
    with client.session_transaction() as session:
        session["user_id"] = user_id


@pytest.fixture
def client(db_file):
    app_module.app.config["DB_FILE"] = db_file
    test_client = app_module.app.test_client()
    sign_in(test_client, 1)
    return test_client


def convert(client, amount="500"):
    return client.post("/api/convert", json={"amount": amount, "from": "GBP", "to": "USD"}).get_json()["transaction_id"]


def test_deleting_a_conversion_removes_it_from_history(client):
    keep = convert(client, "300")
    remove = convert(client, "500")
    response = client.delete("/api/transactions/" + str(remove))
    assert response.status_code == 200
    ids = [t["transaction_id"] for t in client.get("/api/history").get_json()["transactions"]]
    assert ids == [keep]


def test_deleting_a_conversion_removes_it_from_the_dashboard(client):
    convert(client, "300")
    remove = convert(client, "500")
    client.delete("/api/transactions/" + str(remove))
    recent = client.get("/api/dashboard").get_json()["recent"]
    assert [t["amount"] for t in recent] == ["300.00"]


def test_deleting_the_same_conversion_twice_gives_not_found(client):
    transaction_id = convert(client)
    assert client.delete("/api/transactions/" + str(transaction_id)).status_code == 200
    again = client.delete("/api/transactions/" + str(transaction_id))
    assert again.status_code == 404
    assert again.get_json()["error"] == "Conversion not found."


def test_deleting_an_unknown_conversion_gives_not_found(client):
    assert client.delete("/api/transactions/999").status_code == 404


def test_a_user_cannot_delete_another_users_conversion(client, db_file):
    transaction_id = convert(client)
    other = app_module.app.test_client()
    other.post("/api/register", json={"name": "Alex Roe", "email": "alex@example.com", "phone": "", "password": "Secret123"})
    assert other.delete("/api/transactions/" + str(transaction_id)).status_code == 404
    assert len(client.get("/api/history").get_json()["transactions"]) == 1


def test_deleting_needs_login(db_file):
    app_module.app.config["DB_FILE"] = db_file
    assert app_module.app.test_client().delete("/api/transactions/1").status_code == 401
