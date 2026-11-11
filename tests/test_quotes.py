from decimal import Decimal                                             # Exact numbers

import pytest                                                           # For parametrize
import database                                                         # To load the plans from the test database
import quotes                                                           # The file we are testing

D = Decimal                                                             # A short name, to keep the numbers readable

@pytest.fixture                                                         # Set-up code the tests can ask for
def plans(db_file):                                                     # The three plans from the test database
    return database.get_plans(db_file)                                  # Load them

@pytest.mark.parametrize("profit, expected", [                          # Plan 3's tax rules: 10% above 12,000 and 20% above 40,000
    ("0", "0"),                                                         # No profit, no tax
    ("12000", "0"),                                                     # Exactly 12,000 is not above 12,000
    ("20000", "800"),                                                   # 10% of the 8,000 above 12,000
    ("40000", "2800"),                                                  # 10% of 28,000
    ("50000", "4800"),                                                  # 2,800 plus 20% of the 10,000 above 40,000
    ("-500", "0"),                                                      # A loss pays no tax
])                                                                      # End of the table
def test_marginal_tax_for_plan_3(plans, profit, expected):              # One run per row
    assert quotes.tax_for_profit(D(profit), plans[2]["tax_rules"]) == D(expected)  # plans[2] is Plan 3

def test_plan_1_has_no_tax(plans):                                      # Plan 1 tax is 0%
    assert quotes.tax_for_profit(D("5000"), plans[0]["tax_rules"]) == D("0")  # No rules, no tax

def test_one_month_by_hand(plans):                                      # Hand-checked: 1000 + 50 = 1050; interest 2.1; fee 0.25% of 1052.10
    balance, fees = quotes.simulate(plans[0], D("1000"), D("50"), 1, D("2.4"))  # Run one month
    assert balance == D("1049.46975")                                   # 1052.10 - 2.63025
    assert fees == D("2.63025")                                         # 0.25% of 1052.10

def test_plan_2_five_year_maximum(plans):                               # Checked against an independent calculation
    row = quotes.calculate_quote(plans[1], D("400"), D("100"), 5, "max")  # Plan 2, 400 lump sum, 100 a month, 5 years, best case
    assert row["contributed"] == D("6400.00")                           # 400 + 60 x 100
    assert row["final_value"] == D("6735.77")                           # Balance after fees; profit 335.77 is below the tax threshold
    assert row["total_profit"] == D("335.77")                           # Balance minus money paid in
    assert row["total_tax"] == D("0.00")                                # Under 12,000 profit

def test_plan_3_ten_year_maximum_pays_tax(plans):                       # Profit just over 12,000
    row = quotes.calculate_quote(plans[2], D("1000"), D("200"), 10, "max")  # Plan 3, best case, 10 years
    assert row["total_profit"] == D("12045.97")                         # Profit before tax
    assert row["total_tax"] == D("4.60")                                # 10% of the 45.97 above 12,000
    assert row["final_value"] == D("37041.37")                          # 37,045.97 minus 4.60
    assert row["total_fees"] == D("26970.69")                           # All the monthly fees added up

def test_plan_3_big_investor_pays_both_tax_bands(plans):                # Profit above 40,000
    row = quotes.calculate_quote(plans[2], D("5000"), D("1000"), 10, "max")  # Large amounts
    assert row["total_tax"] == D("6845.97")                             # 2,800 on the first band plus 20% of the rest
    assert row["final_value"] == D("178383.88")                         # Balance minus tax

def test_plan_1_loses_money_because_fees_exceed_returns(plans):         # 0.25% a month is 3% a year, more than the best 2.4% return
    row = quotes.calculate_quote(plans[0], D("0"), D("100"), 1, "max")  # Plan 1, best case, 1 year
    assert row["loss"] is True                                          # Flagged as a loss
    assert row["total_profit"] == D("-3.93")                            # Checked against an independent calculation
    assert row["total_tax"] == D("0.00")                                # No tax on a loss

def test_eligibility_reasons(plans):                                    # Each rule produces a message
    assert quotes.check_eligibility(plans[0], D("0"), D("40")) != []    # 40 is below the 50 minimum
    assert quotes.check_eligibility(plans[1], D("299.99"), D("50")) != []  # Lump sum below 300
    assert quotes.check_eligibility(plans[2], D("1000"), D("149.99")) != []  # Monthly below 150
    assert quotes.check_eligibility(plans[0], D("15000"), D("500")) != []  # 15,000 + 6,000 = 21,000 is over 20,000
    assert quotes.check_eligibility(plans[0], D("0"), D("50")) == []    # Plan 1 has no lump-sum minimum
    assert quotes.check_eligibility(plans[2], D("1000000"), D("5000")) == []  # Plan 3 has no yearly maximum

def test_build_quote_has_six_rows_per_eligible_plan(plans):             # Two scenarios times three time frames
    entries = quotes.build_quote(plans, D("1000"), D("200"))            # All three plans are available
    assert [len(e["results"]) for e in entries] == [6, 6, 6]            # Six rows each

@pytest.mark.parametrize("lump, monthly, expected", [                   # Who wins in different situations
    ("1000", "200", 3),                                                 # All plans available; Plan 3 has the best best-case value
    ("400", "100", 2),                                                  # Plan 3 needs 1,000 and 150; Plans 1 and 2 are left, and Plan 2 beats Plan 1
    ("0", "60", 1),                                                     # Only Plan 1 needs no lump sum
    ("15000", "500", 3),                                                # Plan 1 (over its yearly maximum) is out; Plan 3 beats Plan 2
])                                                                      # End of the table
def test_recommendation(plans, lump, monthly, expected):                # One run per row
    entries = quotes.build_quote(plans, D(lump), D(monthly))            # Build the quote
    assert quotes.recommend_plan(entries)["plan_id"] == expected        # The winner

def test_no_plan_available_gives_none(plans):                           # Monthly 40 is below every minimum
    entries = quotes.build_quote(plans, D("0"), D("40"))                # Build the quote
    assert quotes.recommend_plan(entries) is None                       # No recommendation

def test_serialise_makes_text(plans):                                   # Decimals must become text for JSON
    entries = quotes.build_quote(plans, D("1000"), D("200"))            # Build the quote
    row = quotes.serialise(entries)[0]["results"][0]                    # The first result row of Plan 1
    assert isinstance(row["final_value"], str)                          # Text
    assert len(row["final_value"].split(".")[1]) == 2                   # Two decimal places