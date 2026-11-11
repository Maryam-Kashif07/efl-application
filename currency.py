import json                                 # NEW: to read the rate service's reply
import urllib.request                       # NEW: Python's built-in web client
from decimal import Decimal, ROUND_HALF_UP  # ROUND_HALF_UP is the school rule: 2.675 rounds to 2.68

import config                               # NEW: the rate service settings
import database                             # We read rates through the database file
import diagnostics

TWO_PLACES = Decimal("0.01")                                            # The shape of a money amount: two decimal places
SIX_PLACES = Decimal("0.000001")                                        # The shape of a rate: six decimal places (matches the data dictionary)

def round_money(value):                                                 # Round any amount to two decimal places
    """Round to 2 decimal places, halves rounded up."""                 # Docstring
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)           # quantize forces the shape of TWO_PLACES

def get_rate(from_code, to_code, db_file=None):                         # Rate for 1 unit of from_code, in to_code
    """Return the rate from one currency to another, rounded to 6 places."""  # Docstring
    from_usd = database.get_rate_to_usd(from_code, db_file)             # US dollars per 1 unit of the first currency
    to_usd = database.get_rate_to_usd(to_code, db_file)                 # US dollars per 1 unit of the second currency
    return (from_usd / to_usd).quantize(SIX_PLACES, rounding=ROUND_HALF_UP)  # Go through US dollars: the dollars cancel out, leaving first-to-second

def convert(amount, rate):                                              # Apply a rate to an amount
    """Return the converted amount rounded to 2 decimal places."""      # Docstring
    return round_money(amount * rate)                                   # Multiply, then round once at the end

def fetch_live_rates():                                                 # Download the current rates
    """Return US dollars per unit for each of our six currencies."""    # Docstring
    with urllib.request.urlopen(config.RATE_URL, timeout=config.RATE_TIMEOUT_SECONDS) as reply:  # Call the rate service; give up after the timeout
        payload = json.loads(reply.read().decode("utf-8"))              # Read the reply and turn the JSON into a dictionary
    per_dollar = payload["rates"]                                       # The service gives units of each currency per one US dollar
    return {code: Decimal("1") / Decimal(str(per_dollar[code])) for code in config.CURRENCIES}  # We store the opposite: dollars per unit, so divide 1 by it

def refresh_rates(db_file=None):                                        # Load fresh rates before converting
    """Try the live service. On failure log it to a file and return a warning."""  # Docstring
    if not config.USE_LIVE_RATES:                                       # Live rates are switched off
        return None                                                     # No warning needed
    if database.has_fresh_live_rate(db_file):                           # We loaded rates a few minutes ago
        return None                                                     # Reuse them
    try:                                                                # The network may fail
        rates = fetch_live_rates()                                      # Download the rates
    except Exception as problem:                                        # Any failure: no network, timeout, bad reply
        diagnostics.log_to_file("Network failure while loading exchange rates: " + repr(problem))  # Network failure: save the diagnostic data to the local file system
        latest = database.latest_rate_time(db_file)                     # When were the saved rates updated?
        return "Live exchange rates are unavailable, so the most recent saved rates (" + str(latest) + " UTC) were used."  # The warning the user sees
    database.save_rates(rates, "live", db_file)                         # Keep the new rates; they become the saved rates for next time
    return None                                                         # No warning
