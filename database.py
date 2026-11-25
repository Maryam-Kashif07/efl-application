import json
import sqlite3
from decimal import Decimal
from pathlib import Path

import config
from errors import RateUnavailableError

BASE_DIR = Path(__file__).parent

def get_connection(db_file=None):
    connection = sqlite3.connect(db_file or config.DB_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def init_db(db_file=None):
    script = (BASE_DIR / "schema.sql").read_text(encoding="utf-8")
    connection = get_connection(db_file)
    connection.executescript(script)
    seed_reference_data(connection)
    connection.commit()
    connection.close()

def seed_reference_data(connection):
    for code in config.CURRENCIES:
        name, symbol = config.CURRENCY_NAMES[code]
        connection.execute(
            "INSERT OR IGNORE INTO currency (currency_code, name, symbol) VALUES (?, ?, ?)",
            (code, name, symbol),
        )
        has_rate = connection.execute(
            "SELECT 1 FROM exchange_rate WHERE currency_code = ?", (code,)
        ).fetchone()
        if has_rate is None:
            connection.execute(
                "INSERT INTO exchange_rate (currency_code, rate_to_usd, source) VALUES (?, ?, 'sample')",
                (code, float(config.SAMPLE_RATES_TO_USD[code])),
            )
    for plan in config.PLANS:
        connection.execute(
            "INSERT OR IGNORE INTO investment_plan VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            plan,
        )
    has_rules = connection.execute("SELECT 1 FROM tax_rule").fetchone()
    if has_rules is None:
        connection.executemany(
            "INSERT INTO tax_rule (plan_id, profit_above, tax_rate_pct) VALUES (?, ?, ?)",
            config.TAX_RULES,
        )
    connection.execute(
        "INSERT OR IGNORE INTO user (user_id, name, email, password_hash) VALUES (?, 'Demo user', 'demo@efl.test', 'not-set')",
        (config.DEMO_USER_ID,),
    )

def get_rate_to_usd(currency_code, db_file=None):
    connection = get_connection(db_file)
    try:
        row = connection.execute(
            "SELECT rate_to_usd FROM exchange_rate WHERE currency_code = ? ORDER BY fetched_at DESC, rate_id DESC LIMIT 1",
            (currency_code,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise RateUnavailableError("No exchange rate is available for " + str(currency_code) + ".")
    return Decimal(str(row["rate_to_usd"]))

def list_currencies(db_file=None):
    connection = get_connection(db_file)
    try:
        rows = connection.execute(
            "SELECT currency_code, name, symbol FROM currency WHERE is_active = 1 ORDER BY currency_code"
        ).fetchall()
    finally:
        connection.close()
    return [{"code": r["currency_code"], "name": r["name"], "symbol": r["symbol"]} for r in rows]

def save_transaction(user_id, transaction, db_file=None):
    connection = get_connection(db_file)
    try:
        cursor = connection.execute(
            "INSERT INTO conversion_transaction (user_id, from_currency, to_currency, amount, rate_used, fee_percent, fee_usd, converted_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                transaction["from_currency"],
                transaction["to_currency"],
                float(transaction["amount"]),
                float(transaction["rate_used"]),
                float(transaction["fee_percent"]),
                float(transaction["fee_usd"]),
                float(transaction["converted_amount"]),
            ),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()

def get_plans(db_file=None):
    """Return the plans as dictionaries holding Decimal values."""
    connection = get_connection(db_file)
    try:
        plan_rows = connection.execute("SELECT * FROM investment_plan ORDER BY plan_id").fetchall()
        rule_rows = connection.execute("SELECT plan_id, profit_above, tax_rate_pct FROM tax_rule ORDER BY plan_id, profit_above").fetchall()
    finally:
        connection.close()
    plans = []
    for row in plan_rows:
        rules = [(Decimal(str(r["profit_above"])), Decimal(str(r["tax_rate_pct"]))) for r in rule_rows if r["plan_id"] == row["plan_id"]]
        plans.append({
            "plan_id": row["plan_id"],
            "name": row["name"],
            "max_per_year": None if row["max_per_year"] is None else Decimal(str(row["max_per_year"])),
            "min_monthly": Decimal(str(row["min_monthly"])),
            "min_lump_sum": None if row["min_lump_sum"] is None else Decimal(str(row["min_lump_sum"])),
            "return_min_pct": Decimal(str(row["return_min_pct"])),
            "return_max_pct": Decimal(str(row["return_max_pct"])),
            "monthly_fee_pct": Decimal(str(row["monthly_fee_pct"])),
            "tax_rules": rules,
        })
    return plans

def save_quote(user_id, plan_id, recommended_plan_id, lump_sum, monthly, rows, db_file=None):
    """Insert a quote and its result rows, and return the quote id."""
    connection = get_connection(db_file)
    try:
        cursor = connection.execute(
            "INSERT INTO quote (user_id, plan_id, recommended_plan_id, lump_sum, monthly_amount) VALUES (?, ?, ?, ?, ?)",
            (user_id, plan_id, recommended_plan_id, float(lump_sum), float(monthly)),
        )
        quote_id = cursor.lastrowid
        for row in rows:
            connection.execute(
                "INSERT INTO quote_result (quote_id, scenario, years, final_value, total_profit, total_fees, total_tax) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (quote_id, row["scenario"], row["years"], float(row["final_value"]), float(row["total_profit"]), float(row["total_fees"]), float(row["total_tax"])),
            )
        connection.commit()
        return quote_id
    finally:
        connection.close()

def mark_quote_saved(quote_id, user_id, db_file=None):
    """Set is_saved for this user's quote. Return True if a row changed."""
    connection = get_connection(db_file)
    try:
        cursor = connection.execute("UPDATE quote SET is_saved = 1 WHERE quote_id = ? AND user_id = ?", (quote_id, user_id))
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()

def log_error(source, message, db_file=None):
    """Record an internal error with its diagnostic data."""
    connection = get_connection(db_file)
    try:
        connection.execute("INSERT INTO error_log (source, message) VALUES (?, ?)", (source, message))
        connection.commit()
    finally:
        connection.close()

def create_user(name, email, phone, password_hash, db_file=None):
    """Insert a user and return the new user id."""
    connection = get_connection(db_file)
    try:
        cursor = connection.execute("INSERT INTO user (name, email, phone, password_hash) VALUES (?, ?, ?, ?)", (name, email, phone, password_hash))
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()

def get_user_by_email(email, db_file=None):
    """Return the user row as a dictionary, or None."""
    connection = get_connection(db_file)
    try:
        row = connection.execute("SELECT user_id, name, email, password_hash FROM user WHERE email = ?", (email,)).fetchone()
    finally:
        connection.close()
    return dict(row) if row else None

def has_fresh_live_rate(db_file=None):
    """True if a live rate younger than RATE_MAX_AGE_MINUTES is stored."""
    connection = get_connection(db_file)
    try:
        row = connection.execute("SELECT 1 FROM exchange_rate WHERE source = 'live' AND fetched_at > datetime('now', ?) LIMIT 1", ("-" + str(config.RATE_MAX_AGE_MINUTES) + " minutes",)).fetchone()
    finally:
        connection.close()
    return row is not None

def save_rates(rates, source, db_file=None):
    """Insert one exchange_rate row for each currency in the dictionary."""
    connection = get_connection(db_file)
    try:
        for code, rate in rates.items():
            connection.execute("INSERT INTO exchange_rate (currency_code, rate_to_usd, source) VALUES (?, ?, ?)", (code, float(rate), source))
        connection.commit()
    finally:
        connection.close()

def latest_rate_time(db_file=None):
    """Return the newest fetched_at text, or None."""
    connection = get_connection(db_file)
    try:
        row = connection.execute("SELECT MAX(fetched_at) AS latest FROM exchange_rate").fetchone()
    finally:
        connection.close()
    return row["latest"]

def get_history(user_id, db_file=None):
    """Return the user's transactions and saved quotes."""
    connection = get_connection(db_file)
    try:
        transactions = connection.execute("SELECT transaction_id, created_at, from_currency, to_currency, amount, rate_used, fee_percent, fee_usd, converted_amount FROM conversion_transaction WHERE user_id = ? ORDER BY transaction_id DESC LIMIT 100", (user_id,)).fetchall()
        quote_rows = connection.execute("SELECT q.quote_id, q.created_at, q.lump_sum, q.monthly_amount, p.name AS plan_name FROM quote q JOIN investment_plan p ON p.plan_id = q.plan_id WHERE q.user_id = ? AND q.is_saved = 1 ORDER BY q.quote_id DESC", (user_id,)).fetchall()
        quotes_out = []
        for q in quote_rows:
            results = connection.execute("SELECT scenario, years, final_value, total_profit, total_fees, total_tax FROM quote_result WHERE quote_id = ? ORDER BY scenario, years", (q["quote_id"],)).fetchall()
            quotes_out.append({**dict(q), "results": [dict(r) for r in results]})
    finally:
        connection.close()
    return {"transactions": [dict(t) for t in transactions], "quotes": quotes_out}

def save_draft(user_id, form_data, db_file=None):
    """Insert a draft and return its id."""
    connection = get_connection(db_file)
    try:
        cursor = connection.execute("INSERT INTO draft (user_id, form_data) VALUES (?, ?)", (user_id, json.dumps(form_data)))
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()

def get_draft(draft_id, user_id, db_file=None):
    """Return the draft's form data, or None."""
    connection = get_connection(db_file)
    try:
        row = connection.execute("SELECT form_data FROM draft WHERE draft_id = ? AND user_id = ?", (draft_id, user_id)).fetchone()
    finally:
        connection.close()
    return json.loads(row["form_data"]) if row else None

def latest_rate_info(db_file=None):
    connection = get_connection(db_file)
    try:
        row = connection.execute("SELECT fetched_at, source FROM exchange_rate ORDER BY fetched_at DESC, rate_id DESC LIMIT 1").fetchone()
    finally:
        connection.close()
    if row is None:
        return {"fetched_at": None, "source": None}
    return {"fetched_at": row["fetched_at"], "source": row["source"]}


def get_dashboard(user_id, db_file=None):
    connection = get_connection(db_file)
    try:
        user = connection.execute("SELECT name FROM user WHERE user_id = ?", (user_id,)).fetchone()
        recent = connection.execute("SELECT created_at, from_currency, to_currency, amount, converted_amount FROM conversion_transaction WHERE user_id = ? ORDER BY transaction_id DESC LIMIT 5", (user_id,)).fetchall()
        saved = connection.execute("SELECT COUNT(*) AS total FROM quote WHERE user_id = ? AND is_saved = 1", (user_id,)).fetchone()
        latest = connection.execute("SELECT p.name FROM quote q JOIN investment_plan p ON p.plan_id = q.recommended_plan_id WHERE q.user_id = ? ORDER BY q.quote_id DESC LIMIT 1", (user_id,)).fetchone()
    finally:
        connection.close()
    return {
        "name": user["name"] if user else "",
        "recent": [dict(r) for r in recent],
        "saved_quotes": saved["total"],
        "recommended_plan": latest["name"] if latest else None,
    }


def record_failed_login(email, db_file=None):
    connection = get_connection(db_file)
    try:
        connection.execute("DELETE FROM login_attempt WHERE attempted_at < datetime('now', '-1 day')")
        connection.execute("INSERT INTO login_attempt (email) VALUES (?)", (email,))
        connection.commit()
    finally:
        connection.close()


def count_recent_failures(email, db_file=None):
    connection = get_connection(db_file)
    try:
        row = connection.execute("SELECT COUNT(*) AS total FROM login_attempt WHERE email = ? AND attempted_at > datetime('now', ?)", (email, "-" + str(config.LOGIN_LOCK_MINUTES) + " minutes")).fetchone()
    finally:
        connection.close()
    return row["total"]


def clear_failed_logins(email, db_file=None):
    connection = get_connection(db_file)
    try:
        connection.execute("DELETE FROM login_attempt WHERE email = ?", (email,))
        connection.commit()
    finally:
        connection.close()


def create_password_reset(user_id, token_hash, db_file=None):
    connection = get_connection(db_file)
    try:
        connection.execute("INSERT INTO password_reset (user_id, token_hash, expires_at) VALUES (?, ?, datetime('now', ?))", (user_id, token_hash, "+" + str(config.RESET_TOKEN_MINUTES) + " minutes"))
        connection.commit()
    finally:
        connection.close()


def reset_password_with_token(token_hash, password_hash, db_file=None):
    connection = get_connection(db_file)
    try:
        row = connection.execute("SELECT r.user_id, u.email FROM password_reset r JOIN user u ON u.user_id = r.user_id WHERE r.token_hash = ? AND r.used = 0 AND r.expires_at > datetime('now')", (token_hash,)).fetchone()
        if row is None:
            return None
        connection.execute("UPDATE user SET password_hash = ? WHERE user_id = ?", (password_hash, row["user_id"]))
        connection.execute("UPDATE password_reset SET used = 1 WHERE user_id = ?", (row["user_id"],))
        connection.execute("DELETE FROM login_attempt WHERE email = ?", (row["email"],))
        connection.commit()
        return row["email"]
    finally:
        connection.close()

def delete_transaction(transaction_id, user_id, db_file=None):
    connection = get_connection(db_file)
    try:
        cursor = connection.execute("DELETE FROM conversion_transaction WHERE transaction_id = ? AND user_id = ?", (transaction_id, user_id))
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()
