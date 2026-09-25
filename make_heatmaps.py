import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import TwoSlopeNorm

FIGDIR = "../figs"
DATADIR = "../data"
NAVY = "#1a3a5c"; RED = "#b3341f"; LIGHT = "#e8edf2"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11,
    "axes.edgecolor": "#333333", "axes.labelcolor": "#222222", "text.color": "#222222",
    "xtick.color": "#333333", "ytick.color": "#333333",
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})

debts = np.load(f"{DATADIR}/grid_debts.npy")
growths = np.load(f"{DATADIR}/grid_growths.npy")
grid_rap = np.load(f"{DATADIR}/grid_rap_npv.npy")
grid_ibr = np.load(f"{DATADIR}/grid_ibr_npv.npy")
grid_rap2 = np.load(f"{DATADIR}/grid_rap2_npv.npy")
grid_std2 = np.load(f"{DATADIR}/grid_std2_npv.npy")

# Fig 8: RAP vs IBR heatmap, existing borrowers
diff_pct = (grid_ibr - grid_rap) / grid_ibr * 100  # % of IBR's NPV saved by choosing RAP
fig, ax = plt.subplots(figsize=(6.9, 4.6), dpi=200)
vmax = max(diff_pct.max(), 1)
vmin = min(diff_pct.min(), -1)  # guard: TwoSlopeNorm requires vmin < 0 < vmax
norm = TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
im = ax.pcolormesh(debts, growths * 100, diff_pct, shading="auto", cmap="RdBu", norm=norm)
cbar = fig.colorbar(im, ax=ax, pad=0.02)
cbar.set_label("Blue = RAP lower modeled NPV, red = IBR lower modeled NPV\n"
               "(% difference in modeled borrower-cost NPV, not % of borrowers)", fontsize=8.5)
if diff_pct.min() < 0:
    CS = ax.contour(debts, growths * 100, diff_pct, levels=[0], colors="black", linewidths=1.8)
    ax.clabel(CS, inline=True, fmt="break-even", fontsize=8)
ax.set_xlabel("Starting federal loan balance")
ax.set_ylabel("Assumed annual income growth rate")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: f"${x/1000:,.0f}k"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: f"{x:.0f}%"))
ax.set_title("Figure 8.  RAP produces a lower modeled NPV than legacy IBR across\n"
              "most of the debt/income-growth space, and most strongly at low growth rates",
              fontsize=10, loc="left")
fig.tight_layout()
fig.savefig(f"{FIGDIR}/fig8_heatmap_rap_vs_ibr.png")
plt.close(fig)

# Fig 9: RAP vs Tiered Standard heatmap, new borrowers
diff_pct2 = (grid_std2 - grid_rap2) / grid_std2 * 100
fig, ax = plt.subplots(figsize=(6.9, 4.6), dpi=200)
vmax2 = max(diff_pct2.max(), 1)
vmin2 = min(diff_pct2.min(), -1)
norm2 = TwoSlopeNorm(vmin=vmin2, vcenter=0, vmax=vmax2)
im2 = ax.pcolormesh(debts, growths * 100, diff_pct2, shading="auto", cmap="RdBu", norm=norm2)
cbar2 = fig.colorbar(im2, ax=ax, pad=0.02)
cbar2.set_label("Blue = RAP lower modeled NPV, red = Tiered Standard lower modeled NPV\n"
                "(% difference in modeled borrower-cost NPV, not % of borrowers)", fontsize=8.5)
if diff_pct2.min() < 0:
    CS2 = ax.contour(debts, growths * 100, diff_pct2, levels=[0], colors="black", linewidths=1.8)
    ax.clabel(CS2, inline=True, fmt="break-even", fontsize=8)
ax.set_xlabel("Starting federal loan balance")
ax.set_ylabel("Assumed annual income growth rate")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: f"${x/1000:,.0f}k"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: f"{x:.0f}%"))
ax.set_title("Figure 9.  RAP produces the lower modeled NPV than Tiered Standard\n"
              "almost everywhere; the exception is small, stagnant-income balances under ~$20,000",
              fontsize=10, loc="left")
fig.tight_layout()
fig.savefig(f"{FIGDIR}/fig9_heatmap_rap_vs_standard.png")
plt.close(fig)

print("Wrote fig8 and fig9")
print(f"Fig 8 range: {diff_pct.min():.1f}% to {diff_pct.max():.1f}%")
print(f"Fig 9 range: {diff_pct2.min():.1f}% to {diff_pct2.max():.1f}%")
