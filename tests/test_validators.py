from decimal import Decimal

import pytest
import validators
from errors import InputError

@pytest.mark.parametrize("text, expected", [
    ("300", Decimal("300")),
    ("5000", Decimal("5000")),
    (" 750.50 ", Decimal("750.50")),
    (1200, Decimal("1200")),
])
def test_valid_amounts(text, expected):
    assert validators.validate_amount(text) == expected

@pytest.mark.parametrize("text", ["299.99", "5000.01", "0", "-500", "abc", "", "NaN", "Infinity", "100.123", None])
def test_invalid_amounts_raise_input_error(text):
    with pytest.raises(InputError):
        validators.validate_amount(text)

def test_message_names_the_limits():
    with pytest.raises(InputError) as problem:
        validators.validate_amount("100")
    assert "300" in str(problem.value) and "5,000" in str(problem.value)

def test_currency_is_cleaned_and_checked():
    assert validators.validate_currency(" gbp ") == "GBP"
    with pytest.raises(InputError):
        validators.validate_currency("ABC")

@pytest.mark.parametrize("text", ["abc", "", "-1", "NaN", "10.001", "99999999999", None])
def test_invalid_money_raises_input_error(text):
    with pytest.raises(InputError):
        validators.validate_money(text, "lump sum")

def test_valid_money_allows_zero_and_two_places():
    assert validators.validate_money("0", "lump sum") == Decimal("0")
    assert validators.validate_money("250.50", "monthly amount") == Decimal("250.50")

def test_plan_id_must_exist(db_file):
    import database
    plans = database.get_plans(db_file)
    assert validators.validate_plan_id("2", plans)["plan_id"] == 2
    for bad in ["9", "x", None]:
        with pytest.raises(InputError):
            validators.validate_plan_id(bad, plans)

def test_quote_inputs_must_meet_plan_rules(db_file):
    import database
    plans = database.get_plans(db_file)
    with pytest.raises(InputError) as problem:
        validators.validate_quote_inputs(plans[1], Decimal("100"), Decimal("50"))
    assert "300.00" in str(problem.value)