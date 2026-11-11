from flask import Blueprint, current_app, jsonify, request              # Flask tools

import database                                                         # Saving and loading data
import security                                                         # Who is the user

bp = Blueprint("history", __name__)                                     # Create the group; app.py registers it

def money(value):                                                       # Format a number with two decimal places
    return f"{value:.2f}"                                               # 12.5 becomes 12.50

@bp.route("/api/history", methods=["GET"])                              # The user's transactions and saved quotes
def history():                                                          # Runs for GET /api/history
    data = database.get_history(security.current_user_id(), current_app.config["DB_FILE"])  # Load this user's records only
    for t in data["transactions"]:                                      # Tidy each transaction
        for key in ("amount", "fee_usd", "converted_amount"):           # The money fields
            t[key] = money(t[key])                                      # Two decimal places
    for q in data["quotes"]:                                            # Tidy each saved quote
        q["lump_sum"] = money(q["lump_sum"])                            # Lump sum
        q["monthly_amount"] = money(q["monthly_amount"])                # Monthly amount
        for r in q["results"]:                                          # Each result row
            for key in ("final_value", "total_profit", "total_fees", "total_tax"):  # The money fields
                r[key] = money(r[key])                                  # Two decimal places
    return jsonify(data), 200                                           # 200 means OK

@bp.route("/api/drafts", methods=["POST"])                              # Save a draft of a form
def save_draft():                                                       # Runs for POST /api/drafts
    data = request.get_json(silent=True) or {}                          # Read the JSON body, or an empty dictionary
    if not data:                                                        # Nothing to save
        return jsonify({"error": "There is nothing to save."}), 400     # 400 means Bad Request
    draft_id = database.save_draft(security.current_user_id(), data, current_app.config["DB_FILE"])  # Store it for this user
    return jsonify({"draft_id": draft_id}), 200                         # Send back the id

@bp.route("/api/drafts/<int:draft_id>", methods=["GET"])                # Load a draft
def load_draft(draft_id):                                               # Runs for GET /api/drafts/5
    form_data = database.get_draft(draft_id, security.current_user_id(), current_app.config["DB_FILE"])  # Only this user's drafts
    if form_data is None:                                               # Not found, or not theirs
        return jsonify({"error": "Draft not found."}), 404              # 404 means Not Found
    return jsonify(form_data), 200                                      # Send the saved values back