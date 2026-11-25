from flask import Blueprint, current_app, jsonify, request

import database
import quotes
import security
import validators
from errors import InputError

bp = Blueprint("quotes", __name__)

@bp.route("/api/quote", methods=["POST"])
def quote():
    data = request.get_json(silent=True) or {}
    db_file = current_app.config["DB_FILE"]
    plans = database.get_plans(db_file)
    try:
        lump_sum = validators.validate_money(data.get("lump_sum"), "lump sum")
        monthly = validators.validate_money(data.get("monthly"), "monthly amount")
        chosen = validators.validate_plan_id(data.get("plan_id"), plans)
        validators.validate_quote_inputs(chosen, lump_sum, monthly)
    except InputError as error:
        return jsonify({"error": str(error)}), 400
    entries = quotes.build_quote(plans, lump_sum, monthly)
    best = quotes.recommend_plan(entries)
    chosen_entry = next(e for e in entries if e["plan_id"] == chosen["plan_id"])
    quote_id = database.save_quote(
        security.current_user_id(),
        chosen["plan_id"],
        best["plan_id"] if best else None,
        lump_sum,
        monthly,
        chosen_entry["results"],
        db_file,
    )
    return jsonify({
        "quote_id": quote_id,
        "chosen_plan_id": chosen["plan_id"],
        "recommended_plan_id": best["plan_id"] if best else None,
        "plans": quotes.serialise(entries),
    }), 200

@bp.route("/api/quotes/<int:quote_id>/save", methods=["POST"])
def save_quote_route(quote_id):
    db_file = current_app.config["DB_FILE"]
    if not database.mark_quote_saved(quote_id, security.current_user_id(), db_file):
        return jsonify({"error": "Quote not found."}), 404
    return jsonify({"saved": True}), 200