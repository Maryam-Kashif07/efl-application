from decimal import Decimal

import pytest
import database
import quotes

D = Decimal

@pytest.fixture
def plans(db_file):
    return database.get_plans(db_file)

@pytest.mark.parametrize("profit, expected", [
    ("0", "0"),
    ("12000", "0"),
    ("20000", "800"),
    ("40000", "2800"),
    ("50000", "4800"),
    ("-500", "0"),
])
def test_marginal_tax_for_plan_3(plans, profit, expected):
    assert quotes.tax_for_profit(D(profit), plans[2]["tax_rules"]) == D(expected)

def test_plan_1_has_no_tax(plans):
    assert quotes.tax_for_profit(D("5000"), plans[0]["tax_rules"]) == D("0")

def test_one_month_by_hand(plans):
    balance, fees = quotes.simulate(plans[0], D("1000"), D("50"), 1, D("2.4"))
    assert balance == D("1049.46975")
    assert fees == D("2.63025")

def test_plan_2_five_year_maximum(plans):
    row = quotes.calculate_quote(plans[1], D("400"), D("100"), 5, "max")
    assert row["contributed"] == D("6400.00")
    assert row["final_value"] == D("6735.77")
    assert row["total_profit"] == D("335.77")
    assert row["total_tax"] == D("0.00")

def test_plan_3_ten_year_maximum_pays_tax(plans):
    row = quotes.calculate_quote(plans[2], D("1000"), D("200"), 10, "max")
    assert row["total_profit"] == D("12045.97")
    assert row["total_tax"] == D("4.60")
    assert row["final_value"] == D("37041.37")
    assert row["total_fees"] == D("26970.69")

def test_plan_3_big_investor_pays_both_tax_bands(plans):
    row = quotes.calculate_quote(plans[2], D("5000"), D("1000"), 10, "max")
    assert row["total_tax"] == D("6845.97")
    assert row["final_value"] == D("178383.88")

def test_plan_1_loses_money_because_fees_exceed_returns(plans):
    row = quotes.calculate_quote(plans[0], D("0"), D("100"), 1, "max")
    assert row["loss"] is True
    assert row["total_profit"] == D("-3.93")
    assert row["total_tax"] == D("0.00")

def test_eligibility_reasons(plans):
    assert quotes.check_eligibility(plans[0], D("0"), D("40")) != []
    assert quotes.check_eligibility(plans[1], D("299.99"), D("50")) != []
    assert quotes.check_eligibility(plans[2], D("1000"), D("149.99")) != []
    assert quotes.check_eligibility(plans[0], D("15000"), D("500")) != []
    assert quotes.check_eligibility(plans[0], D("0"), D("50")) == []
    assert quotes.check_eligibility(plans[2], D("1000000"), D("5000")) == []

def test_build_quote_has_six_rows_per_eligible_plan(plans):
    entries = quotes.build_quote(plans, D("1000"), D("200"))
    assert [len(e["results"]) for e in entries] == [6, 6, 6]

@pytest.mark.parametrize("lump, monthly, expected", [
    ("1000", "200", 3),
    ("400", "100", 2),
    ("0", "60", 1),
    ("15000", "500", 3),
])
def test_recommendation(plans, lump, monthly, expected):
    entries = quotes.build_quote(plans, D(lump), D(monthly))
    assert quotes.recommend_plan(entries)["plan_id"] == expected

def test_no_plan_available_gives_none(plans):
    entries = quotes.build_quote(plans, D("0"), D("40"))
    assert quotes.recommend_plan(entries) is None

def test_serialise_makes_text(plans):
    entries = quotes.build_quote(plans, D("1000"), D("200"))
    row = quotes.serialise(entries)[0]["results"][0]
    assert isinstance(row["final_value"], str)
    assert len(row["final_value"].split(".")[1]) == 2