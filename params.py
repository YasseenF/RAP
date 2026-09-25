"""
Verified parameters for RAP / Tiered Standard / Legacy IBR modeling.
Every numeric input here is sourced from primary or authoritative secondary
sources gathered during research (ED.gov, CRS, IRS, ASPE/HHS, FSA Partners).
See paper References for citations.

MODELING FRAMEWORK -- NOMINAL DOLLARS THROUGHOUT.
Every dollar figure this module and simulate.py produce (loan balances,
payments, AGI trajectories, RAP/IBR statutory thresholds) is in NOMINAL
(current-year) dollars: `income_growth` in simulate.make_agi_schedule is a
nominal AGI growth rate, loan interest rates below are the stated nominal
rates on the underlying loans, and RAP's payment brackets are fixed nominal
dollar thresholds (they are NOT inflation-indexed under the statute -- see
the bracket-creep analysis in run_all_analysis.py, which is the one place
a *real* burden is deliberately computed, by explicitly deflating nominal
RAP payments). Because the whole trajectory is nominal, the NPV discount
rate used elsewhere (simulate.npv) should be read as a NOMINAL discount
rate, and federal income tax brackets -- which by statute (IRC Sec. 1(f))
ARE inflation-indexed every year -- must be projected forward to whatever
calendar year a tax event (e.g., taxable forgiveness) actually falls in,
rather than held at their 2026 levels. See inflate_brackets() and
federal_tax_on_agi() below, and tax_bomb() in simulate.py, which is the
function that carries a `years_from_2026` argument end to end.
INFLATION_RATE is the single long-run CPI assumption used for both that
forward bracket indexing and the bracket-creep analysis, so the two stay
mutually consistent.
"""

INFLATION_RATE = 0.027  # long-run CPI assumption (see paper Sec. on inflation assumptions)

FPL_2026 = {1: 15960, 2: 21640, 3: 27320, 4: 33000, 5: 38680, 6: 44360}
FPL_INCREMENT = 5680

def fpl(size: int) -> float:
    if size in FPL_2026:
        return FPL_2026[size]
    if size < 1:
        size = 1
    return FPL_2026[6] + (size - 6) * FPL_INCREMENT


TAX_BRACKETS_SINGLE_2026 = [
    (0, 12400, 0.10),
    (12400, 50400, 0.12),
    (50400, 105700, 0.22),
    (105700, 201775, 0.24),
    (201775, 256225, 0.32),
    (256225, 640600, 0.35),
    (640600, float("inf"), 0.37),
]
STD_DEDUCTION_SINGLE_2026 = 16100


def federal_tax_on_taxable_income(taxable_income: float, brackets=None) -> float:
    if brackets is None:
        brackets = TAX_BRACKETS_SINGLE_2026
    if taxable_income <= 0:
        return 0.0
    tax = 0.0
    for lo, hi, rate in brackets:
        if taxable_income > lo:
            tax += (min(taxable_income, hi) - lo) * rate
        else:
            break
    return tax


def inflate_brackets(years_from_2026: float, brackets=None, rate: float = INFLATION_RATE):
    """Project the 2026 tax brackets forward by `years_from_2026` years at the
    assumed long-run inflation rate. Federal income-tax brackets are
    inflation-indexed annually under current law (IRC Sec. 1(f)); this
    reproduces that indexing so a nominal AGI realized decades from now is
    taxed against brackets of comparable *real* width, rather than against
    stale 2026-dollar brackets. years_from_2026=0 recovers the 2026 brackets
    exactly."""
    if brackets is None:
        brackets = TAX_BRACKETS_SINGLE_2026
    factor = (1 + rate) ** years_from_2026
    return [(lo * factor, hi * factor if hi != float("inf") else float("inf"), r)
            for lo, hi, r in brackets]


def federal_tax_on_agi(agi: float, years_from_2026: float = 0.0,
                        std_deduction: float = STD_DEDUCTION_SINGLE_2026,
                        inflation_rate: float = INFLATION_RATE) -> float:
    """Federal tax on a given AGI. `years_from_2026` projects both the
    standard deduction and the tax brackets forward at `inflation_rate`
    before applying them, so a tax event N years in the future is evaluated
    against brackets of N years' worth of (assumed) statutory inflation
    indexing rather than frozen 2026 brackets. Pass years_from_2026=0 (the
    default) to use the 2026 brackets/deduction exactly, e.g. for a
    same-year calculation."""
    factor = (1 + inflation_rate) ** years_from_2026
    taxable = max(0.0, agi - std_deduction * factor)
    brackets = inflate_brackets(years_from_2026, rate=inflation_rate)
    return federal_tax_on_taxable_income(taxable, brackets)


def marginal_income_tax_rate(agi: float, std_deduction: float = STD_DEDUCTION_SINGLE_2026) -> float:
    taxable = max(0.0, agi - std_deduction)
    for lo, hi, rate in TAX_BRACKETS_SINGLE_2026:
        if lo <= taxable < hi:
            return rate
    return TAX_BRACKETS_SINGLE_2026[-1][2]


SS_WAGE_BASE_2026 = 184500
SS_RATE = 0.062
MEDICARE_RATE = 0.0145
ADDL_MEDICARE_RATE = 0.009
ADDL_MEDICARE_THRESHOLD_SINGLE = 200000


def fica_marginal_rate(agi: float) -> float:
    rate = MEDICARE_RATE
    if agi < SS_WAGE_BASE_2026:
        rate += SS_RATE
    if agi > ADDL_MEDICARE_THRESHOLD_SINGLE:
        rate += ADDL_MEDICARE_RATE
    return rate


RATE_UNDERGRAD = 0.0652
RATE_GRAD_UNSUB = 0.0807
RATE_PLUS = 0.0907

RAP_BRACKETS = [
    (10000, 20000, 0.01),
    (20000, 30000, 0.02),
    (30000, 40000, 0.03),
    (40000, 50000, 0.04),
    (50000, 60000, 0.05),
    (60000, 70000, 0.06),
    (70000, 80000, 0.07),
    (80000, 90000, 0.08),
    (90000, 100000, 0.09),
    (100000, float("inf"), 0.10),
]
RAP_FLOOR_MONTHLY = 10.0
RAP_DEPENDENT_CREDIT = 50.0
RAP_PRINCIPAL_MATCH_FLOOR = 50.0
RAP_FORGIVENESS_MONTHS = 360
RAP_PSLF_MONTHS = 120


def rap_rate(agi: float):
    if agi <= 10000:
        return None
    for lo, hi, rate in RAP_BRACKETS:
        if lo < agi <= hi:
            return rate
    return RAP_BRACKETS[-1][2]


def rap_monthly_payment(agi: float, dependents: int = 0) -> float:
    if agi <= 10000:
        base = RAP_FLOOR_MONTHLY
    else:
        rate = rap_rate(agi)
        base = (agi * rate) / 12.0
    payment = base - RAP_DEPENDENT_CREDIT * dependents
    return max(payment, RAP_FLOOR_MONTHLY)


def discretionary_income(agi: float, family_size: int) -> float:
    return max(0.0, agi - 1.5 * fpl(family_size))


def ibr_monthly_payment(agi: float, family_size: int, new_ibr: bool, standard_cap: float) -> float:
    di = discretionary_income(agi, family_size)
    rate = 0.10 if new_ibr else 0.15
    payment = (di * rate) / 12.0
    return min(payment, standard_cap)


IBR_NEW_FORGIVENESS_MONTHS = 240
IBR_OLD_FORGIVENESS_MONTHS = 300


TIERED_STANDARD_MIN_PAYMENT = 50.0  # statutory minimum monthly payment on Tiered Standard


def tiered_standard_term_months(balance: float) -> int:
    if balance < 25000:
        return 120
    elif balance < 50000:
        return 180
    elif balance < 100000:
        return 240
    else:
        return 300


def amortized_payment(principal: float, annual_rate: float, n_months: int) -> float:
    r = annual_rate / 12.0
    if r == 0:
        return principal / n_months
    return principal * r / (1 - (1 + r) ** (-n_months))
