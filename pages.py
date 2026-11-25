from flask import Blueprint, current_app, redirect, render_template, session

import database

bp = Blueprint("pages", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/login")
def login_page():
    if "user_id" in session:
        return redirect("/dashboard")
    return render_template("login.html")


@bp.route("/register")
def register_page():
    if "user_id" in session:
        return redirect("/dashboard")
    return render_template("register.html")


@bp.route("/forgot-password")
def forgot_password_page():
    return render_template("forgot_password.html")


@bp.route("/reset-password")
def reset_password_page():
    return render_template("reset_password.html")


@bp.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")


@bp.route("/converter")
def converter_page():
    return render_template("converter.html")


@bp.route("/quote-page")
def quote_page():
    plans = database.get_plans(current_app.config["DB_FILE"])
    return render_template("quote.html", plans=plans)


@bp.route("/history-page")
def history_page():
    return render_template("history.html")
