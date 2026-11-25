import hashlib
import secrets
import sqlite3

from flask import Blueprint, current_app, jsonify, request, session

import auth
import config
import database
import diagnostics
import validators
from errors import InputError

bp = Blueprint("auth", __name__)


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def clean_email(value):
    return str(value or "").strip().lower()[:254]


@bp.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    db_file = current_app.config["DB_FILE"]
    try:
        clean = validators.validate_registration(data)
        user_id = database.create_user(clean["name"], clean["email"], clean["phone"], auth.hash_password(clean["password"]), db_file)
    except InputError as error:
        return jsonify({"error": str(error)}), 400
    except sqlite3.IntegrityError:
        return jsonify({"error": "An account with this email already exists."}), 400
    session.clear()
    session["user_id"] = user_id
    return jsonify({"name": clean["name"]}), 200


@bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    db_file = current_app.config["DB_FILE"]
    email = clean_email(data.get("email"))
    password = str(data.get("password") or "")
    if database.count_recent_failures(email, db_file) >= config.MAX_LOGIN_FAILURES:
        message = "Too many failed attempts. Please wait " + str(config.LOGIN_LOCK_MINUTES) + " minutes and try again."
        return jsonify({"error": message}), 429
    user = database.get_user_by_email(email, db_file)
    if user is None or not auth.check_password(password, user["password_hash"]):
        database.record_failed_login(email, db_file)
        return jsonify({"error": "The email or password is incorrect."}), 401
    database.clear_failed_logins(email, db_file)
    session.clear()
    session["user_id"] = user["user_id"]
    return jsonify({"name": user["name"]}), 200


@bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"signed_out": True}), 200


@bp.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    db_file = current_app.config["DB_FILE"]
    email = clean_email(data.get("email"))
    reply = {"message": "If an account exists for that email, a reset link has been sent."}
    user = database.get_user_by_email(email, db_file)
    if user is not None:
        token = secrets.token_urlsafe(32)
        database.create_password_reset(user["user_id"], hash_token(token), db_file)
        link = request.host_url + "reset-password?token=" + token
        diagnostics.log_to_file("Password reset link for " + email + ": " + link, "reset_links.log")
        if config.SHOW_RESET_LINK:
            reply["reset_link"] = link
    return jsonify(reply), 200


@bp.route("/api/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    db_file = current_app.config["DB_FILE"]
    try:
        password = validators.validate_new_password(data.get("password"), data.get("confirm"))
    except InputError as error:
        return jsonify({"error": str(error)}), 400
    token = str(data.get("token") or "")
    if database.reset_password_with_token(hash_token(token), auth.hash_password(password), db_file) is None:
        return jsonify({"error": "This reset link is invalid or has expired. Please request a new one."}), 400
    return jsonify({"reset": True}), 200
