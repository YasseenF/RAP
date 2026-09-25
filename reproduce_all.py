"""
reproduce_all.py

Runs the full RAP analysis pipeline end-to-end, in dependency order, and
regenerates every CSV, .npy array, and figure/table image used in the paper
from scratch. Intended to be the single command a reviewer needs:

    python reproduce_all.py

Expected layout (this file lives in the `code/` directory alongside the
other analysis scripts; `data/` and `figs/` are created automatically as
siblings of `code/`):

    project/
      code/            <- this file and all analysis scripts
        reproduce_all.py
        params.py
        simulate.py
        ...
      data/            <- created automatically; CSV / .npy outputs
      figs/            <- created automatically; PNG figures/tables

Each step is run as a separate subprocess (rather than imported) because the
analysis scripts are written as top-level scripts that execute on import;
running them as subprocesses keeps each script's globals isolated and
matches exactly how they behave when run individually, which is how they
were developed and checked.
"""
import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Order matters: later scripts read CSV/.npy files earlier scripts write.
PIPELINE = [
    "run_all_analysis.py",          # notch table, dominated regions, archetypes A-D,
                                     # bracket creep, combined marginal rates,
                                     # break-even growth, discount-rate sensitivity
    "bunching_and_sensitivity.py",  # supplementary/consistency-check pass over the
                                     # dominated-region and break-even analyses above,
                                     # plus the discount-rate sensitivity printout
    "generalized_maps.py",          # debt x income-growth grids (RAP vs IBR, RAP vs Std)
    "fast_stochastic.py",           # Gauss-Hermite quadrature + cross-validation checkpoint
    "make_figures.py",              # Figures 1-7
    "make_heatmaps.py",             # Figures 8-9
    "make_fig10.py",                # Figure 10
    "make_tables.py",               # Tables 1-2
]


def main():
    os.makedirs(os.path.join(SCRIPT_DIR, "..", "data"), exist_ok=True)
    os.makedirs(os.path.join(SCRIPT_DIR, "..", "figs"), exist_ok=True)
    for script in PIPELINE:
        print(f"\n{'=' * 70}\nRunning {script}\n{'=' * 70}")
        result = subprocess.run([sys.executable, script], cwd=SCRIPT_DIR)
        if result.returncode != 0:
            print(f"\n!! {script} exited with code {result.returncode} -- stopping.")
            sys.exit(result.returncode)
    print("\nAll steps completed successfully.")
    print("Tables/CSVs/arrays: ../data    Figures/table images: ../figs")


if __name__ == "__main__":
    main()
