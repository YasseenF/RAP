import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams["text.usetex"] = False
try:
    matplotlib.rcParams["text.parse_math"] = False  # matplotlib >=3.4: disables $ mathtext entirely
except KeyError:
    pass

NAVY = "#1a3a5c"
LIGHT = "#eef2f6"
WHITE = "#ffffff"

# ============================= TABLE 1: RAP Schedule =============================
rows1 = [
    ["AGI \u2264 $10,000", "$10.00 / month (flat minimum)"],
    ["$10,001 \u2013 $20,000", "1% of AGI"],
    ["$20,001 \u2013 $30,000", "2% of AGI"],
    ["$30,001 \u2013 $40,000", "3% of AGI"],
    ["$40,001 \u2013 $50,000", "4% of AGI"],
    ["$50,001 \u2013 $60,000", "5% of AGI"],
    ["$60,001 \u2013 $70,000", "6% of AGI"],
    ["$70,001 \u2013 $80,000", "7% of AGI"],
    ["$80,001 \u2013 $90,000", "8% of AGI"],
    ["$90,001 \u2013 $100,000", "9% of AGI"],
    ["$100,001 and above", "10% of AGI"],
]
fig, ax = plt.subplots(figsize=(7.6, 5.0), dpi=200)
ax.axis("off")
tbl = ax.table(
    cellText=rows1,
    colLabels=["Adjusted Gross Income (AGI)", "Required Annual Payment"],
    cellLoc="center", loc="center", colWidths=[0.5, 0.5],
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(13)
tbl.scale(1, 2.05)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor("#bbbbbb")
    if r == 0:
        cell.set_facecolor(NAVY)
        cell.set_text_props(color="white", weight="bold")
    else:
        cell.set_facecolor(LIGHT if r % 2 == 0 else WHITE)
fig.tight_layout()
fig.savefig("../figs/table1_rap_schedule.png", bbox_inches="tight", pad_inches=0.15)
plt.close(fig)

# ============================= TABLE 2: Archetype Summary =============================
df = pd.read_csv("../data/archetype_summary.csv")
label_map = {
    "A. New Teacher ($30k debt, 6.52%)": "A. Teacher\n$30k debt",
    "B. Caseworker ($95k debt, 8.07%)": "B. Caseworker\n$95k debt",
    "C. Early-Career Engineer ($32k debt, 6.52%)": "C. Engineer\n$32k debt",
    "D. New Physician ($200k debt, 8.07%)": "D. Physician\n$200k debt",
}
rows2 = []
for _, r in df.iterrows():
    rows2.append([
        label_map.get(r["Archetype"], r["Archetype"]),
        r["Plan"],
        f"{r['Years']:.1f}",
        r["Ends_in"],
        f"${r['Forgiven_balance']:,.0f}" if r["Forgiven_balance"] > 0 else "\u2014",
        f"${r['Tax_bomb']:,.0f}" if r["Tax_bomb"] > 0 else "\u2014",
        f"${r['Total_paid_nominal']:,.0f}",
        f"${r['NPV_5pct']:,.0f}",
    ])

fig, ax = plt.subplots(figsize=(10.4, 4.6), dpi=200)
ax.axis("off")
col_labels = ["Archetype", "Plan", "Years", "Ends in", "Forgiven\nBalance", "Tax\nBomb",
              "Total Paid\n(Nominal)", "NPV\n(5%)"]
tbl = ax.table(cellText=rows2, colLabels=col_labels, cellLoc="center", loc="center",
               colWidths=[0.15, 0.13, 0.07, 0.11, 0.12, 0.11, 0.13, 0.11])
tbl.auto_set_font_size(False)
tbl.set_fontsize(11.5)
tbl.scale(1, 2.6)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor("#bbbbbb")
    if r == 0:
        cell.set_facecolor(NAVY)
        cell.set_text_props(color="white", weight="bold")
    else:
        arche_row = (r - 1) // 2
        cell.set_facecolor(LIGHT if arche_row % 2 == 0 else WHITE)
    if c == 0:
        cell.set_text_props(ha="left")
        cell._text.set_ha("left")
fig.tight_layout()
fig.savefig("../figs/table2_archetype_summary.png", bbox_inches="tight", pad_inches=0.15)
plt.close(fig)

print("Wrote table1 and table2 images")
