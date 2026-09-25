# RAP / IBR / Tiered Standard repayment model

Month-by-month simulation of federal student loan repayment under the
Repayment Assistance Plan (RAP), legacy Income-Based Repayment (IBR), and
the new Tiered Standard plan, plus the notch/bunching, bracket-creep,
break-even, and grid analyses built on top of it.

## Layout

```
project/
  code/      <- all scripts below live here; run them from inside this directory
  data/      <- created automatically: CSVs and .npy arrays
  figs/      <- created automatically: PNG figures and table images
```

## Reproducing everything

```
cd code/
pip install -r requirements.txt
python reproduce_all.py
```

This runs the full pipeline in dependency order and regenerates every CSV,
array, and figure/table image (Tables 1-2, Figures 1-10) from scratch. Each
script can also be run individually, in this order, from inside `code/`:

1. `run_all_analysis.py` -- notch table, dominated-region (bunching)
   analysis, the four archetype simulations (A-D), bracket creep, combined
   marginal rates, break-even growth rate, discount-rate sensitivity
2. `bunching_and_sensitivity.py` -- a supplementary pass re-deriving the
   dominated-region and break-even results (with a closed-form consistency
   check) and the discount-rate sensitivity printout
3. `generalized_maps.py` -- the debt x income-growth grids behind Figures
   8-9, plus the dependent-credit comparison
4. `fast_stochastic.py` -- Gauss-Hermite quadrature machinery for Figure 10,
   with a cross-validation checkpoint against the canonical payment formula
5. `make_figures.py`, `make_heatmaps.py`, `make_fig10.py`, `make_tables.py`
   -- render Figures 1-10 and Tables 1-2 from the CSVs/arrays above

## Modules

- `params.py` -- every statutory/economic constant (RAP brackets, IBR
  formula, Tiered Standard tiers, tax brackets, FPL, interest rates,
  inflation assumption) and the pure functions that turn AGI into a
  required payment or a tax liability. Single source of truth: every other
  file imports from here rather than re-deriving these numbers.
- `simulate.py` -- the month-by-month engine (`simulate_rap`,
  `simulate_ibr`, `simulate_tiered_standard`), `npv`, `tax_bomb`, and the
  shared `compute_npv_from_traj` helper.

## Modeling framework: nominal dollars throughout

Loan balances, payments, and AGI trajectories are all in nominal
(current-year) dollars; RAP's payment brackets are fixed nominal thresholds
(not inflation-indexed, by statute). Because of that, the NPV discount rate
used everywhere (5%, as a default) should be read as a **nominal** discount
rate, and federal tax brackets -- which *are* inflation-indexed annually
under current law -- are projected forward to whatever calendar year a
forgiveness event actually falls in (`years_from_2026` in `tax_bomb`) rather
than held at frozen 2026 levels. See the docstring at the top of `params.py`
for the full explanation.

## Code audit -- fixes made against the January 2026 reviewer critique

- **RAP principal match** (`simulate.py`): corrected to match the statute --
  the government match brings total principal reduction up to the lesser of
  $50 or the borrower's total monthly payment, not an unconditional $50
  (confirmed against CRS and Federal Student Aid servicer guidance on the
  final rule). Verified this changes no currently-reported archetype or
  grid number, since every starting AGI used in this codebase (>=$42,000)
  already produces a payment above $50; it matters for any lower-income
  scenario (see example in the audit notes / conversation).
- **Tax brackets projected forward** (`params.py`, `simulate.py`): federal
  tax brackets and the standard deduction are now inflated to the calendar
  year a forgiveness event actually occurs (`INFLATION_RATE`, shared with
  the bracket-creep analysis) rather than always using 2026 brackets for
  forgiveness happening 20-30 years out. This meaningfully changes
  Archetype B's tax bomb and the RAP-vs-IBR grid (Figure 8); it does not
  change Figures 1-3, 5-7 or Archetypes A/C/D, none of which have a taxable
  forgiveness event.
- **Tiered Standard $50 minimum payment** (`simulate.py`): added the
  statutory payment floor, which was entirely absent from the model. Also
  added explicit early-payoff detection (matching `simulate_rap`/
  `simulate_ibr`) so a floored payment that clears a small balance early
  doesn't keep recording phantom payments against a zero balance. Doesn't
  change any balance used in this paper (all comfortably amortize above
  $50/month) but matters for smaller loans.
- **Deduplication**: `compute_npv_from_traj` was implemented identically in
  three separate files; consolidated into `simulate.py` so the three
  callers can't silently drift apart. Same for the vectorized RAP payment
  formula in `fast_stochastic.py`, which previously re-hardcoded the
  bracket thresholds/rates/floor/dependent-credit instead of deriving them
  from `params.RAP_BRACKETS`; a cross-validation checkpoint now asserts the
  two implementations agree at every bracket boundary.
- **Terminology**: "utility-maximizing" -> "expected-net-income-maximizing"
  in code comments (the model has no labor disutility or leisure
  preference); "RAP wins"/"beats" -> "RAP has/produces the lower modeled
  NPV" in diagnostic prints and figure titles, consistent with the paper's
  own "not a population claim" framing.
- **Robustness**: Figure 8's color scale was missing the defensive
  `vmin`/contour guard that Figure 9 already had, which would crash
  `TwoSlopeNorm` if a future parameterization ever produced an all-positive
  grid; added for consistency.
- Everything else audited and left unchanged: the notch/bunching math, the
  IBR and RAP payment formulas themselves, the interest-waiver logic, the
  Tiered Standard term tiers, and every loan interest rate and FPL/tax
  constant, are confirmed correct against primary/authoritative sources.
