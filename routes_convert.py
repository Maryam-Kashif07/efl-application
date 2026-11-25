from decimal import Decimal

from flask import Blueprint, current_app, jsonify, request

import currency
import database
import fees
import security
import validators
from errors import InputError, RateUnavailableError

bp = Blueprint("convert", __name__)


@bp.route("/api/currencies", methods=["GET"])
def currencies():
    return jsonify(database.list_currencies(current_app.config["DB_FILE"]))


@bp.route("/api/convert", methods=["POST"])
def convert():
    data = request.get_json(silent=True) or {}
    db_file = current_app.config["DB_FILE"]
    try:
        amount = validators.validate_amount(data.get("amount"))
        from_code = validators.validate_currency(data.get("from"))
        to_code = validators.validate_currency(data.get("to"))
        if from_code == to_code:
            raise InputError("Choose two different currencies.")
        warning = currency.refresh_rates(db_file)
        rate = currency.get_rate(from_code, to_code, db_file)
        from_usd = currency.get_rate(from_code, "USD", db_file)
        fee_percent = fees.conversion_fee_percent(amount)
        fee_usd = fees.conversion_fee_usd(amount, from_usd)
        fee_original = currency.round_money(amount * fee_percent / Decimal("100"))
        total_cost_usd = currency.round_money(amount * from_usd) + fee_usd
        converted = currency.convert(amount, rate)
    except InputError as error:
        return jsonify({"error": str(error)}), 400
    except RateUnavailableError as error:
        return jsonify({"error": str(error)}), 503
    rate_info = database.latest_rate_info(db_file)
    rate_source = "live" if warning is None and rate_info["source"] == "live" else "saved"
    transaction_id = database.save_transaction(
        security.current_user_id(),
        {
            "from_currency": from_code,
            "to_currency": to_code,
            "amount": amount,
            "rate_used": rate,
            "fee_percent": fee_percent,
            "fee_usd": fee_usd,
            "converted_amount": converted,
        },
        db_file,
    )
    return jsonify({
        "transaction_id": transaction_id,
        "amount": str(amount),
        "from": from_code,
        "to": to_code,
        "rate": str(rate),
        "fee_percent": str(fee_percent),
        "fee_usd": str(fee_usd),
        "fee_original": str(fee_original),
        "total_cost_usd": str(total_cost_usd),
        "converted": str(converted),
        "rates_updated": rate_info["fetched_at"],
        "rate_source": rate_source,
        "warning": warning,
    }), 200
