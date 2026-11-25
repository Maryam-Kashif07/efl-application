import json
import urllib.request
from decimal import Decimal, ROUND_HALF_UP

import config
import database
import diagnostics

TWO_PLACES = Decimal("0.01")
SIX_PLACES = Decimal("0.000001")

def round_money(value):
    """Round to 2 decimal places, halves rounded up."""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

def get_rate(from_code, to_code, db_file=None):
    """Return the rate from one currency to another, rounded to 6 places."""
    from_usd = database.get_rate_to_usd(from_code, db_file)
    to_usd = database.get_rate_to_usd(to_code, db_file)
    return (from_usd / to_usd).quantize(SIX_PLACES, rounding=ROUND_HALF_UP)

def convert(amount, rate):
    """Return the converted amount rounded to 2 decimal places."""
    return round_money(amount * rate)

def fetch_live_rates():
    """Return US dollars per unit for each of our six currencies."""
    with urllib.request.urlopen(config.RATE_URL, timeout=config.RATE_TIMEOUT_SECONDS) as reply:
        payload = json.loads(reply.read().decode("utf-8"))
    per_dollar = payload["rates"]
    return {code: Decimal("1") / Decimal(str(per_dollar[code])) for code in config.CURRENCIES}

def refresh_rates(db_file=None):
    """Try the live service. On failure log it to a file and return a warning."""
    if not config.USE_LIVE_RATES:
        return None
    if database.has_fresh_live_rate(db_file):
        return None
    try:
        rates = fetch_live_rates()
    except Exception as problem:
        diagnostics.log_to_file("Network failure while loading exchange rates: " + repr(problem))
        latest = database.latest_rate_time(db_file)
        return "Live exchange rates are unavailable, so the most recent saved rates (" + str(latest) + " UTC) were used."
    database.save_rates(rates, "live", db_file)
    return None