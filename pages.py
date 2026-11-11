"""The HTML pages."""                         # Docstring: what this file does
from flask import Blueprint, current_app, render_template  # NEW: current_app, to read the database file name
import database

bp = Blueprint("pages", __name__)             # Create the group; app.py registers it

@bp.route("/")                                # The home page
def index():                                  # Runs when the browser asks for /
    return render_template("index.html")      # Fill in templates/index.html and send it

@bp.route("/login")                           # Login page (built on Thursday)
def login_page():                             # Runs for /login
    return render_template("login.html")      # Send the page

@bp.route("/converter")                       # The converter page
def converter_page():                         # Runs for /converter
    return render_template("converter.html")  # Send the page

@bp.route("/quote-page")                      # Quote page (Tuesday)
def quote_page():                                              # Runs for /quote-page
    plans = database.get_plans(current_app.config["DB_FILE"])  # NEW: load the plans for the drop-down list
    return render_template("quote.html", plans=plans)      # Send the page

@bp.route("/history-page")                    # History page (Thursday)
def history_page():                           # Runs for /history-page
    return render_template("history.html")    # Send the page