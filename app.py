import sqlite3

from flask import Flask, render_template

app = Flask(__name__)
app.config["DB_FILE"] = "efl.db"


def get_db():
    """Open a connection to the SQLite database."""
    connection = sqlite3.connect(app.config["DB_FILE"])
    connection.row_factory = sqlite3.Row  # lets us read columns by name
    return connection


@app.route("/")
def index():
    connection = get_db()
    row = connection.execute("SELECT message FROM greeting LIMIT 1").fetchone()
    connection.close()
    return render_template("index.html", message=row["message"])


if __name__ == "__main__":
    app.run(debug=True)