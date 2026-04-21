"""Monte Carlo simulation engine for DCF valuation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
from scipy import stats

from dcf_engine import DCFInputs, run_dcf


@dataclass
class MonteCarloInputs:
    """Parameters for the Monte Carlo simulation."""
    base_revenue: float
    growth_rate: float          # base (mode) for triangular
    ebitda_margin: float        # base (mode) for triangular
    da_pct: float
    capex_pct: float
    nwc_pct: float
    tax_rate: float
    wacc: float                 # base for truncated normal
    terminal_growth: float      # base for uniform
    exit_multiple: float        # base for truncated normal
    use_perpetuity: bool
    net_debt: float
    shares: float
    current_price: float
    n_years: int = 5

    # Triangular spread parameters
    growth_spread: float = 0.05
    margin_spread_down: float = 0.05
    margin_spread_up: float = 0.03
    wacc_sigma: float = 0.01
    tg_spread: float = 0.01
    multiple_sigma: float = 2.0


@dataclass
class MonteCarloResults:
    """Output of the Monte Carlo simulation."""
    prices: np.ndarray
    mean: float
    median: float
    std: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    var5: float
    prob_upside: float
    cv: float


def run_simulation(inputs: MonteCarloInputs, n_sims: int = 10_000) -> MonteCarloResults:
    """Run correlated Monte Carlo simulation and return implied share prices.

    Uses Cholesky decomposition on a 4×4 correlation matrix, then transforms
    correlated standard normals to the target marginal distributions via the
    probability integral transform (copula method).

    Correlation structure:
      - growth ↔ margin: +0.3
      - WACC ↔ terminal_g: +0.2
      - all other pairs: 0

    Args:
        inputs: MonteCarloInputs with base parameters and spread assumptions.
        n_sims: Number of simulations.

    Returns:
        MonteCarloResults dataclass with statistics.
    """
    rng = np.random.default_rng()

    # 4×4 correlation matrix: [growth, margin, wacc, terminal_g]
    corr = np.array([
        [1.0, 0.3, 0.0, 0.0],
        [0.3, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.2],
        [0.0, 0.0, 0.2, 1.0],
    ])
    L = np.linalg.cholesky(corr)

    Z = rng.standard_normal((n_sims, 4))
    correlated = Z @ L.T

    # Transform to uniform [0, 1] via normal CDF
    u = stats.norm.cdf(correlated)

    # --- Growth: triangular ---
    g = inputs.growth_rate
    g_min = g - inputs.growth_spread
    g_max = g + inputs.growth_spread
    c_g = (g - g_min) / (g_max - g_min) if g_max != g_min else 0.5
    growth_draws = stats.triang.ppf(u[:, 0], c=c_g, loc=g_min, scale=g_max - g_min)

    # --- Margin: triangular (slight downward skew) ---
    m = inputs.ebitda_margin
    m_min = m - inputs.margin_spread_down
    m_max = m + inputs.margin_spread_up
    c_m = (m - m_min) / (m_max - m_min) if m_max != m_min else 0.5
    margin_draws = stats.triang.ppf(u[:, 1], c=c_m, loc=m_min, scale=m_max - m_min)

    # --- WACC: truncated normal ±3σ ---
    wacc_draws = stats.truncnorm.ppf(
        u[:, 2],
        a=-3, b=3,
        loc=inputs.wacc,
        scale=inputs.wacc_sigma,
    )

    # --- Terminal growth: uniform, clamped so WACC > g always ---
    tg_min = inputs.terminal_growth - inputs.tg_spread
    tg_max = inputs.terminal_growth + inputs.tg_spread
    tg_draws = stats.uniform.ppf(u[:, 3], loc=tg_min, scale=tg_max - tg_min)
    # Enforce WACC > terminal growth with 0.5% buffer
    tg_draws = np.minimum(tg_draws, wacc_draws - 0.005)

    # --- Exit multiple: truncated normal ---
    em = inputs.exit_multiple
    em_lo = max(1.0, em - 6.0)
    em_hi = em + 6.0
    em_a = (em_lo - em) / inputs.multiple_sigma
    em_b = (em_hi - em) / inputs.multiple_sigma
    multiple_draws = stats.truncnorm.ppf(
        u[:, 0],  # reuse growth uniform, independent from tg
        a=em_a, b=em_b,
        loc=em,
        scale=inputs.multiple_sigma,
    )

    # --- Run DCF for each simulation ---
    growth_rates = [inputs.growth_rate] * inputs.n_years
    prices = np.empty(n_sims)

    for i in range(n_sims):
        sim_growth = float(growth_draws[i])
        sim_margin = float(margin_draws[i])
        sim_wacc = float(wacc_draws[i])
        sim_tg = float(tg_draws[i])
        sim_multiple = float(multiple_draws[i])

        sim_growth_rates = [sim_growth] * inputs.n_years

        dcf_inputs = DCFInputs(
            base_revenue=inputs.base_revenue,
            growth_rates=sim_growth_rates,
            ebitda_margin=sim_margin,
            da_pct=inputs.da_pct,
            capex_pct=inputs.capex_pct,
            nwc_pct=inputs.nwc_pct,
            tax_rate=inputs.tax_rate,
            wacc=sim_wacc,
            terminal_growth=sim_tg,
            exit_multiple=sim_multiple,
            use_perpetuity=inputs.use_perpetuity,
            net_debt=inputs.net_debt,
            shares=inputs.shares,
            current_price=inputs.current_price,
        )
        try:
            result = run_dcf(dcf_inputs)
            prices[i] = result["implied_price"]
        except Exception:
            prices[i] = float("nan")

    # Drop NaN results
    valid = prices[~np.isnan(prices)]
    if len(valid) == 0:
        valid = np.array([0.0])

    mean = float(np.mean(valid))
    median = float(np.median(valid))
    std = float(np.std(valid))
    p10, p25, p50, p75, p90 = np.percentile(valid, [10, 25, 50, 75, 90])
    var5 = float(np.percentile(valid, 5))
    prob_upside = float(np.mean(valid > inputs.current_price)) if inputs.current_price > 0 else 0.0
    cv = std / mean if mean != 0 else 0.0

    return MonteCarloResults(
        prices=valid,
        mean=mean,
        median=median,
        std=std,
        p10=float(p10),
        p25=float(p25),
        p50=float(p50),
        p75=float(p75),
        p90=float(p90),
        var5=var5,
        prob_upside=prob_upside,
        cv=cv,
    )
