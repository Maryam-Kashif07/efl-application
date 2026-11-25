from flask import Blueprint, current_app, jsonify, request

import database
import security

bp = Blueprint("history", __name__)


def money(value):
    return f"{value:.2f}"


@bp.route("/api/history", methods=["GET"])
def history():
    data = database.get_history(security.current_user_id(), current_app.config["DB_FILE"])
    for t in data["transactions"]:
        for key in ("amount", "fee_usd", "converted_amount"):
            t[key] = money(t[key])
    for q in data["quotes"]:
        q["lump_sum"] = money(q["lump_sum"])
        q["monthly_amount"] = money(q["monthly_amount"])
        for r in q["results"]:
            for key in ("final_value", "total_profit", "total_fees", "total_tax"):
                r[key] = money(r[key])
    return jsonify(data), 200


@bp.route("/api/dashboard", methods=["GET"])
def dashboard():
    data = database.get_dashboard(security.current_user_id(), current_app.config["DB_FILE"])
    for t in data["recent"]:
        for key in ("amount", "converted_amount"):
            t[key] = money(t[key])
    return jsonify(data), 200


@bp.route("/api/transactions/<int:transaction_id>", methods=["DELETE"])
def delete_transaction(transaction_id):
    if not database.delete_transaction(transaction_id, security.current_user_id(), current_app.config["DB_FILE"]):
        return jsonify({"error": "Conversion not found."}), 404
    return jsonify({"deleted": True}), 200


@bp.route("/api/drafts", methods=["POST"])
def save_draft():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "There is nothing to save."}), 400
    draft_id = database.save_draft(security.current_user_id(), data, current_app.config["DB_FILE"])
    return jsonify({"draft_id": draft_id}), 200


@bp.route("/api/drafts/<int:draft_id>", methods=["GET"])
def load_draft(draft_id):
    form_data = database.get_draft(draft_id, security.current_user_id(), current_app.config["DB_FILE"])
    if form_data is None:
        return jsonify({"error": "Draft not found."}), 404
    return jsonify(form_data), 200
