import sqlite3
from decimal import Decimal

import pytest
import database
import init_db as init_db_script

def count(db_file, table):
    connection = database.get_connection(db_file)
    number = connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
    connection.close()
    return number

def test_init_creates_ten_tables(db_file):
    connection = database.get_connection(db_file)
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()
    connection.close()
    assert len(rows) == 12

def test_seed_data_is_loaded(db_file):
    assert count(db_file, "currency") == 6
    assert count(db_file, "investment_plan") == 3
    assert count(db_file, "tax_rule") == 3

def test_init_db_script_seeds_all_exchange_rates(tmp_path):
    path = str(tmp_path / "script.db")
    init_db_script.main(path)
    connection = database.get_connection(path)
    rows = connection.execute(
        "SELECT currency_code, rate_to_usd, source FROM exchange_rate ORDER BY currency_code"
    ).fetchall()
    connection.close()
    assert [row["currency_code"] for row in rows] == ["BRL", "EUR", "GBP", "JPY", "TRY", "USD"]
    assert all(row["source"] == "sample" for row in rows)

def test_running_init_twice_adds_nothing(db_file):
    database.init_db(db_file)
    assert count(db_file, "currency") == 6
    assert count(db_file, "exchange_rate") == 6
    assert count(db_file, "tax_rule") == 3

def test_list_currencies_has_six_in_code_order(db_file):
    codes = [c["code"] for c in database.list_currencies(db_file)]
    assert codes == ["BRL", "EUR", "GBP", "JPY", "TRY", "USD"]

def test_save_transaction_stores_a_row(db_file):
    transaction = {
        "from_currency": "GBP",
        "to_currency": "USD",
        "amount": Decimal("300"),
        "rate_used": Decimal("1.30"),
        "fee_percent": Decimal("3.5"),
        "fee_usd": Decimal("13.65"),
        "converted_amount": Decimal("390.00"),
    }
    new_id = database.save_transaction(1, transaction, db_file)
    assert new_id == 1
    assert count(db_file, "conversion_transaction") == 1

def test_foreign_key_blocks_unknown_user(db_file):
    transaction = {"from_currency": "GBP", "to_currency": "USD", "amount": 300, "rate_used": 1.3, "fee_percent": 3.5, "fee_usd": 13.65, "converted_amount": 390}
    with pytest.raises(sqlite3.IntegrityError):
        database.save_transaction(999, transaction, db_file)

def test_get_plans_returns_decimals_and_rules(db_file):
    plans = database.get_plans(db_file)
    assert [p["name"] for p in plans] == ["Basic Savings Plan", "Savings Plan Plus", "Managed Stock Investments"]
    assert plans[0]["min_lump_sum"] is None and plans[2]["max_per_year"] is None
    assert plans[1]["monthly_fee_pct"] == Decimal("0.3")
    assert plans[2]["tax_rules"] == [(Decimal("12000"), Decimal("10")), (Decimal("40000"), Decimal("20"))]
    assert plans[0]["tax_rules"] == []