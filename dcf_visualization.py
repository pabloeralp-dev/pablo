"""Plotly chart builders for the DCF valuation tool."""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Shared theme constants ──────────────────────────────────────────────────
BACKGROUND = "#0E1117"
PAPER_BG = "#0E1117"
PLOT_BG = "#0E1117"
GRID_COLOR = "#1E2435"
FONT_COLOR = "#E8EAF0"
FONT_FAMILY = "Source Code Pro, Courier New, monospace"
ACCENT_BLUE = "#4A90D9"
GREEN = "#2ECC71"
RED = "#E05555"
MUTED = "#7BB3E8"


def _base_layout(title: str = "", height: int = 420) -> dict:
    return dict(
        title=dict(text=title, font=dict(color=ACCENT_BLUE, size=14, family=FONT_FAMILY)),
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=FONT_COLOR, family=FONT_FAMILY, size=11),
        height=height,
        margin=dict(l=60, r=30, t=50, b=50),
        xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
        yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    )


# ── FCF Waterfall / Bar chart ───────────────────────────────────────────────

def plot_fcff_waterfall(df: pd.DataFrame) -> go.Figure:
    """Plot projected FCFF as a bar chart with the financial waterfall overlay.

    Args:
        df: DataFrame from project_financials() with Year, Revenue, EBITDA,
            D&A, EBIT, NOPAT, CapEx, ΔNWC, FCFF columns.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["Year"].astype(str).apply(lambda y: f"Year {y}"),
        y=df["Revenue"],
        name="Revenue",
        marker_color="#1E4A80",
        opacity=0.7,
    ))
    fig.add_trace(go.Bar(
        x=df["Year"].astype(str).apply(lambda y: f"Year {y}"),
        y=df["EBITDA"],
        name="EBITDA",
        marker_color="#2A6AAD",
        opacity=0.85,
    ))
    fig.add_trace(go.Scatter(
        x=df["Year"].astype(str).apply(lambda y: f"Year {y}"),
        y=df["FCFF"],
        name="FCFF",
        mode="lines+markers",
        line=dict(color=ACCENT_BLUE, width=2),
        marker=dict(size=7, color=ACCENT_BLUE),
    ))

    layout = _base_layout("Projected Financials & Free Cash Flow", height=400)
    layout["barmode"] = "overlay"
    layout["legend"] = dict(
        orientation="h", x=0, y=1.12,
        font=dict(size=10, family=FONT_FAMILY),
        bgcolor="rgba(0,0,0,0)",
    )
    layout["yaxis"]["tickprefix"] = "$"
    layout["yaxis"]["tickformat"] = ",.0f"
    fig.update_layout(**layout)
    return fig


def plot_ev_bridge(pv_fcfs: float, pv_tv: float, net_debt: float) -> go.Figure:
    """Waterfall bridge from PV of FCFs + TV down to equity value.

    Args:
        pv_fcfs: Present value of forecast-period FCFs.
        pv_tv: Present value of terminal value.
        net_debt: Net debt (positive = debt > cash).

    Returns:
        Plotly Figure.
    """
    ev = pv_fcfs + pv_tv
    equity = ev - net_debt

    labels = ["PV of FCFs", "PV of Terminal Value", "Enterprise Value", "Less: Net Debt", "Equity Value"]
    values = [pv_fcfs, pv_tv, 0, -net_debt, 0]
    measures = ["relative", "relative", "total", "relative", "total"]
    colors = [ACCENT_BLUE, MUTED, ACCENT_BLUE, RED if net_debt > 0 else GREEN, GREEN if equity > 0 else RED]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        connector=dict(line=dict(color=GRID_COLOR, width=1)),
        increasing=dict(marker_color=ACCENT_BLUE),
        decreasing=dict(marker_color=RED),
        totals=dict(marker_color=GREEN if equity > 0 else RED),
        text=[f"${v:,.0f}" if v != 0 else f"${ev:,.0f}" if i == 2 else f"${equity:,.0f}"
              for i, v in enumerate(values)],
        textposition="outside",
        textfont=dict(size=9, color=FONT_COLOR, family=FONT_FAMILY),
    ))

    layout = _base_layout("Enterprise Value → Equity Value Bridge", height=380)
    layout["yaxis"]["tickprefix"] = "$"
    layout["yaxis"]["tickformat"] = ",.0f"
    layout["showlegend"] = False
    fig.update_layout(**layout)
    return fig


# ── Sensitivity heatmap ─────────────────────────────────────────────────────

def plot_sensitivity_heatmap(
    table: pd.DataFrame,
    current_price: float,
) -> go.Figure:
    """Plot sensitivity table as a Plotly heatmap.

    Args:
        table: DataFrame with implied prices (rows = tg, cols = wacc).
        current_price: Current share price for colour midpoint.

    Returns:
        Plotly Figure.
    """
    z = table.values
    x_labels = [f"{c:.1%}" for c in table.columns]
    y_labels = [f"{r:.1%}" for r in table.index]

    text = [[f"${v:,.2f}" if not np.isnan(v) else "N/A" for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=x_labels,
        y=y_labels,
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=10, family=FONT_FAMILY),
        colorscale=[
            [0.0, "#3A0A0A"],
            [0.4, "#2E1010"],
            [0.5, "#1A1F2E"],
            [0.6, "#0D2818"],
            [1.0, "#0D3320"],
        ],
        zmid=current_price,
        showscale=True,
        colorbar=dict(
            title=dict(text="Implied Price", font=dict(color=MUTED, size=10)),
            tickfont=dict(color=FONT_COLOR, size=9),
            tickprefix="$",
        ),
    ))

    layout = _base_layout("Sensitivity: Implied Share Price", height=400)
    layout["xaxis"]["title"] = "WACC"
    layout["yaxis"]["title"] = "Terminal Growth Rate"
    fig.update_layout(**layout)
    return fig


# ── Football field ──────────────────────────────────────────────────────────

def plot_football_field(
    ranges: List[dict],
    current_price: float,
) -> go.Figure:
    """Plot a horizontal football field chart.

    Args:
        ranges: List of dicts with keys: label (str), low (float), high (float).
        current_price: Current share price shown as a vertical line.

    Returns:
        Plotly Figure.
    """
    bar_colors = ["#1E4A80", "#2A6AAD", "#1A5C3A", "#4A3A0A", "#3A1A5C"]
    bar_border = ["#4A90D9", "#7BB3E8", "#2ECC71", "#F0C040", "#9B59B6"]

    fig = go.Figure()

    for i, r in enumerate(reversed(ranges)):
        low = r.get("low", 0)
        high = r.get("high", 0)
        width = high - low
        label = r.get("label", f"Method {i+1}")
        color = bar_colors[i % len(bar_colors)]
        border = bar_border[i % len(bar_border)]

        fig.add_trace(go.Bar(
            x=[width],
            y=[label],
            base=[low],
            orientation="h",
            marker=dict(color=color, line=dict(color=border, width=1.5)),
            text=f"${low:,.1f} – ${high:,.1f}",
            textposition="inside",
            textfont=dict(size=9, color=FONT_COLOR, family=FONT_FAMILY),
            showlegend=False,
            hovertemplate=f"<b>{label}</b><br>Low: ${low:,.2f}<br>High: ${high:,.2f}<extra></extra>",
        ))

    # Current price line
    if current_price and current_price > 0:
        fig.add_vline(
            x=current_price,
            line=dict(color=ACCENT_BLUE, width=2, dash="dash"),
            annotation_text=f"Current: ${current_price:,.2f}",
            annotation_font=dict(color=ACCENT_BLUE, size=10, family=FONT_FAMILY),
            annotation_position="top",
        )

    layout = _base_layout("Football Field — Valuation Summary", height=max(300, 80 * len(ranges) + 100))
    layout["barmode"] = "overlay"
    layout["xaxis"]["title"] = "Implied Share Price ($)"
    layout["xaxis"]["tickprefix"] = "$"
    layout["xaxis"]["tickformat"] = ",.0f"
    layout["yaxis"]["title"] = ""
    layout["showlegend"] = False
    fig.update_layout(**layout)
    return fig


# ── Monte Carlo histogram ───────────────────────────────────────────────────

def plot_monte_carlo_histogram(
    prices: np.ndarray,
    p10: float,
    p25: float,
    p50: float,
    p75: float,
    p90: float,
    current_price: float,
    n_bins: int = 80,
) -> go.Figure:
    """Plot Monte Carlo implied price distribution as a histogram.

    Args:
        prices: Array of simulated implied share prices.
        p10/p25/p50/p75/p90: Percentile values.
        current_price: Current share price.
        n_bins: Number of histogram bins.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=prices,
        nbinsx=n_bins,
        marker=dict(
            color=ACCENT_BLUE,
            opacity=0.7,
            line=dict(color=GRID_COLOR, width=0.5),
        ),
        name="Simulated Prices",
        showlegend=False,
    ))

    # Percentile lines
    for val, label, color, dash in [
        (p10, "P10", "#E05555", "dot"),
        (p25, "P25", "#E07722", "dash"),
        (p50, "P50", GREEN, "solid"),
        (p75, "P75", "#E07722", "dash"),
        (p90, "P90", "#E05555", "dot"),
    ]:
        fig.add_vline(
            x=val,
            line=dict(color=color, width=1.5, dash=dash),
            annotation_text=f"{label}: ${val:,.1f}",
            annotation_font=dict(color=color, size=9, family=FONT_FAMILY),
            annotation_position="top",
        )

    # Current price
    if current_price and current_price > 0:
        fig.add_vline(
            x=current_price,
            line=dict(color="#FFFFFF", width=2, dash="longdash"),
            annotation_text=f"Current: ${current_price:,.1f}",
            annotation_font=dict(color="#FFFFFF", size=10, family=FONT_FAMILY),
            annotation_position="top right",
        )

    layout = _base_layout("Monte Carlo — Implied Share Price Distribution", height=420)
    layout["xaxis"]["title"] = "Implied Share Price ($)"
    layout["xaxis"]["tickprefix"] = "$"
    layout["yaxis"]["title"] = "Frequency"
    layout["bargap"] = 0.05
    fig.update_layout(**layout)
    return fig


def plot_terminal_value_comparison(pv_perpetuity: float, pv_exit: float) -> go.Figure:
    """Side-by-side bar comparing PV of terminal value under two methods.

    Args:
        pv_perpetuity: PV of terminal value via perpetuity growth.
        pv_exit: PV of terminal value via exit multiple.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure(go.Bar(
        x=["Perpetuity Growth", "Exit Multiple"],
        y=[pv_perpetuity, pv_exit],
        marker=dict(
            color=[ACCENT_BLUE, MUTED],
            line=dict(color=[ACCENT_BLUE, MUTED], width=1),
        ),
        text=[f"${pv_perpetuity:,.0f}", f"${pv_exit:,.0f}"],
        textposition="outside",
        textfont=dict(size=11, family=FONT_FAMILY, color=FONT_COLOR),
    ))

    layout = _base_layout("Terminal Value Comparison", height=320)
    layout["yaxis"]["tickprefix"] = "$"
    layout["yaxis"]["tickformat"] = ",.0f"
    layout["showlegend"] = False
    fig.update_layout(**layout)
    return fig
