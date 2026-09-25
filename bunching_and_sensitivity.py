import sys
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from params import RAP_BRACKETS, rap_monthly_payment
from simulate import simulate_rap, simulate_tiered_standard, npv, tax_bomb, compute_npv_from_traj

# ===========================================================================
# PART A: Dominated-region (bunching) analysis
#
# Standard notch theory (Kleven & Waseem 2013): at a notch where the rate
# jumps from r1 to r2 > r1 at threshold T, after-payment income is
#   y(z) = z*(1 - r1)   for z <= T
#   y(z) = z*(1 - r2)   for z >  T
# Any z in (T, T*) yields STRICTLY LESS after-payment income than earning
# exactly T, where T* solves T*(1-r2) = T(1-r1)  =>  T* = T*(1-r1)/(1-r2).
# (T, T*) is the "dominated region": no expected-net-income-maximizing
# borrower would ever choose to locate there. (Not "utility-maximizing":
# this model has no labor disutility, leisure preference, or nonlinear
# utility -- it maximizes income net of RAP payments, nothing else.)
# ===========================================================================
rows = []
for lo, hi, rate in RAP_BRACKETS:
    T = lo
    if T == 10000:
        continue  # absorbed by the $10 floor -- no genuine notch here (see Fig 1/2)
    # rate just below T
    prev_rate = [r for (l2, h2, r) in RAP_BRACKETS if h2 == T]
    if not prev_rate:
        continue
    r1 = prev_rate[0]
    r2 = rate
    T_star = T * (1 - r1) / (1 - r2)
    dominated_width = T_star - T
    width_pct_of_income = dominated_width / T * 100
    # closed form check: width_pct = (r2-r1)/(1-r2) * 100
    closed_form_pct = (r2 - r1) / (1 - r2) * 100
    rows.append(dict(threshold=T, r1=r1, r2=r2, T_star=T_star,
                      dominated_width_dollars=dominated_width,
                      width_pct_of_income=width_pct_of_income,
                      closed_form_check_pct=closed_form_pct))

dom_df = pd.DataFrame(rows)
dom_df.to_csv("../data/dominated_regions.csv", index=False)
print("=== Dominated-region (bunching) analysis ===")
print(dom_df.to_string(index=False))
print(f"\nClosed-form width formula matches direct computation: "
      f"{np.allclose(dom_df['width_pct_of_income'], dom_df['closed_form_check_pct'])}")
print(f"Mean dominated-region width: {dom_df['width_pct_of_income'].mean():.3f}% of income")
print(f"Range: {dom_df['width_pct_of_income'].min():.3f}% to {dom_df['width_pct_of_income'].max():.3f}%")

# ===========================================================================
# PART B: Break-even income-growth rate, RAP vs Tiered Standard
# For a fixed starting balance/AGI (Archetype A's parameters), find the
# annual income growth rate g* at which NPV(RAP) = NPV(Tiered Standard).
#
# NOTE ON RANGE: this sweeps growth 0-12%, wider than the 0-6% range used in
# the generalized debt x growth grids (generalized_maps.py) and Figure 8/9.
# This is intentional -- it is the single-archetype sensitivity check behind
# Figure 7, run further out to confirm RAP stays cheaper across the fuller
# range, not a second attempt at the same 0-6% grid. State this explicitly
# in the methods section so the two ranges don't read as inconsistent.
# ===========================================================================
from params import RATE_UNDERGRAD

A_balance, A_agi0 = 30000, 42000
growth_rates = np.arange(0.0, 0.121, 0.0025)
npv_rap_list, npv_std_list = [], []
for g in growth_rates:
    res, traj = simulate_rap(A_balance, A_agi0, RATE_UNDERGRAD, g, dependents=0)
    tb = tax_bomb(res["forgiven_balance"], res["final_agi"], res["months_to_resolution"] / 12.0)
    fmonth = res["months_to_resolution"] if res["forgiven_balance"] > 0 else None
    npv_rap = compute_npv_from_traj(traj, tb, fmonth, 0.05)
    npv_rap_list.append(npv_rap)

res_std, traj_std = simulate_tiered_standard(A_balance, RATE_UNDERGRAD)
npv_std = compute_npv_from_traj(traj_std, 0, None, 0.05)  # constant, doesn't depend on g

breakeven_df = pd.DataFrame({
    "growth_rate": growth_rates,
    "npv_rap": npv_rap_list,
    "npv_tiered_standard": [npv_std] * len(growth_rates),
})
breakeven_df["rap_cheaper"] = breakeven_df["npv_rap"] < breakeven_df["npv_tiered_standard"]
breakeven_df.to_csv("../data/breakeven_growth.csv", index=False)
print("\n=== Break-even income growth rate: RAP vs Tiered Standard (Archetype A parameters) ===")
print(breakeven_df.to_string(index=False))

# find the crossover
crossings = breakeven_df[breakeven_df["rap_cheaper"] != breakeven_df["rap_cheaper"].shift(1)]
print(f"\nCrossover row(s):\n{crossings}")

# ===========================================================================
# PART C: Discount-rate sensitivity check for Archetype B (RAP vs New IBR)
# ===========================================================================
from params import RATE_GRAD_UNSUB, amortized_payment
from simulate import simulate_ibr

B_balance, B_agi0, B_rate, B_growth = 95000, 48000, RATE_GRAD_UNSUB, 0.025
B_standard_cap = amortized_payment(B_balance, B_rate, 120)

print("\n=== Discount-rate sensitivity, Archetype B ===")
for dr in [0.03, 0.04, 0.05, 0.06, 0.07]:
    res_rap, traj_rap = simulate_rap(B_balance, B_agi0, B_rate, B_growth, dependents=0)
    tb_rap = tax_bomb(res_rap["forgiven_balance"], res_rap["final_agi"], res_rap["months_to_resolution"] / 12.0)
    fmonth_rap = res_rap["months_to_resolution"] if res_rap["forgiven_balance"] > 0 else None
    npv_rap = compute_npv_from_traj(traj_rap, tb_rap, fmonth_rap, dr)

    res_ibr, traj_ibr = simulate_ibr(B_balance, B_agi0, B_rate, B_growth, family_size=1,
                                       new_ibr=True, standard_cap=B_standard_cap)
    tb_ibr = tax_bomb(res_ibr["forgiven_balance"], res_ibr["final_agi"], res_ibr["months_to_resolution"] / 12.0)
    fmonth_ibr = res_ibr["months_to_resolution"] if res_ibr["forgiven_balance"] > 0 else None
    npv_ibr = compute_npv_from_traj(traj_ibr, tb_ibr, fmonth_ibr, dr)

    print(f"  discount rate {dr*100:.0f}%: NPV(RAP) = ${npv_rap:,.0f}   "
          f"NPV(New IBR) = ${npv_ibr:,.0f}   RAP cheaper: {npv_rap < npv_ibr}   "
          f"gap = ${npv_ibr-npv_rap:,.0f}")
