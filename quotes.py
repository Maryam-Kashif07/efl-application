from decimal import Decimal

import config
from currency import round_money

HUNDRED = Decimal("100")
TWELVE = Decimal("12")
ZERO = Decimal("0")

def tax_for_profit(profit, tax_rules):
    """Marginal tax: each rate applies only to the slice of profit above its threshold."""
    if profit <= 0:
        return ZERO
    rules = sorted(tax_rules)
    tax = ZERO
    for index, (above, rate) in enumerate(rules):
        upper = rules[index + 1][0] if index + 1 < len(rules) else profit
        top = min(profit, upper)
        if top > above:
            tax += (top - above) * rate / HUNDRED
    return tax

def simulate(plan, lump_sum, monthly, months, annual_rate_pct):
    """Return (balance, total_fees) after the given number of months."""
    monthly_rate = annual_rate_pct / HUNDRED / TWELVE
    fee_rate = plan["monthly_fee_pct"] / HUNDRED
    balance = lump_sum
    total_fees = ZERO
    for _ in range(months):
        balance += monthly
        balance += balance * monthly_rate
        fee = balance * fee_rate
        balance -= fee
        total_fees += fee
    return balance, total_fees

def calculate_quote(plan, lump_sum, monthly, years, scenario):
    """Return final value, profit, fees and tax. Scenario is 'min' or 'max'."""
    rate = plan["return_min_pct"] if scenario == "min" else plan["return_max_pct"]
    months = years * 12
    balance, fees = simulate(plan, lump_sum, monthly, months, rate)
    contributed = lump_sum + monthly * months
    profit = balance - contributed
    tax = tax_for_profit(profit, plan["tax_rules"])
    return {
        "scenario": scenario,
        "years": years,
        "contributed": round_money(contributed),
        "final_value": round_money(balance - tax),
        "total_profit": round_money(profit),
        "total_fees": round_money(fees),
        "total_tax": round_money(tax),
        "loss": profit < 0,
    }

def check_eligibility(plan, lump_sum, monthly):
    """Return a list of reasons the plan is not available. Empty means eligible."""
    reasons = []
    if monthly < plan["min_monthly"]:
        reasons.append(f"{plan['name']}: the minimum monthly investment is £{plan['min_monthly']:,.2f}.")
    if plan["min_lump_sum"] is not None and lump_sum < plan["min_lump_sum"]:
        reasons.append(f"{plan['name']}: the minimum initial lump sum is £{plan['min_lump_sum']:,.2f}.")
    first_year = lump_sum + monthly * 12
    if plan["max_per_year"] is not None and first_year > plan["max_per_year"]:
        reasons.append(f"{plan['name']}: the maximum investment per year is £{plan['max_per_year']:,.2f}; your first year would be £{first_year:,.2f}.")
    return reasons

def build_quote(plans, lump_sum, monthly):
    """Return one entry per plan with eligibility and the 1, 5 and 10 year results."""
    entries = []
    for plan in plans:
        reasons = check_eligibility(plan, lump_sum, monthly)
        rows = []
        if not reasons:
            for scenario in ("min", "max"):
                for years in config.YEARS:
                    rows.append(calculate_quote(plan, lump_sum, monthly, years, scenario))
        entries.append({"plan_id": plan["plan_id"], "name": plan["name"], "eligible": not reasons, "reasons": reasons, "results": rows})
    return entries

def recommend_plan(entries):
    """Highest after-tax value after 10 years in the maximum scenario, among eligible plans."""
    best = None
    best_value = None
    for entry in entries:
        if not entry["eligible"]:
            continue
        row = next(r for r in entry["results"] if r["scenario"] == "max" and r["years"] == 10)
        if best_value is None or row["final_value"] > best_value:
            best, best_value = entry, row["final_value"]
    return best

def serialise(entries):
    """Turn every Decimal into text with two decimal places."""
    clean = []
    for entry in entries:
        rows = []
        for row in entry["results"]:
            rows.append({key: (str(value) if isinstance(value, Decimal) else value) for key, value in row.items()})
        clean.append({**entry, "results": rows})
    return clean