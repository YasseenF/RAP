# Replication Package: "Payment Cliffs and Deferred Taxation Under the Federal
# Student Loan Repayment Assistance Plan"

This folder contains the complete simulation code, generated data, and figures
underlying every number, table, and figure in the paper. It is the package
referenced in the paper's "Data and Code Availability" section.

## Requirements

Python 3.10+ with: numpy, pandas, matplotlib, scipy

    pip install numpy pandas matplotlib scipy --break-system-packages

## Structure

    code/    all analysis scripts (see run order below)
    data/    CSV outputs from each script (regenerated when you run the scripts)
    figs/    PNG figures and tables (regenerated when you run the scripts)

## Core modules

- `params.py` -- every statutory/regulatory parameter used in the model
  (RAP's payment schedule, legacy IBR formula, federal poverty guidelines,
  2026 tax brackets, FICA rates, federal loan interest rates), each sourced
  to a specific reference in the paper's bibliography. Includes the RAP
  payment function, validated against the Department of Education's own
  worked example ($45,000 AGI -> $150.00/month).
- `simulate.py` -- the month-by-month lifecycle simulation engine for RAP,
  legacy IBR, and the Tiered Standard Plan, plus NPV and tax-liability
  ("tax bomb") calculation functions.

## How to reproduce everything, in order

    cd code
    python3 run_all_analysis.py        # notch table, dominated regions,
                                        # 4 archetypes, bracket creep,
                                        # combined marginal rates,
                                        # break-even growth sweep,
                                        # discount-rate sensitivity
    python3 generalized_maps.py        # Fig. 8 / Fig. 9 debt x growth grids
                                        # + dependent-credit comparison
    python3 fast_stochastic.py         # validates the quadrature model
                                        # against the checkpoint case
    python3 make_fig10.py              # Fig. 10 (income-uncertainty smoothing)
    python3 make_figures.py            # Fig. 1-7
    python3 make_heatmaps.py           # Fig. 8-9 (rendered)
    python3 make_tables.py             # Table 1-2 (rendered as images)

Each script prints its own numeric results to stdout as it runs (including
the validation checkpoints) and writes CSVs to `../data/` and PNGs to
`../figs/`. Every dollar figure, percentage, and year count quoted in the
paper can be found in the corresponding printed output or CSV.

## Key validation checkpoints

Run these first if you only want to confirm the model is correctly
implemented before trusting anything else:

    python3 -c "
    import sys; sys.path.insert(0, '.')
    from params import rap_monthly_payment
    print(rap_monthly_payment(45000, 0))   # must print 150.0
    print(rap_monthly_payment(120000, 0))  # must print 1000.0
    "

Both values are drawn directly from the Department of Education's own
published worked examples (see paper, Sec. II-A).

## Notes on reproducibility

- All Monte Carlo / quadrature calculations use fixed random seeds or
  deterministic quadrature nodes, so re-running any script reproduces the
  paper's numbers exactly (confirmed by re-running the full pipeline from a
  clean `data/` directory before packaging this release).
- File paths are relative; run scripts from inside `code/`.
