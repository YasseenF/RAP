"""
Core month-by-month simulation engine for RAP / New IBR / Tiered Standard.

All simulate_* functions operate in NOMINAL dollars (see the framework note
at the top of params.py): the AGI trajectory, loan balance, and payments are
all nominal, so cash flows returned here should be discounted at a nominal
rate, and any tax computed on a forgiveness event occurring `y` years in the
future should use federal_tax_on_agi(..., years_from_2026=y) rather than the
raw 2026 brackets, which tax_bomb() below does automatically.
"""
import sys
sys.path.insert(0, ".")
from params import (
    rap_monthly_payment, ibr_monthly_payment, amortized_payment,
    tiered_standard_term_months, discretionary_income,
    RAP_PRINCIPAL_MATCH_FLOOR, RAP_FORGIVENESS_MONTHS, RAP_PSLF_MONTHS,
    IBR_NEW_FORGIVENESS_MONTHS, IBR_OLD_FORGIVENESS_MONTHS,
    TIERED_STANDARD_MIN_PAYMENT,
    federal_tax_on_agi,
)


def make_agi_schedule(initial_agi, income_growth):
    def schedule(year):
        return initial_agi * ((1 + income_growth) ** (year - 1))
    return schedule


def make_phased_schedule(phases):
    def schedule(year):
        y = year
        for n_years, start_agi, growth in phases:
            if y <= n_years:
                return start_agi * ((1 + growth) ** (y - 1))
            y -= n_years
        n_years, start_agi, growth = phases[-1]
        last_val = start_agi * ((1 + growth) ** (n_years - 1))
        extra_years = year - sum(p[0] for p in phases)
        return last_val * ((1 + growth) ** extra_years)
    return schedule


def simulate_rap(initial_balance, initial_agi=None, annual_rate=0.065, income_growth=0.0,
                  dependents=0, max_months=RAP_FORGIVENESS_MONTHS, pslf=False,
                  agi_schedule=None):
    forgiveness_months = RAP_PSLF_MONTHS if pslf else max_months
    if agi_schedule is None:
        agi_schedule = make_agi_schedule(initial_agi, income_growth)
    balance = float(initial_balance)
    total_paid = 0.0
    total_interest_charged = 0.0
    total_interest_waived = 0.0
    total_govt_principal_match = 0.0
    trajectory = []
    month = 0
    payoff_month = None

    for year in range(1, 100):
        agi = agi_schedule(year)
        monthly_payment = rap_monthly_payment(agi, dependents)
        for _ in range(12):
            month += 1
            interest_accrued = balance * annual_rate / 12.0

            if balance + interest_accrued <= monthly_payment:
                actual_payment = balance + interest_accrued
                total_paid += actual_payment
                total_interest_charged += interest_accrued
                balance = 0.0
                trajectory.append((month, year, agi, actual_payment, balance))
                payoff_month = month
                break

            interest_paid = min(monthly_payment, interest_accrued)
            interest_waived = max(0.0, interest_accrued - interest_paid)
            own_principal = max(0.0, monthly_payment - interest_accrued)
            # Matching principal payment (statutory): the borrower's principal
            # reduction is brought up to the LESSER of $50 or their total
            # monthly payment -- not an unconditional $50. A borrower paying
            # the $10 floor gets their principal reduced by $10, not $50.
            target_principal_reduction = min(RAP_PRINCIPAL_MATCH_FLOOR, monthly_payment)
            govt_match = max(0.0, target_principal_reduction - own_principal)
            principal_reduction = own_principal + govt_match
            principal_reduction = min(principal_reduction, balance)

            balance -= principal_reduction
            total_paid += monthly_payment
            total_interest_charged += interest_paid
            total_interest_waived += interest_waived
            total_govt_principal_match += govt_match
            trajectory.append((month, year, agi, monthly_payment, balance))

            if month >= forgiveness_months:
                break
        if payoff_month is not None or month >= forgiveness_months or balance <= 0.005:
            break

    forgiven_balance = balance if (month >= forgiveness_months and balance > 0.005) else 0.0
    is_pslf_forgiveness = pslf and forgiven_balance > 0

    result = dict(
        plan="RAP" + (" (PSLF)" if pslf else ""),
        months_to_resolution=month,
        years_to_resolution=month / 12.0,
        payoff_before_forgiveness=payoff_month is not None,
        forgiven_balance=forgiven_balance,
        total_borrower_paid=total_paid,
        total_interest_charged=total_interest_charged,
        total_interest_waived=total_interest_waived,
        total_govt_principal_match=total_govt_principal_match,
        final_agi=agi,
        is_pslf_forgiveness=is_pslf_forgiveness,
    )
    return result, trajectory


def simulate_ibr(initial_balance, initial_agi=None, annual_rate=0.065, income_growth=0.0,
                  family_size=1, new_ibr=True, standard_cap=1e9, agi_schedule=None):
    forgiveness_months = IBR_NEW_FORGIVENESS_MONTHS if new_ibr else IBR_OLD_FORGIVENESS_MONTHS
    if agi_schedule is None:
        agi_schedule = make_agi_schedule(initial_agi, income_growth)
    balance = float(initial_balance)
    total_paid = 0.0
    total_interest_charged = 0.0
    total_capitalized = 0.0
    trajectory = []
    month = 0
    payoff_month = None

    for year in range(1, 100):
        agi = agi_schedule(year)
        monthly_payment = ibr_monthly_payment(agi, family_size, new_ibr, standard_cap)
        for _ in range(12):
            month += 1
            interest_accrued = balance * annual_rate / 12.0

            if balance + interest_accrued <= monthly_payment:
                actual_payment = balance + interest_accrued
                total_paid += actual_payment
                total_interest_charged += interest_accrued
                balance = 0.0
                trajectory.append((month, year, agi, actual_payment, balance))
                payoff_month = month
                break

            if monthly_payment >= interest_accrued:
                principal_reduction = monthly_payment - interest_accrued
                balance -= principal_reduction
                total_interest_charged += interest_accrued
            else:
                shortfall = interest_accrued - monthly_payment
                balance += shortfall
                total_interest_charged += monthly_payment
                total_capitalized += shortfall

            total_paid += monthly_payment
            trajectory.append((month, year, agi, monthly_payment, balance))

            if month >= forgiveness_months:
                break
        if payoff_month is not None or month >= forgiveness_months or balance <= 0.005:
            break

    forgiven_balance = balance if (month >= forgiveness_months and balance > 0.005) else 0.0

    result = dict(
        plan="New IBR" if new_ibr else "Old IBR",
        months_to_resolution=month,
        years_to_resolution=month / 12.0,
        payoff_before_forgiveness=payoff_month is not None,
        forgiven_balance=forgiven_balance,
        total_borrower_paid=total_paid,
        total_interest_charged=total_interest_charged,
        total_capitalized=total_capitalized,
        final_agi=agi,
    )
    return result, trajectory


def simulate_tiered_standard(initial_balance, annual_rate, min_payment=TIERED_STANDARD_MIN_PAYMENT):
    term = tiered_standard_term_months(initial_balance)
    payment = max(amortized_payment(initial_balance, annual_rate, term), min_payment)
    balance = float(initial_balance)
    total_paid = 0.0
    total_interest = 0.0
    trajectory = []
    month = 0
    # Safety cap, consistent with the 100-year cap used in simulate_rap/simulate_ibr;
    # never actually reached since payment >= the amortized payment for `term`.
    while balance > 0.005 and month < 1200:
        month += 1
        interest_accrued = balance * annual_rate / 12.0
        if balance + interest_accrued <= payment:
            actual_payment = balance + interest_accrued
            total_paid += actual_payment
            total_interest += interest_accrued
            balance = 0.0
            trajectory.append((month, (month - 1) // 12 + 1, None, actual_payment, balance))
            break
        principal_reduction = payment - interest_accrued
        balance -= principal_reduction
        total_paid += payment
        total_interest += interest_accrued
        trajectory.append((month, (month - 1) // 12 + 1, None, payment, balance))
    result = dict(
        plan="Tiered Standard",
        months_to_resolution=month,
        years_to_resolution=month / 12.0,
        payoff_before_forgiveness=True,
        forgiven_balance=0.0,
        total_borrower_paid=total_paid,
        total_interest_charged=total_interest,
        monthly_payment=payment,
        final_agi=None,
    )
    return result, trajectory


def npv(cashflows_by_year, annual_discount_rate=0.05):
    total = 0.0
    for yr, amt in cashflows_by_year.items():
        total += amt / ((1 + annual_discount_rate) ** yr)
    return total


def compute_npv_from_traj(traj, tax_bomb_amt, forgiveness_month, discount_rate=0.05):
    """Shared helper: sum a trajectory's payments (plus a one-time tax-bomb
    cash flow at the forgiveness month, if any) into annual cash flows and
    discount them. Single source of truth -- previously reimplemented
    identically in three separate analysis scripts."""
    cashflows = {}
    for month, year, agi, pay, bal in traj:
        yr = month / 12.0
        cashflows[yr] = cashflows.get(yr, 0.0) + pay
    if tax_bomb_amt and forgiveness_month:
        yr = forgiveness_month / 12.0
        cashflows[yr] = cashflows.get(yr, 0.0) + tax_bomb_amt
    return npv(cashflows, discount_rate)


def tax_bomb(forgiven_balance, agi_in_forgiveness_year, years_from_2026: float = 0.0, is_pslf=False):
    """Tax liability created by taxable forgiveness. `years_from_2026` --
    typically a trajectory's months_to_resolution / 12 -- projects the tax
    brackets and standard deduction forward to the calendar year the
    forgiveness actually occurs in (see federal_tax_on_agi), rather than
    taxing a forgiveness event 20-30 years out at frozen 2026 brackets."""
    if is_pslf or forgiven_balance <= 0:
        return 0.0
    tax_with = federal_tax_on_agi(agi_in_forgiveness_year + forgiven_balance, years_from_2026)
    tax_without = federal_tax_on_agi(agi_in_forgiveness_year, years_from_2026)
    return tax_with - tax_without
