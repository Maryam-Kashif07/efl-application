import sqlite3                                                          # To catch the duplicate-email error

from flask import Blueprint, current_app, jsonify, request, session     # Flask tools; session is the signed login cookie

import auth                                                             # Password hashing
import database                                                         # Saving and loading data
import validators                                                       # Input checks
from errors import InputError                                           # The error for bad input

bp = Blueprint("auth", __name__)                                        # Create the group; app.py registers it

@bp.route("/api/register", methods=["POST"])                            # Create an account and keep the contact details
def register():                                                         # Runs for POST /api/register
    data = request.get_json(silent=True) or {}                          # Read the JSON body, or an empty dictionary
    db_file = current_app.config["DB_FILE"]                             # Which database file to use
    try:                                                                # Known input errors are caught below
        clean = validators.validate_registration(data)                  # Check every field
        user_id = database.create_user(clean["name"], clean["email"], clean["phone"], auth.hash_password(clean["password"]), db_file)  # Store the user with a hashed password
    except InputError as error:                                         # A field was invalid
        return jsonify({"error": str(error)}), 400                      # 400 means Bad Request
    except sqlite3.IntegrityError:                                      # The UNIQUE rule on email was broken
        return jsonify({"error": "An account with this email already exists."}), 400  # Tell the user
    session.clear()                                                     # Start a fresh session
    session["user_id"] = user_id                                        # Sign the new user in
    return jsonify({"name": clean["name"]}), 200                        # 200 means OK

@bp.route("/api/login", methods=["POST"])                               # Sign in
def login():                                                            # Runs for POST /api/login
    data = request.get_json(silent=True) or {}                          # Read the JSON body, or an empty dictionary
    email = str(data.get("email") or "").strip().lower()                # The email, cleaned the same way as at registration
    password = str(data.get("password") or "")                          # The password as typed
    user = database.get_user_by_email(email, current_app.config["DB_FILE"])  # Find the user, or None
    if user is None or not auth.check_password(password, user["password_hash"]):  # Unknown email or wrong password
        return jsonify({"error": "The email or password is incorrect."}), 401  # One message for both cases, so attackers cannot tell which emails exist
    session.clear()                                                     # Start a fresh session, which blocks session fixation
    session["user_id"] = user["user_id"]                                # Sign the user in
    return jsonify({"name": user["name"]}), 200                         # 200 means OK

@bp.route("/api/logout", methods=["POST"])                              # Sign out
def logout():                                                           # Runs for POST /api/logout
    session.clear()                                                     # Forget the user
    return jsonify({"signed_out": True}), 200                           # 200 means OK