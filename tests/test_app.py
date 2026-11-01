import sqlite3

import app as app_module


def make_test_db(path):
    connection = sqlite3.connect(path)
    connection.executescript(
        "CREATE TABLE greeting (id INTEGER PRIMARY KEY, message TEXT NOT NULL);"
        "INSERT INTO greeting (message) VALUES ('Hello from the test database!');"
    )
    connection.commit()
    connection.close()


def test_home_page_shows_message_from_database(tmp_path):
    db_file = tmp_path / "test.db"
    make_test_db(db_file)
    app_module.app.config["DB_FILE"] = str(db_file)
    client = app_module.app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Hello from the test database!" in response.data