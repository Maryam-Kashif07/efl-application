from decimal import Decimal                                             # Exact money maths

import config                                                           # The list of years lives in config.py
from currency import round_money                                        # Reuse the 2-decimal rounding rule

HUNDRED = Decimal("100")                                                # To turn percentages into fractions
TWELVE = Decimal("12")                                                  # Months in a year
ZERO = Decimal("0")                                                     # A Decimal zero

def tax_for_profit(profit, tax_rules):                                  # Tax on the total profit of one time frame
    """Marginal tax: each rate applies only to the slice of profit above its threshold."""  # Docstring
    if profit <= 0:                                                     # No profit, no tax
        return ZERO                                                     # Zero tax
    rules = sorted(tax_rules)                                           # Lowest threshold first
    tax = ZERO                                                          # Running total
    for index, (above, rate) in enumerate(rules):                       # Look at each tax band in turn
        upper = rules[index + 1][0] if index + 1 < len(rules) else profit  # The band ends where the next one starts, or at the profit
        top = min(profit, upper)                                        # The profit that falls inside this band cannot go past the end of it
        if top > above:                                                 # Is there any profit inside this band?
            tax += (top - above) * rate / HUNDRED                       # Tax only that slice
    return tax                                                          # Total tax

def simulate(plan, lump_sum, monthly, months, annual_rate_pct):         # Run the account month by month
    """Return (balance, total_fees) after the given number of months."""  # Docstring
    monthly_rate = annual_rate_pct / HUNDRED / TWELVE                   # Yearly percentage to a monthly fraction
    fee_rate = plan["monthly_fee_pct"] / HUNDRED                        # Monthly fee as a fraction
    balance = lump_sum                                                  # The lump sum goes in at month 0
    total_fees = ZERO                                                   # Fees paid so far
    for _ in range(months):                                             # One loop for each month
        balance += monthly                                              # The monthly amount is paid in
        balance += balance * monthly_rate                               # Interest for the month, compounded
        fee = balance * fee_rate                                        # The fee is a percentage of the current balance
        balance -= fee                                                  # Take the fee off
        total_fees += fee                                               # Add it to the fees paid
    return balance, total_fees                                          # The balance and the fees

def calculate_quote(plan, lump_sum, monthly, years, scenario):          # One result row: one scenario, one time frame
    """Return final value, profit, fees and tax. Scenario is 'min' or 'max'."""  # Docstring
    rate = plan["return_min_pct"] if scenario == "min" else plan["return_max_pct"]  # Lowest or highest predicted return
    months = years * 12                                                 # Years to months
    balance, fees = simulate(plan, lump_sum, monthly, months, rate)     # Run the account
    contributed = lump_sum + monthly * months                           # Everything the user paid in
    profit = balance - contributed                                      # Profit after fees, before tax; a loss is negative
    tax = tax_for_profit(profit, plan["tax_rules"])                     # Tax once, on the total profit
    return {                                                            # The result row
        "scenario": scenario,                                           # min or max
        "years": years,                                                 # 1, 5 or 10
        "contributed": round_money(contributed),                        # Money paid in
        "final_value": round_money(balance - tax),                      # Value after fees and tax
        "total_profit": round_money(profit),                            # Profit in the period
        "total_fees": round_money(fees),                                # Fees paid in the period
        "total_tax": round_money(tax),                                  # Tax paid in the period
        "loss": profit < 0,                                             # True when fees and returns leave the user worse off
    }                                                                   # End of the row

def check_eligibility(plan, lump_sum, monthly):                         # Does this user meet the plan's rules?
    """Return a list of reasons the plan is not available. Empty means eligible."""  # Docstring
    reasons = []                                                        # Collect every problem, not just the first
    if monthly < plan["min_monthly"]:                                   # Monthly amount too small
        reasons.append(f"{plan['name']}: the minimum monthly investment is £{plan['min_monthly']:,.2f}.")  # Message with the limit
    if plan["min_lump_sum"] is not None and lump_sum < plan["min_lump_sum"]:  # Lump sum too small (None means N/A)
        reasons.append(f"{plan['name']}: the minimum initial lump sum is £{plan['min_lump_sum']:,.2f}.")  # Message with the limit
    first_year = lump_sum + monthly * 12                                # Year one is the biggest: lump sum plus twelve payments
    if plan["max_per_year"] is not None and first_year > plan["max_per_year"]:  # Over the yearly maximum (None means unlimited)
        reasons.append(f"{plan['name']}: the maximum investment per year is £{plan['max_per_year']:,.2f}; your first year would be £{first_year:,.2f}.")  # Message with both numbers
    return reasons                                                      # The list, possibly empty

def build_quote(plans, lump_sum, monthly):                              # Results for every plan
    """Return one entry per plan with eligibility and the 1, 5 and 10 year results."""  # Docstring
    entries = []                                                        # The answer
    for plan in plans:                                                  # Every plan
        reasons = check_eligibility(plan, lump_sum, monthly)            # Is it available to this user?
        rows = []                                                       # Result rows for this plan
        if not reasons:                                                 # Only calculate eligible plans
            for scenario in ("min", "max"):                             # Lowest and highest return
                for years in config.YEARS:                              # 1, 5 and 10 years
                    rows.append(calculate_quote(plan, lump_sum, monthly, years, scenario))  # Add the row
        entries.append({"plan_id": plan["plan_id"], "name": plan["name"], "eligible": not reasons, "reasons": reasons, "results": rows})  # One entry per plan
    return entries                                                      # The finished list

def recommend_plan(entries):                                            # Pick the best plan
    """Highest after-tax value after 10 years in the maximum scenario, among eligible plans."""  # Docstring
    best = None                                                         # Best entry so far
    best_value = None                                                   # Its value
    for entry in entries:                                               # Every plan
        if not entry["eligible"]:                                       # Skip plans the user cannot have
            continue                                                    # Next plan
        row = next(r for r in entry["results"] if r["scenario"] == "max" and r["years"] == 10)  # Find the 10-year maximum row
        if best_value is None or row["final_value"] > best_value:       # Strictly better than the best so far; a tie keeps the lower plan number
            best, best_value = entry, row["final_value"]                # New best
    return best                                                         # The best entry, or None if no plan is available

def serialise(entries):                                                 # Make the results safe to send as JSON
    """Turn every Decimal into text with two decimal places."""         # Docstring
    clean = []                                                          # The answer
    for entry in entries:                                               # Every plan
        rows = []                                                       # Cleaned rows for this plan
        for row in entry["results"]:                                    # Every result row
            rows.append({key: (str(value) if isinstance(value, Decimal) else value) for key, value in row.items()})  # Decimals become text, other values stay
        clean.append({**entry, "results": rows})                        # Copy the entry with the cleaned rows
    return clean                                                        # The finished list