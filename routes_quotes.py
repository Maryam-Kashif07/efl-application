from flask import Blueprint, current_app, jsonify, request              # Flask tools

import database                                                         # Saving and loading data
import quotes                                                           # The quote engine
import security                                                         # Who is the user
import validators                                                       # Input checks
from errors import InputError                                           # The error for bad input

bp = Blueprint("quotes", __name__)                                      # Create the group; app.py registers it

@bp.route("/api/quote", methods=["POST"])                               # Calculate a quote for every plan
def quote():                                                            # Runs for POST /api/quote
    data = request.get_json(silent=True) or {}                          # Read the JSON body, or an empty dictionary
    db_file = current_app.config["DB_FILE"]                             # Which database file to use
    plans = database.get_plans(db_file)                                 # Load the plans and tax rules
    try:                                                                # Known input errors are caught below
        lump_sum = validators.validate_money(data.get("lump_sum"), "lump sum")  # Check the lump sum
        monthly = validators.validate_money(data.get("monthly"), "monthly amount")  # Check the monthly amount
        chosen = validators.validate_plan_id(data.get("plan_id"), plans)  # Check the chosen plan
        validators.validate_quote_inputs(chosen, lump_sum, monthly)     # Check the chosen plan's rules
    except InputError as error:                                         # The user typed something invalid
        return jsonify({"error": str(error)}), 400                      # 400 means Bad Request
    entries = quotes.build_quote(plans, lump_sum, monthly)              # Results for every plan
    best = quotes.recommend_plan(entries)                               # The recommended plan, or None
    chosen_entry = next(e for e in entries if e["plan_id"] == chosen["plan_id"])  # The entry for the plan the user picked
    quote_id = database.save_quote(                                     # Store the quote and its results
        security.current_user_id(),                                     # Whose quote it is
        chosen["plan_id"],                                              # The plan the user chose
        best["plan_id"] if best else None,                              # The recommended plan, or nothing
        lump_sum,                                                       # Lump sum
        monthly,                                                        # Monthly amount
        chosen_entry["results"],                                        # The six result rows of the chosen plan
        db_file,                                                        # Which database
    )                                                                   # End of the call
    return jsonify({                                                    # Send the quote to the browser
        "quote_id": quote_id,                                           # The id, used by the Save button
        "chosen_plan_id": chosen["plan_id"],                            # The user's choice
        "recommended_plan_id": best["plan_id"] if best else None,       # Our recommendation
        "plans": quotes.serialise(entries),                             # All results as text values
    }), 200                                                             # 200 means OK

@bp.route("/api/quotes/<int:quote_id>/save", methods=["POST"])          # Mark a quote as saved
def save_quote_route(quote_id):                                         # Runs for POST /api/quotes/5/save
    db_file = current_app.config["DB_FILE"]                             # Which database file to use
    if not database.mark_quote_saved(quote_id, security.current_user_id(), db_file):  # False means no such quote for this user
        return jsonify({"error": "Quote not found."}), 404              # 404 means Not Found
    return jsonify({"saved": True}), 200                                # 200 means OK