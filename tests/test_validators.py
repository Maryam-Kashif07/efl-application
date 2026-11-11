"""Tests for input validation."""                                       # Docstring: what is tested
from decimal import Decimal                                             # Exact numbers

import pytest                                                           # For parametrize and raises
import validators                                                       # The file we are testing
from errors import InputError                                           # The error we expect for bad input

@pytest.mark.parametrize("text, expected", [                            # Valid amounts and what they should become
    ("300", Decimal("300")),                                            # The minimum is allowed
    ("5000", Decimal("5000")),                                          # The maximum is allowed
    (" 750.50 ", Decimal("750.50")),                                    # Spaces are removed
    (1200, Decimal("1200")),                                            # A number, not text, also works
])                                                                      # End of the table
def test_valid_amounts(text, expected):                                 # One run per row
    assert validators.validate_amount(text) == expected                 # The clean Decimal comes back

@pytest.mark.parametrize("text", ["299.99", "5000.01", "0", "-500", "abc", "", "NaN", "Infinity", "100.123", None])  # Every kind of bad input we thought of
def test_invalid_amounts_raise_input_error(text):                       # One run per bad value
    with pytest.raises(InputError):                                     # Each must be rejected
        validators.validate_amount(text)                                # Try the bad value

def test_message_names_the_limits():                                    # The message must help the user
    with pytest.raises(InputError) as problem:                          # Keep the error so we can read its message
        validators.validate_amount("100")                               # Below the minimum
    assert "300" in str(problem.value) and "5,000" in str(problem.value)  # The message contains both limits

def test_currency_is_cleaned_and_checked():                             # Currency codes
    assert validators.validate_currency(" gbp ") == "GBP"               # Spaces and lower case are fixed
    with pytest.raises(InputError):                                     # Unknown code
        validators.validate_currency("ABC")                             # Not one of the six

@pytest.mark.parametrize("text", ["abc", "", "-1", "NaN", "10.001", "99999999999", None])  # NEW: bad money amounts for the quote page
def test_invalid_money_raises_input_error(text):                        # One run per bad value
    with pytest.raises(InputError):                                     # Each must be rejected
        validators.validate_money(text, "lump sum")                     # Try it

def test_valid_money_allows_zero_and_two_places():                      # NEW: good amounts
    assert validators.validate_money("0", "lump sum") == Decimal("0")   # Zero lump sum is fine
    assert validators.validate_money("250.50", "monthly amount") == Decimal("250.50")  # Two decimal places are fine

def test_plan_id_must_exist(db_file):                                   # NEW: the chosen plan must be real
    import database                                                     # Imported here because only this test needs it
    plans = database.get_plans(db_file)                                 # Load the plans
    assert validators.validate_plan_id("2", plans)["plan_id"] == 2      # A real plan
    for bad in ["9", "x", None]:                                        # Three bad choices
        with pytest.raises(InputError):                                 # Each must be rejected
            validators.validate_plan_id(bad, plans)                     # Try it

def test_quote_inputs_must_meet_plan_rules(db_file):                    # NEW: the plan's rules are enforced
    import database                                                     # Imported here because only this test needs it
    plans = database.get_plans(db_file)                                 # Load the plans
    with pytest.raises(InputError) as problem:                          # Plan 2 needs a 300 lump sum
        validators.validate_quote_inputs(plans[1], Decimal("100"), Decimal("50"))  # Lump sum too small
    assert "300.00" in str(problem.value)                               # The message names the minimum