"""DCF calculation engine — all pure functions, no Streamlit imports."""

from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List


class ValidationError(Exception):
    """Raised when input parameters fail validation."""
    pass


# ---------------------------------------------------------------------------
# Individual calculation functions
# ---------------------------------------------------------------------------

def compute_wacc(
    rf: float,
    beta: float,
    erp: float,
    cost_of_debt: float,
    tax_rate: float,
    debt_weight: float,
) -> float:
    """Compute Weighted Average Cost of Capital.

    Args:
        rf: Risk-free rate (decimal).
        beta: Equity beta.
        erp: Equity risk premium (decimal).
        cost_of_debt: Pre-tax cost of debt (decimal).
        tax_rate: Corporate tax rate (decimal).
        debt_weight: Debt / (Debt + Equity) ratio (decimal).

    Returns:
        WACC as a decimal.
    """
    equity_weight = 1.0 - debt_weight
    cost_of_equity = rf + beta * erp
    wacc = equity_weight * cost_of_equity + debt_weight * cost_of_debt * (1 - tax_rate)
    return wacc


def compute_fcff(
    revenue: float,
    ebitda_margin: float,
    tax_rate: float,
    da_pct: float,
    capex_pct: float,
    nwc_pct: float,
) -> float:
    """Compute Free Cash Flow to Firm for a single year.

    FCFF = EBIT * (1 - t) + D&A - CapEx - ΔNWC
    EBIT = EBITDA - D&A

    Args:
        revenue: Revenue for the year.
        ebitda_margin: EBITDA / Revenue (decimal).
        tax_rate: Tax rate (decimal).
        da_pct: D&A / Revenue (decimal).
        capex_pct: CapEx / Revenue (decimal).
        nwc_pct: Change in NWC / Revenue (decimal).

    Returns:
        FCFF for the year.
    """
    ebitda = revenue * ebitda_margin
    da = revenue * da_pct
    ebit = ebitda - da
    nopat = ebit * (1 - tax_rate)
    capex = revenue * capex_pct
    delta_nwc = revenue * nwc_pct
    return nopat + da - capex - delta_nwc


def project_financials(
    base_revenue: float,
    growth_rates: List[float],
    ebitda_margin: float,
    da_pct: float,
    capex_pct: float,
    nwc_pct: float,
    tax_rate: float,
) -> pd.DataFrame:
    """Project full income statement and FCFF for each forecast year.

    Args:
        base_revenue: Year-0 (current) revenue.
        growth_rates: List of annual growth rates (decimals) for each forecast year.
        ebitda_margin: EBITDA margin (decimal), constant across years.
        da_pct: D&A as % of revenue (decimal).
        capex_pct: CapEx as % of revenue (decimal).
        nwc_pct: Change in NWC as % of revenue (decimal).
        tax_rate: Tax rate (decimal).

    Returns:
        DataFrame with columns: Year, Revenue, EBITDA, DA, EBIT, NOPAT, CapEx, DeltaNWC, FCFF.
    """
    rows = []
    revenue = base_revenue
    for i, g in enumerate(growth_rates, start=1):
        revenue = revenue * (1 + g)
        ebitda = revenue * ebitda_margin
        da = revenue * da_pct
        ebit = ebitda - da
        nopat = ebit * (1 - tax_rate)
        capex = revenue * capex_pct
        delta_nwc = revenue * nwc_pct
        fcff = nopat + da - capex - delta_nwc
        rows.append({
            "Year": i,
            "Revenue": revenue,
            "EBITDA": ebitda,
            "D&A": da,
            "EBIT": ebit,
            "NOPAT": nopat,
            "CapEx": capex,
            "ΔNWC": delta_nwc,
            "FCFF": fcff,
        })
    return pd.DataFrame(rows)


def terminal_value_perpetuity(fcf_n: float, growth: float, wacc: float) -> float:
    """Compute terminal value using the Gordon Growth / perpetuity method.

    TV = FCF_n * (1 + g) / (WACC - g)

    Args:
        fcf_n: Final forecast year free cash flow.
        growth: Terminal growth rate (decimal).
        wacc: WACC (decimal).

    Returns:
        Terminal value.

    Raises:
        ValueError: If growth >= wacc or wacc <= 0.
    """
    if wacc <= 0:
        raise ValueError("WACC must be positive.")
    if growth >= wacc:
        raise ValueError(
            f"Terminal growth ({growth:.2%}) must be less than WACC ({wacc:.2%})."
        )
    return fcf_n * (1 + growth) / (wacc - growth)


def terminal_value_exit(ebitda_n: float, multiple: float) -> float:
    """Compute terminal value using the exit multiple method.

    TV = EBITDA_n * multiple

    Args:
        ebitda_n: Final forecast year EBITDA.
        multiple: EV/EBITDA exit multiple.

    Returns:
        Terminal value.
    """
    return ebitda_n * multiple


def compute_ev(
    fcfs: List[float],
    wacc: float,
    terminal_value: float,
) -> float:
    """Compute Enterprise Value as sum of discounted FCFs plus discounted TV.

    Args:
        fcfs: List of annual FCFFs (Year 1 … Year n).
        wacc: Discount rate (decimal).
        terminal_value: Terminal value (undiscounted).

    Returns:
        Enterprise Value.
    """
    n = len(fcfs)
    pv_fcfs = sum(cf / (1 + wacc) ** t for t, cf in enumerate(fcfs, start=1))
    pv_tv = terminal_value / (1 + wacc) ** n
    return pv_fcfs + pv_tv


def compute_equity_value(ev: float, net_debt: float) -> float:
    """Compute equity value from enterprise value.

    Args:
        ev: Enterprise value.
        net_debt: Net debt (debt minus cash); can be negative for net-cash companies.

    Returns:
        Equity value.
    """
    return ev - net_debt


def compute_implied_price(equity_value: float, shares: float) -> float:
    """Compute implied share price from equity value.

    Args:
        equity_value: Total equity value.
        shares: Shares outstanding.

    Returns:
        Implied share price.

    Raises:
        ValueError: If shares <= 0.
    """
    if shares <= 0:
        raise ValueError("Shares outstanding must be greater than zero.")
    return equity_value / shares


# ---------------------------------------------------------------------------
# Sensitivity table
# ---------------------------------------------------------------------------

@dataclass
class DCFInputs:
    """All inputs needed to run a DCF model."""
    base_revenue: float
    growth_rates: List[float]
    ebitda_margin: float
    da_pct: float
    capex_pct: float
    nwc_pct: float
    tax_rate: float
    wacc: float
    terminal_growth: float
    exit_multiple: float
    use_perpetuity: bool
    net_debt: float
    shares: float
    current_price: float


def run_dcf(inputs: DCFInputs) -> dict:
    """Run the full DCF model and return all results.

    Args:
        inputs: DCFInputs dataclass with all parameters.

    Returns:
        Dictionary with keys: df (projections), ev, equity_value, implied_price,
        terminal_value, tv_pct_ev, pv_fcfs.
    """
    df = project_financials(
        inputs.base_revenue,
        inputs.growth_rates,
        inputs.ebitda_margin,
        inputs.da_pct,
        inputs.capex_pct,
        inputs.nwc_pct,
        inputs.tax_rate,
    )

    fcf_n = df["FCFF"].iloc[-1]
    ebitda_n = df["EBITDA"].iloc[-1]

    if inputs.use_perpetuity:
        tv = terminal_value_perpetuity(fcf_n, inputs.terminal_growth, inputs.wacc)
    else:
        tv = terminal_value_exit(ebitda_n, inputs.exit_multiple)

    fcfs = df["FCFF"].tolist()
    ev = compute_ev(fcfs, inputs.wacc, tv)
    n = len(fcfs)
    pv_fcfs = sum(cf / (1 + inputs.wacc) ** t for t, cf in enumerate(fcfs, start=1))
    pv_tv = tv / (1 + inputs.wacc) ** n
    tv_pct_ev = pv_tv / ev if ev != 0 else 0.0

    equity_value = compute_equity_value(ev, inputs.net_debt)
    implied_price = compute_implied_price(equity_value, inputs.shares)

    return {
        "df": df,
        "ev": ev,
        "pv_fcfs": pv_fcfs,
        "pv_tv": pv_tv,
        "terminal_value": tv,
        "tv_pct_ev": tv_pct_ev,
        "equity_value": equity_value,
        "implied_price": implied_price,
    }


def sensitivity_table(
    inputs: DCFInputs,
    wacc_values: List[float],
    tg_values: List[float],
) -> pd.DataFrame:
    """Build a 2D sensitivity table of implied share price vs WACC and terminal growth.

    Args:
        inputs: Base DCF inputs (will be overridden per cell).
        wacc_values: List of WACC values (columns).
        tg_values: List of terminal growth rates (rows).

    Returns:
        DataFrame indexed by terminal growth, columns are WACC values.
        Values are implied share prices.
    """
    data = {}
    for w in wacc_values:
        col = []
        for g in tg_values:
            try:
                override = DCFInputs(
                    base_revenue=inputs.base_revenue,
                    growth_rates=inputs.growth_rates,
                    ebitda_margin=inputs.ebitda_margin,
                    da_pct=inputs.da_pct,
                    capex_pct=inputs.capex_pct,
                    nwc_pct=inputs.nwc_pct,
                    tax_rate=inputs.tax_rate,
                    wacc=w,
                    terminal_growth=g,
                    exit_multiple=inputs.exit_multiple,
                    use_perpetuity=inputs.use_perpetuity,
                    net_debt=inputs.net_debt,
                    shares=inputs.shares,
                    current_price=inputs.current_price,
                )
                result = run_dcf(override)
                col.append(result["implied_price"])
            except (ValueError, ZeroDivisionError):
                col.append(float("nan"))
        data[w] = col

    df = pd.DataFrame(data, index=tg_values)
    df.index.name = "Terminal Growth"
    df.columns.name = "WACC"
    return df


def sensitivity_table_exit_multiple(
    inputs: DCFInputs,
    wacc_values: List[float],
    multiple_values: List[float],
) -> pd.DataFrame:
    """Build sensitivity table using exit multiple method.

    Args:
        inputs: Base DCF inputs.
        wacc_values: List of WACC values (columns).
        multiple_values: List of EV/EBITDA multiples (rows).

    Returns:
        DataFrame indexed by exit multiple, columns are WACC values.
    """
    data = {}
    for w in wacc_values:
        col = []
        for m in multiple_values:
            try:
                override = DCFInputs(
                    base_revenue=inputs.base_revenue,
                    growth_rates=inputs.growth_rates,
                    ebitda_margin=inputs.ebitda_margin,
                    da_pct=inputs.da_pct,
                    capex_pct=inputs.capex_pct,
                    nwc_pct=inputs.nwc_pct,
                    tax_rate=inputs.tax_rate,
                    wacc=w,
                    terminal_growth=inputs.terminal_growth,
                    exit_multiple=m,
                    use_perpetuity=False,
                    net_debt=inputs.net_debt,
                    shares=inputs.shares,
                    current_price=inputs.current_price,
                )
                result = run_dcf(override)
                col.append(result["implied_price"])
            except (ValueError, ZeroDivisionError):
                col.append(float("nan"))
        data[w] = col

    df = pd.DataFrame(data, index=multiple_values)
    df.index.name = "Exit Multiple"
    df.columns.name = "WACC"
    return df
