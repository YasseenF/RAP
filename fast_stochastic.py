import sys
sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from scipy.special import roots_hermite
from params import RAP_BRACKETS, RAP_FLOOR_MONTHLY, RAP_DEPENDENT_CREDIT, rap_monthly_payment

# Derive the vectorized bracket thresholds/rates from RAP_BRACKETS itself
# (single source of truth -- params.py) rather than hardcoding them a second
# time here. RAP_BRACKETS = [(10000,20000,.01), ..., (100000,inf,.10)];
# the "agi<=10000" floor regime is handled separately below via np.where,
# so we only need the upper edge and rate of each bracket.
_THRESHOLDS = [hi for (lo, hi, rate) in RAP_BRACKETS]  # [20000, 30000, ..., inf]
_RATES = [rate for (lo, hi, rate) in RAP_BRACKETS]      # [0.01, 0.02, ..., 0.10]

def rap_annual_payment_vec(agi, dependents=0):
    agi = np.clip(np.asarray(agi, dtype=float), 0, None)
    rate = np.select(
        [agi <= hi for hi in _THRESHOLDS[:-1]],  # last bracket's hi is inf -> use as default
        _RATES[:-1],
        default=_RATES[-1],
    )
    base_monthly = np.where(agi <= 10000, RAP_FLOOR_MONTHLY, agi * rate / 12.0)
    payment_monthly = np.maximum(base_monthly - RAP_DEPENDENT_CREDIT * dependents, RAP_FLOOR_MONTHLY)
    return payment_monthly * 12.0

# Cross-check the vectorized formula against the canonical scalar
# implementation in params.py, at every bracket boundary and a few
# dependent counts, so a future edit to either copy that breaks the
# equivalence is caught immediately rather than silently biasing Figure 10.
_test_agis = np.array([0, 5000, 10000, 10000.01, 12000, 20000, 20000.01,
                        45000, 100000, 100000.01, 150000])
for _dep in (0, 1, 3):
    _vec = rap_annual_payment_vec(_test_agis, _dep) / 12.0
    _scalar = np.array([rap_monthly_payment(a, _dep) for a in _test_agis])
    assert np.allclose(_vec, _scalar, atol=0.01), (
        f"rap_annual_payment_vec diverges from params.rap_monthly_payment "
        f"at dependents={_dep}: vec={_vec} vs scalar={_scalar}")
print("Checkpoint OK: vectorized RAP payment matches scalar params.rap_monthly_payment "
      "across all bracket boundaries and dependent counts tested.")

# ---- Gauss-Hermite quadrature nodes/weights for E[f(target + sigma*eps)], eps~N(0,1) ----
N_NODES = 40
_nodes, _weights = roots_hermite(N_NODES)  # for integral against e^{-x^2}
_nodes = _nodes * np.sqrt(2)               # rescale: eps = sqrt(2)*u
_weights = _weights / np.sqrt(np.pi)       # normalize

def expected_payment_vec(targets, sigma):
    """targets: 1D array. Returns E[payment(target + sigma*eps)] for each target,
    via Gauss-Hermite quadrature (exact for polynomials, very accurate for this
    piecewise-linear-with-jumps integrand given enough nodes)."""
    targets = np.asarray(targets, dtype=float)
    if sigma == 0:
        return rap_annual_payment_vec(targets)
    # shape: (n_targets, n_nodes)
    grid = targets[:, None] + sigma * _nodes[None, :]
    pay = rap_annual_payment_vec(grid.ravel()).reshape(grid.shape)
    return pay @ _weights

def expected_net_income_vec(targets, sigma):
    return targets - expected_payment_vec(targets, sigma)

def optimal_target_fast(threshold, sigma, search_window=2500, step=5):
    candidates = np.arange(threshold - search_window, threshold + 1, step)
    net_income = expected_net_income_vec(candidates, sigma)
    i = np.argmax(net_income)
    return candidates[i], net_income[i]

if __name__ == "__main__":
    # quick validation against the (slow) Monte Carlo results already on file
    for T, s, expect_buf in [(50000, 0, 0), (50000, 100, 120), (50000, 5000, 0), (100000, 0, 0)]:
        t_star, _ = optimal_target_fast(T, s)
        buf = T - t_star
        print(f"T=${T:,} sigma=${s}: buffer=${buf} (MC gave ~${expect_buf})")
