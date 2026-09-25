import sys, os, json
sys.path.insert(0, ".")
os.makedirs("../data", exist_ok=True)
os.makedirs("../figs", exist_ok=True)

import numpy as np
import pandas as pd
from params import (
    RAP_BRACKETS, rap_monthly_payment, RATE_UNDERGRAD, RATE_GRAD_UNSUB,
    amortized_payment, marginal_income_tax_rate, fica_marginal_rate,
    INFLATION_RATE,
)
from simulate import (
    simulate_rap, simulate_ibr, simulate_tiered_standard,
    make_phased_schedule, npv, tax_bomb, compute_npv_from_traj,
)

pd.set_option("display.float_format", lambda x: f"{x:,.4f}")

# ===========================================================================
# 1. NOTCH TABLE
# ===========================================================================
rows = []
thresholds = [b[0] for b in RAP_BRACKETS]
for t in thresholds:
    below = rap_monthly_payment(t, 0) * 12
    above = rap_monthly_payment(t + 1, 0) * 12
    jump = above - below
    rows.append({"threshold": t, "annual_at_threshold": below,
                 "annual_at_threshold_plus_1": above, "dollar_jump": jump,
                 "implicit_marginal_pct": jump * 100})
notch_df = pd.DataFrame(rows)
notch_df.to_csv("../data/notch_table.csv", index=False)
real_notches = notch_df[notch_df["dollar_jump"] > 1].copy()
print("=== NOTCH TABLE ===")
print(real_notches.to_string(index=False))

# ===========================================================================
# 2. DOMINATED-REGION (BUNCHING) ANALYSIS
# ===========================================================================
dom_rows = []
for lo, hi, rate in RAP_BRACKETS:
    T = lo
    prev = [r for (l2, h2, r) in RAP_BRACKETS if h2 == T]
    if not prev or T == 10000:
        continue
    r1, r2 = prev[0], rate
    T_star = T * (1 - r1) / (1 - r2)
    width = T_star - T
    width_pct = width / T * 100
    dom_rows.append(dict(threshold=T, r1=r1, r2=r2, T_star=T_star,
                          dominated_width_dollars=width, width_pct_of_income=width_pct))
dom_df = pd.DataFrame(dom_rows)
dom_df.to_csv("../data/dominated_regions.csv", index=False)
print("\n=== DOMINATED-REGION (BUNCHING) ANALYSIS ===")
print(dom_df.to_string(index=False))
print(f"Mean width: {dom_df['width_pct_of_income'].mean():.4f}% of income "
      f"(range {dom_df['width_pct_of_income'].min():.4f}%-{dom_df['width_pct_of_income'].max():.4f}%)")

# ===========================================================================
# 3. ARCHETYPE SIMULATIONS
# ===========================================================================
results, trajectories, archetype_params = {}, {}, {}

A_balance, A_agi0, A_rate, A_growth = 30000, 42000, RATE_UNDERGRAD, 0.030
res, traj = simulate_rap(A_balance, A_agi0, A_rate, A_growth, dependents=0)
res["tax_bomb"] = tax_bomb(res["forgiven_balance"], res["final_agi"], res["months_to_resolution"] / 12.0)
results["A_RAP"] = res; trajectories["A_RAP"] = traj
archetype_params["A_RAP"] = dict(starting_debt=A_balance, starting_agi=A_agi0, rate=A_rate, income_growth=A_growth)
res2, traj2 = simulate_tiered_standard(A_balance, A_rate)
res2["tax_bomb"] = 0.0
results["A_TieredStandard"] = res2; trajectories["A_TieredStandard"] = traj2
archetype_params["A_TieredStandard"] = dict(starting_debt=A_balance, starting_agi=None, rate=A_rate, income_growth=None)

B_balance, B_agi0, B_rate, B_growth = 95000, 48000, RATE_GRAD_UNSUB, 0.025
B_cap = amortized_payment(B_balance, B_rate, 120)
res, traj = simulate_rap(B_balance, B_agi0, B_rate, B_growth, dependents=0)
res["tax_bomb"] = tax_bomb(res["forgiven_balance"], res["final_agi"], res["months_to_resolution"] / 12.0)
results["B_RAP"] = res; trajectories["B_RAP"] = traj
archetype_params["B_RAP"] = dict(starting_debt=B_balance, starting_agi=B_agi0, rate=B_rate, income_growth=B_growth)
res2, traj2 = simulate_ibr(B_balance, B_agi0, B_rate, B_growth, family_size=1, new_ibr=True, standard_cap=B_cap)
res2["tax_bomb"] = tax_bomb(res2["forgiven_balance"], res2["final_agi"], res2["months_to_resolution"] / 12.0)
results["B_NewIBR"] = res2; trajectories["B_NewIBR"] = traj2
archetype_params["B_NewIBR"] = dict(starting_debt=B_balance, starting_agi=B_agi0, rate=B_rate, income_growth=B_growth)

C_balance, C_agi0, C_rate, C_growth = 32000, 88000, RATE_UNDERGRAD, 0.045
res, traj = simulate_rap(C_balance, C_agi0, C_rate, C_growth, dependents=0)
res["tax_bomb"] = tax_bomb(res["forgiven_balance"], res["final_agi"], res["months_to_resolution"] / 12.0)
results["C_RAP"] = res; trajectories["C_RAP"] = traj
archetype_params["C_RAP"] = dict(starting_debt=C_balance, starting_agi=C_agi0, rate=C_rate, income_growth=C_growth)
res2, traj2 = simulate_tiered_standard(C_balance, C_rate)
res2["tax_bomb"] = 0.0
results["C_TieredStandard"] = res2; trajectories["C_TieredStandard"] = traj2
archetype_params["C_TieredStandard"] = dict(starting_debt=C_balance, starting_agi=None, rate=C_rate, income_growth=None)

D_balance, D_rate = 200000, RATE_GRAD_UNSUB
D_schedule = make_phased_schedule([(3, 65000, 0.02), (27, 285000, 0.03)])
res, traj = simulate_rap(D_balance, annual_rate=D_rate, dependents=0, agi_schedule=D_schedule)
res["tax_bomb"] = tax_bomb(res["forgiven_balance"], res["final_agi"], res["months_to_resolution"] / 12.0)
results["D_RAP"] = res; trajectories["D_RAP"] = traj
archetype_params["D_RAP"] = dict(starting_debt=D_balance, starting_agi=65000, rate=D_rate, income_growth="phased (2%/3%)")
res2, traj2 = simulate_tiered_standard(D_balance, D_rate)
res2["tax_bomb"] = 0.0
results["D_TieredStandard"] = res2; trajectories["D_TieredStandard"] = traj2
archetype_params["D_TieredStandard"] = dict(starting_debt=D_balance, starting_agi=None, rate=D_rate, income_growth=None)

for key, res in results.items():
    traj = trajectories[key]
    fmonth = res["months_to_resolution"] if res.get("forgiven_balance", 0) > 0 else None
    res["npv_5pct"] = compute_npv_from_traj(traj, res.get("tax_bomb", 0.0), fmonth, 0.05)

labels = {
    "A_RAP": ("A. New Teacher ($30k debt, 6.52%)", "RAP"),
    "A_TieredStandard": ("A. New Teacher ($30k debt, 6.52%)", "Tiered Standard"),
    "B_RAP": ("B. Caseworker ($95k debt, 8.07%)", "RAP"),
    "B_NewIBR": ("B. Caseworker ($95k debt, 8.07%)", "New IBR"),
    "C_RAP": ("C. Early-Career Engineer ($32k debt, 6.52%)", "RAP"),
    "C_TieredStandard": ("C. Early-Career Engineer ($32k debt, 6.52%)", "Tiered Standard"),
    "D_RAP": ("D. New Physician ($200k debt, 8.07%)", "RAP"),
    "D_TieredStandard": ("D. New Physician ($200k debt, 8.07%)", "Tiered Standard"),
}
summary_rows = []
for key, res in results.items():
    arche, plan = labels[key]
    p = archetype_params[key]
    summary_rows.append({
        "Archetype": arche, "Plan": plan,
        "Starting_debt": p["starting_debt"],
        "Starting_AGI": p["starting_agi"],
        "Interest_rate": p["rate"],
        "Income_growth": p["income_growth"],
        "Years": round(res["years_to_resolution"], 1),
        "Ends_in": "Forgiveness" if res.get("forgiven_balance", 0) > 0 else "Full payoff",
        "Forgiven_balance": round(res.get("forgiven_balance", 0), 0),
        "Tax_bomb": round(res.get("tax_bomb", 0), 0),
        "Total_paid_nominal": round(res["total_borrower_paid"], 0),
        "NPV_5pct": round(res["npv_5pct"], 0),
    })
summary_df = pd.DataFrame(summary_rows)
summary_df.to_csv("../data/archetype_summary.csv", index=False)
print("\n=== ARCHETYPE SUMMARY ===")
print(summary_df.to_string(index=False))

with open("../data/trajectories.json", "w") as f:
    json.dump(trajectories, f)
with open("../data/results_raw.json", "w") as f:
    json.dump(results, f, indent=2)

# ===========================================================================
# 4. BRACKET CREEP
# ===========================================================================
real_income = 48000
creep_rows = []
for t in range(0, 26):
    nominal_agi = real_income * ((1 + INFLATION_RATE) ** t)
    rap_annual_nominal = rap_monthly_payment(nominal_agi, 0) * 12
    rap_annual_real = rap_annual_nominal / ((1 + INFLATION_RATE) ** t)
    rap_burden_pct = rap_annual_real / real_income * 100
    di_indexed = max(0.0, nominal_agi - 1.5 * (23940 * (1 + INFLATION_RATE) ** t))
    ibr_annual_nominal = di_indexed * 0.10
    ibr_annual_real = ibr_annual_nominal / ((1 + INFLATION_RATE) ** t)
    ibr_burden_pct = ibr_annual_real / real_income * 100
    creep_rows.append(dict(year=t, nominal_agi=nominal_agi, rap_burden_pct=rap_burden_pct,
                            ibr_burden_pct=ibr_burden_pct))
creep_df = pd.DataFrame(creep_rows)
creep_df.to_csv("../data/bracket_creep.csv", index=False)
print("\n=== BRACKET CREEP (year 0, 10, 20, 25) ===")
print(creep_df.iloc[[0, 10, 20, 25]][["year", "nominal_agi", "rap_burden_pct", "ibr_burden_pct"]].to_string(index=False))

# ===========================================================================
# 5. COMBINED MARGINAL RATE SCHEDULE
# ===========================================================================
agis = np.arange(1000, 160000, 500)
cmr_rows = []
for agi in agis:
    it = marginal_income_tax_rate(agi)
    fica = fica_marginal_rate(agi)
    cmr_rows.append(dict(agi=agi, income_tax_marginal=it, fica_marginal=fica, combined_marginal=it + fica))
cmr_df = pd.DataFrame(cmr_rows)
cmr_df.to_csv("../data/combined_marginal_rates.csv", index=False)

# ===========================================================================
# 6. BREAK-EVEN GROWTH RATE: RAP vs Tiered Standard (Archetype A params)
# ===========================================================================
growth_rates = np.arange(0.0, 0.121, 0.0025)
npv_rap_list = []
for g in growth_rates:
    res, traj = simulate_rap(A_balance, A_agi0, A_rate, g, dependents=0)
    tb = tax_bomb(res["forgiven_balance"], res["final_agi"], res["months_to_resolution"] / 12.0)
    fmonth = res["months_to_resolution"] if res["forgiven_balance"] > 0 else None
    npv_rap_list.append(compute_npv_from_traj(traj, tb, fmonth, 0.05))
res_std, traj_std = simulate_tiered_standard(A_balance, A_rate)
npv_std = compute_npv_from_traj(traj_std, 0, None, 0.05)
breakeven_df = pd.DataFrame({"growth_rate": growth_rates, "npv_rap": npv_rap_list,
                              "npv_tiered_standard": [npv_std] * len(growth_rates)})
breakeven_df["rap_cheaper"] = breakeven_df["npv_rap"] < breakeven_df["npv_tiered_standard"]
breakeven_df.to_csv("../data/breakeven_growth.csv", index=False)
crossings = breakeven_df[breakeven_df["rap_cheaper"] != breakeven_df["rap_cheaper"].shift(1)]
print("\n=== BREAK-EVEN GROWTH RATE (Archetype A: RAP vs Tiered Standard) ===")
print(f"NPV Tiered Standard (constant): ${npv_std:,.0f}")
print(breakeven_df.iloc[::4].to_string(index=False))
print(f"\nCrossover point(s):\n{crossings}")

# ===========================================================================
# 7. DISCOUNT-RATE SENSITIVITY (Archetype B, RAP vs New IBR)
# ===========================================================================
print("\n=== DISCOUNT-RATE SENSITIVITY (Archetype B) ===")
sens_rows = []
for dr in [0.03, 0.04, 0.05, 0.06, 0.07]:
    res_rap, traj_rap = simulate_rap(B_balance, B_agi0, B_rate, B_growth, dependents=0)
    tb_rap = tax_bomb(res_rap["forgiven_balance"], res_rap["final_agi"], res_rap["months_to_resolution"] / 12.0)
    fmonth_rap = res_rap["months_to_resolution"] if res_rap["forgiven_balance"] > 0 else None
    npv_rap = compute_npv_from_traj(traj_rap, tb_rap, fmonth_rap, dr)

    res_ibr, traj_ibr = simulate_ibr(B_balance, B_agi0, B_rate, B_growth, family_size=1, new_ibr=True, standard_cap=B_cap)
    tb_ibr = tax_bomb(res_ibr["forgiven_balance"], res_ibr["final_agi"], res_ibr["months_to_resolution"] / 12.0)
    fmonth_ibr = res_ibr["months_to_resolution"] if res_ibr["forgiven_balance"] > 0 else None
    npv_ibr = compute_npv_from_traj(traj_ibr, tb_ibr, fmonth_ibr, dr)

    sens_rows.append(dict(discount_rate=dr, npv_rap=npv_rap, npv_ibr=npv_ibr,
                           rap_cheaper=npv_rap < npv_ibr, gap=npv_ibr - npv_rap))
    print(f"  {dr*100:.0f}%: NPV(RAP)=${npv_rap:,.0f}  NPV(IBR)=${npv_ibr:,.0f}  "
          f"RAP cheaper: {npv_rap < npv_ibr}  gap=${npv_ibr-npv_rap:,.0f}")
sens_df = pd.DataFrame(sens_rows)
sens_df.to_csv("../data/discount_sensitivity.csv", index=False)

print("\n\n=== ALL ANALYSIS COMPLETE ===")
