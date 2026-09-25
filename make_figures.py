import sys, os, json
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from params import rap_monthly_payment, RAP_BRACKETS

FIGDIR = "../figs"
DATADIR = "../data"

NAVY = "#1a3a5c"; RED = "#b3341f"; GOLD = "#c98a1f"; TEAL = "#1f7a6c"
GRAY = "#6b6b6b"; LIGHT = "#e8edf2"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.edgecolor": "#333333", "axes.labelcolor": "#222222", "text.color": "#222222",
    "xtick.color": "#333333", "ytick.color": "#333333",
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})

def dollar_fmt(x, pos):
    return f"${x/1000:,.0f}k" if x >= 1000 else f"${x:,.0f}"

def pct_fmt(x, pos):
    return f"{x:.0f}%"

# Fig 1: notch structure
fig, ax = plt.subplots(figsize=(6.6, 4.0), dpi=200)
agis = np.linspace(0, 150000, 3000)
payments = [rap_monthly_payment(a, 0) * 12 for a in agis]
ax.plot(agis, payments, color=NAVY, linewidth=2.2)
ax.fill_between(agis, 0, payments, color=NAVY, alpha=0.08)
for lo, hi, rate in RAP_BRACKETS:
    if lo == 100000:
        continue
    below = rap_monthly_payment(lo, 0) * 12
    above = rap_monthly_payment(lo + 1, 0) * 12
    if above - below > 1:
        ax.plot([lo, lo], [below, above], color=RED, linewidth=1.4, linestyle=(0, (2, 1.5)))
        ax.scatter([lo], [above], color=RED, s=14, zorder=5)
ax.set_xlabel("Adjusted gross income (AGI)")
ax.set_ylabel("Required annual RAP payment")
ax.set_title("Figure 1.  RAP's required payment jumps at every $10,000 threshold\n"
              "(each dashed red segment is a payment cliff, not a smooth marginal increase)",
              fontsize=10.5, loc="left")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(dollar_fmt))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(dollar_fmt))
ax.set_xlim(0, 150000); ax.set_ylim(0, 15500)
ax.grid(axis="y", color=LIGHT, linewidth=0.8); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig1_rap_notch_structure.png"); plt.close(fig)

# Fig 2: notch magnitudes
notch_df = pd.read_csv(f"{DATADIR}/notch_table.csv")
real_notches = notch_df[notch_df["dollar_jump"] > 1].copy()
real_notches["pct"] = real_notches["implicit_marginal_pct"]
fig, ax = plt.subplots(figsize=(6.6, 4.0), dpi=200)
ax.bar(real_notches["threshold"] / 1000, real_notches["pct"] / 1000, width=6.5,
       color=GOLD, edgecolor="#8a5f10", linewidth=0.8)
ax.set_xlabel("RAP income threshold crossed (AGI, $000s)")
ax.set_ylabel("Implicit marginal rate on that\nsingle dollar of income (%, thousands)")
ax.set_title("Figure 2.  Earning the single dollar that crosses a RAP threshold\n"
              "carries an implicit marginal rate of 20,000%\u2013100,000%",
              fontsize=10.5, loc="left")
for x, y, pct in zip(real_notches["threshold"] / 1000, real_notches["pct"] / 1000, real_notches["pct"]):
    ax.text(x, y + 1.5, f"{pct:,.0f}%", ha="center", va="bottom", fontsize=8.2, color="#5c3d0a")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: f"{x:.0f}k%"))
ax.set_ylim(0, 115)
ax.grid(axis="y", color=LIGHT, linewidth=0.8); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig2_notch_magnitudes.png"); plt.close(fig)

# Fig 3: combined marginal rates
cmr = pd.read_csv(f"{DATADIR}/combined_marginal_rates.csv")
fig, ax = plt.subplots(figsize=(7.1, 4.3), dpi=200)
ax.step(cmr["agi"], cmr["combined_marginal"] * 100, where="post", color=TEAL, linewidth=2.0)
ax.fill_between(cmr["agi"], 0, cmr["combined_marginal"] * 100, step="post", color=TEAL, alpha=0.10)
ax2 = ax.twinx()
for i, row in real_notches.iterrows():
    ax2.plot([row["threshold"], row["threshold"]], [0, row["pct"]], color=RED, linewidth=1.6, alpha=0.85, zorder=5)
    ax2.scatter([row["threshold"]], [row["pct"]], color=RED, s=16, zorder=6)
ax2.set_ylabel("RAP notch: implicit rate on the\nsingle threshold-crossing dollar (%)", color=RED)
ax2.tick_params(axis="y", colors=RED); ax2.set_ylim(0, 110000)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: f"{x/1000:,.0f}k%"))
ax.set_xlabel("Adjusted gross income (AGI)")
ax.set_ylabel("Combined marginal tax rate (%)", color=TEAL)
ax.tick_params(axis="y", colors=TEAL); ax.set_ylim(0, 45)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(dollar_fmt)); ax.set_xlim(0, 155000)
ax.set_title("Figure 3.  Two kinds of \u201cmarginal rate\u201d facing the same borrower\n"
              "(teal, left axis: ordinary sustained tax rates \u2014 red, right axis: RAP's payment cliffs)",
              fontsize=9.6, loc="left")
ax.grid(axis="y", color=LIGHT, linewidth=0.8); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig3_combined_marginal_rates.png"); plt.close(fig)

# Fig 4: bracket creep
creep = pd.read_csv(f"{DATADIR}/bracket_creep.csv")
fig, ax = plt.subplots(figsize=(6.6, 4.0), dpi=200)
ax.plot(creep["year"], creep["rap_burden_pct"], color=RED, linewidth=2.2, marker="o", markersize=3.2,
        label="RAP (thresholds fixed in nominal dollars)")
ax.plot(creep["year"], creep["ibr_burden_pct"], color=NAVY, linewidth=2.2, linestyle="--",
        label="Inflation-indexed IDR benchmark\n(legacy IBR-style discretionary income)")
ax.set_xlabel("Years since entering repayment")
ax.set_ylabel("Required payment, as a share of\nthe borrower's real (constant) income")
ax.set_title("Figure 4.  A borrower whose real income never rises still sees their\n"
              "RAP burden more than double in 25 years, from 2.7% assumed inflation alone",
              fontsize=10.3, loc="left")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(pct_fmt))
ax.legend(loc="upper left", fontsize=8.7, frameon=False)
ax.set_ylim(0, 10)
ax.grid(axis="y", color=LIGHT, linewidth=0.8); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig4_bracket_creep.png"); plt.close(fig)

# Fig 5 & 6: trajectories
with open(f"{DATADIR}/trajectories.json") as f:
    traj = json.load(f)

fig, ax = plt.subplots(figsize=(6.8, 4.2), dpi=200)
for key, color, label in [("B_RAP", RED, "RAP (30-yr forgiveness)"), ("B_NewIBR", NAVY, "New IBR (20-yr forgiveness)")]:
    t = traj[key]
    months = [row[0] for row in t]; bal = [row[4] for row in t]
    ax.plot([m / 12 for m in months], bal, color=color, linewidth=2.1, label=label)
ax.axhline(95000, color=GRAY, linewidth=1, linestyle=":")
ax.text(0.3, 97500, "original balance ($95,000)", fontsize=8, color=GRAY)
ax.set_xlabel("Years in repayment"); ax.set_ylabel("Outstanding balance")
ax.set_title("Figure 5.  Archetype B (caseworker, $95,000 debt): RAP's universal\n"
              "interest waiver prevents the balance run-up that IBR still permits", fontsize=10.3, loc="left")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(dollar_fmt))
ax.legend(loc="upper left", fontsize=9, frameon=False)
ax.grid(axis="y", color=LIGHT, linewidth=0.8); ax.set_axisbelow(True); ax.set_xlim(0, 30.3)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig5_archetypeB_trajectories.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(6.8, 4.2), dpi=200)
for key, color, label in [("D_RAP", RED, "RAP"), ("D_TieredStandard", NAVY, "Tiered Standard (25-yr fixed term)")]:
    t = traj[key]
    months = [row[0] for row in t]; bal = [row[4] for row in t]
    ax.plot([m / 12 for m in months], bal, color=color, linewidth=2.1, label=label)
ax.axvline(3, color=GRAY, linewidth=1, linestyle=":")
ax.text(3.15, 185000, "residency ends,\nattending income begins", fontsize=8, color=GRAY)
ax.set_xlabel("Years in repayment"); ax.set_ylabel("Outstanding balance")
ax.set_title("Figure 6.  Archetype D (new physician, $200,000 debt): RAP lets\n"
              "payments track a steep residency-to-attending income jump", fontsize=10.3, loc="left")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(dollar_fmt))
ax.legend(loc="upper right", fontsize=9, frameon=False)
ax.grid(axis="y", color=LIGHT, linewidth=0.8); ax.set_axisbelow(True); ax.set_xlim(0, 25.3)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig6_archetypeD_trajectories.png"); plt.close(fig)

# Fig 7: break-even growth rate (NEW)
be = pd.read_csv(f"{DATADIR}/breakeven_growth.csv")
fig, ax = plt.subplots(figsize=(6.8, 4.2), dpi=200)
ax.plot(be["growth_rate"] * 100, be["npv_rap"], color=RED, linewidth=2.2, label="RAP (NPV, varies with income growth)")
ax.axhline(be["npv_tiered_standard"].iloc[0], color=NAVY, linewidth=2.2, linestyle="--",
           label="Tiered Standard (NPV, fixed regardless of income)")
ax.set_xlabel("Assumed annual income growth rate")
ax.set_ylabel("Present value of total borrower cost\n(5% discount rate)")
ax.set_title("Figure 7.  Archetype A ($30,000 debt): RAP stays the lower-cost\n"
              "plan in present-value terms across the full range of growth rates tested",
              fontsize=10, loc="left")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: f"{x:.0f}%"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(dollar_fmt))
ax.legend(loc="lower right", fontsize=8.8, frameon=False)
ax.set_ylim(20000, 36000)
ax.grid(axis="y", color=LIGHT, linewidth=0.8); ax.set_axisbelow(True)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig7_breakeven_growth.png"); plt.close(fig)

print("All figures regenerated:")
for f in sorted(os.listdir(FIGDIR)):
    print(" ", f)
