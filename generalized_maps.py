import sys, json
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from params import RATE_UNDERGRAD, RATE_GRAD_UNSUB, amortized_payment, fpl, RAP_DEPENDENT_CREDIT
from simulate import (
    simulate_rap, simulate_ibr, simulate_tiered_standard, npv, tax_bomb,
    compute_npv_from_traj,
)

# ===========================================================================
# GENERALIZED MAP 1: RAP vs legacy New-IBR, existing borrowers.
# Holds starting AGI at $45,000 (ED's own worked-example income, for
# continuity with Table 1/Sec. III-A) and varies starting debt and income
# growth rate -- the two dimensions Sec. III-D identifies as decisive.
# ===========================================================================
starting_agi = 45000
debts = np.arange(20000, 155000, 5000)
growths = np.arange(0.0, 0.061, 0.0025)

grid_rap = np.zeros((len(growths), len(debts)))
grid_ibr = np.zeros((len(growths), len(debts)))

for i, g in enumerate(growths):
    for j, d in enumerate(debts):
        cap = amortized_payment(d, RATE_GRAD_UNSUB, 120)
        res_r, traj_r = simulate_rap(d, starting_agi, RATE_GRAD_UNSUB, g, dependents=0)
        tb_r = tax_bomb(res_r["forgiven_balance"], res_r["final_agi"], res_r["months_to_resolution"] / 12.0)
        fm_r = res_r["months_to_resolution"] if res_r["forgiven_balance"] > 0 else None
        grid_rap[i, j] = compute_npv_from_traj(traj_r, tb_r, fm_r, 0.05)

        res_i, traj_i = simulate_ibr(d, starting_agi, RATE_GRAD_UNSUB, g, family_size=1,
                                       new_ibr=True, standard_cap=cap)
        tb_i = tax_bomb(res_i["forgiven_balance"], res_i["final_agi"], res_i["months_to_resolution"] / 12.0)
        fm_i = res_i["months_to_resolution"] if res_i["forgiven_balance"] > 0 else None
        grid_ibr[i, j] = compute_npv_from_traj(traj_i, tb_i, fm_i, 0.05)

diff = grid_ibr - grid_rap  # positive => RAP has the lower modeled NPV
np.save("../data/grid_debts.npy", debts)
np.save("../data/grid_growths.npy", growths)
np.save("../data/grid_rap_npv.npy", grid_rap)
np.save("../data/grid_ibr_npv.npy", grid_ibr)

pct_rap_cheaper = (diff > 0).mean() * 100
print(f"=== GENERALIZED MAP: RAP vs New IBR, starting AGI=${starting_agi:,} ===")
print(f"Grid: {len(debts)} debt levels (${debts[0]:,}-${debts[-1]:,}) x {len(growths)} growth rates (0-6%)")
print(f"RAP has lower NPV in {pct_rap_cheaper:.1f}% of the {diff.size} grid cells")
# find rough crossover: for each growth rate, largest debt where RAP still has the lower NPV
print("\nFor each growth rate, does RAP have the lower NPV at every tested debt level up to $150k?")
for i, g in enumerate(growths[::4]):
    row = diff[i*4, :]
    all_rap = (row > 0).all()
    frac = (row > 0).mean() * 100
    print(f"  growth {g*100:.1f}%: RAP has lower NPV in {frac:.0f}% of debt levels tested"
          f"{'  (ALL)' if all_rap else ''}")

# ===========================================================================
# GENERALIZED MAP 2: RAP vs Tiered Standard, new borrowers.
# Same starting AGI for continuity; debt range capped near new aggregate
# undergraduate limits.
# ===========================================================================
grid_rap2 = np.zeros((len(growths), len(debts)))
grid_std2 = np.zeros((len(growths), len(debts)))
for i, g in enumerate(growths):
    for j, d in enumerate(debts):
        res_r, traj_r = simulate_rap(d, starting_agi, RATE_UNDERGRAD, g, dependents=0)
        tb_r = tax_bomb(res_r["forgiven_balance"], res_r["final_agi"], res_r["months_to_resolution"] / 12.0)
        fm_r = res_r["months_to_resolution"] if res_r["forgiven_balance"] > 0 else None
        grid_rap2[i, j] = compute_npv_from_traj(traj_r, tb_r, fm_r, 0.05)

        res_s, traj_s = simulate_tiered_standard(d, RATE_UNDERGRAD)
        grid_std2[i, j] = compute_npv_from_traj(traj_s, 0, None, 0.05)

diff2 = grid_std2 - grid_rap2
np.save("../data/grid_rap2_npv.npy", grid_rap2)
np.save("../data/grid_std2_npv.npy", grid_std2)
pct_rap_cheaper2 = (diff2 > 0).mean() * 100
print(f"\n=== GENERALIZED MAP: RAP vs Tiered Standard, starting AGI=${starting_agi:,} ===")
print(f"RAP has lower NPV in {pct_rap_cheaper2:.1f}% of the {diff2.size} grid cells")
neg_cells = np.argwhere(diff2 < 0)
print(f"Number of cells where Tiered Standard is actually cheaper: {len(neg_cells)}")
if len(neg_cells) > 0:
    for idx in neg_cells[:10]:
        i, j = idx
        print(f"   growth={growths[i]*100:.2f}%, debt=${debts[j]:,}: "
              f"NPV(RAP)=${grid_rap2[i,j]:,.0f} NPV(Std)=${grid_std2[i,j]:,.0f}")

# ===========================================================================
# DEPENDENT-CREDIT COMPARISON: RAP's flat $50/mo/dependent vs. the
# family-size-adjusted poverty-guideline deduction legacy IDR plans use.
# ===========================================================================
print("\n=== DEPENDENT / FAMILY-SIZE ADJUSTMENT COMPARISON ===")
print("RAP: flat $50/month reduction per dependent, regardless of income.")
print("Legacy IBR: discretionary income = AGI - 150% x FPL(family size).")
print(f"{'AGI':>10} {'Fam size':>9} {'RAP credit/mo':>15} {'IBR value/mo (10%)':>20}")
for agi in [40000, 60000, 90000]:
    for fam in [1, 2, 3, 4]:
        rap_credit = RAP_DEPENDENT_CREDIT * (fam - 1)  # value of having (fam-1) dependents under RAP
        di_1 = max(0, agi - 1.5 * fpl(1))
        di_fam = max(0, agi - 1.5 * fpl(fam))
        ibr_value = (di_1 - di_fam) * 0.10 / 12  # monthly value of the larger family-size deduction
        print(f"{agi:>10,} {fam:>9} {rap_credit:>15,.2f} {ibr_value:>20,.2f}")
