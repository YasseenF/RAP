import sys
sys.path.insert(0, ".")
from fast_stochastic import expected_payment_vec
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

NAVY = "#1a3a5c"; RED = "#b3341f"; GOLD = "#c98a1f"; TEAL = "#1f7a6c"; LIGHT = "#e8edf2"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": "#333333",
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})

targets = np.linspace(46000, 54000, 800)
fig, ax = plt.subplots(figsize=(7.0, 4.4), dpi=200)
configs = [
    (0, "#999999", "No uncertainty (deterministic)", 1.6),
    (100, GOLD, "$100 income uncertainty", 1.8),
    (500, TEAL, "$500 income uncertainty", 2.0),
    (2000, RED, "$2,000 income uncertainty", 2.2),
    (5000, NAVY, "$5,000 income uncertainty", 2.4),
]
for sigma, color, label, lw in configs:
    pay = expected_payment_vec(targets, sigma)
    ax.plot(targets, pay, color=color, linewidth=lw, label=label)

ax.axvline(50000, color="black", linewidth=0.8, linestyle=":", alpha=0.5)
ax.set_xlabel("Target / expected AGI near the $50,000 threshold")
ax.set_ylabel("Expected annual RAP payment")
ax.set_title("Figure 10.  Income uncertainty smooths the notch into a gentle curve;\n"
             "a few hundred to a few thousand dollars of surprise already blunts most of the cliff",
             fontsize=10, loc="left")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: f"${x:,.0f}"))
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: f"${x:,.0f}"))
ax.legend(loc="upper left", fontsize=8.5, frameon=False)
ax.grid(axis="y", color=LIGHT, linewidth=0.8)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig("../figs/fig10_stochastic_buffer.png")
print("saved fig10")
