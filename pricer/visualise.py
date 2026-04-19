"""
Payoff diagrams and Greek sensitivity plots for European options.

All plots can either be displayed interactively (show=True) or saved to
outputs/plots/ (save=True). Both can be combined.

Functions
---------
plot_payoff          — At-expiry payoff and current BS price vs spot.
plot_greek_vs_spot   — Any single Greek across a range of spot prices.
plot_all_greeks      — 2×3 grid of all five Greeks (+ price) vs spot.
plot_greek_vs_vol    — Any single Greek or price across a range of vols.
plot_vol_surface     — Heatmap of call price across spot × vol grid.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from .black_scholes import black_scholes_price, black_scholes_greeks

# Default output directory for saved figures (relative to this file's package root).
_PLOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "plots")

# Colour palette — consistent across all charts.
_COLOUR_CALL = "#2563EB"   # blue
_COLOUR_PUT  = "#DC2626"   # red
_COLOUR_PAYOFF = "#6B7280" # grey for the at-expiry payoff line

_GREEK_LABELS = {
    "delta": "Delta",
    "gamma": "Gamma",
    "vega":  "Vega (per 1% vol)",
    "theta": "Theta (per day)",
    "rho":   "Rho (per 1% rate)",
    "price": "Option Price ($)",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_plots_dir() -> str:
    os.makedirs(_PLOTS_DIR, exist_ok=True)
    return _PLOTS_DIR


def _finalise(fig: plt.Figure, filename: str | None,
              show: bool, save: bool) -> None:
    """Apply tight layout, optionally save and/or display the figure."""
    fig.tight_layout()
    if save and filename:
        path = os.path.join(_ensure_plots_dir(), filename)
        fig.savefig(path, dpi=150, bbox_inches="tight")
    if show:
        plt.show()
    plt.close(fig)


def _spot_range(spot: float, width: float = 0.40) -> np.ndarray:
    """Return 200 evenly spaced spot prices spanning ±width around spot."""
    low  = spot * (1 - width)
    high = spot * (1 + width)
    return np.linspace(low, high, 200)


# ---------------------------------------------------------------------------
# Public plotting functions
# ---------------------------------------------------------------------------

def plot_payoff(spot: float, strike: float, vol: float,
                rate: float, time_to_expiry: float,
                option_type: str,
                show: bool = True, save: bool = False) -> None:
    """
    Plot the at-expiry payoff alongside the current Black-Scholes price curve.

    The payoff diagram shows two lines:
      - At expiry (solid): max(S - K, 0) for calls, max(K - S, 0) for puts.
        This is the option's intrinsic value at expiration.
      - Today's BS price (dashed): the model price discounting time value.

    Parameters
    ----------
    spot, strike, vol, rate, time_to_expiry : Standard BS inputs.
    option_type : 'call' or 'put'.
    show        : Display the plot interactively.
    save        : Save to outputs/plots/payoff_{option_type}.png.
    """
    spots = _spot_range(spot, width=0.50)

    # At-expiry payoff (intrinsic value only, no time value).
    if option_type == "call":
        payoff = np.maximum(spots - strike, 0)
    else:
        payoff = np.maximum(strike - spots, 0)

    # Current BS price across the same spot range.
    bs_prices = np.array([
        black_scholes_price(s, strike, vol, rate, time_to_expiry, option_type)
        for s in spots
    ])

    colour = _COLOUR_CALL if option_type == "call" else _COLOUR_PUT
    label  = option_type.capitalize()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(spots, payoff,    color=_COLOUR_PAYOFF, linewidth=1.5,
            linestyle="--",   label="Payoff at expiry")
    ax.plot(spots, bs_prices, color=colour,         linewidth=2.0,
            label=f"BS price today (T={time_to_expiry}y)")

    ax.axvline(strike, color="black", linewidth=0.8, linestyle=":", alpha=0.6)
    ax.axvline(spot,   color=colour,  linewidth=0.8, linestyle=":", alpha=0.6)
    ax.text(strike, ax.get_ylim()[1] * 0.02, " K", fontsize=9, color="black")
    ax.text(spot,   ax.get_ylim()[1] * 0.02, " S", fontsize=9, color=colour)

    ax.set_xlabel("Spot price ($)")
    ax.set_ylabel("Option value ($)")
    ax.set_title(f"European {label} — Payoff vs Current Price\n"
                 f"K={strike}, σ={vol:.0%}, r={rate:.1%}, T={time_to_expiry}y")
    ax.legend()
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))

    _finalise(fig, f"payoff_{option_type}.png", show, save)


def plot_greek_vs_spot(spot: float, strike: float, vol: float,
                       rate: float, time_to_expiry: float,
                       greek: str,
                       show: bool = True, save: bool = False) -> None:
    """
    Plot a single Greek (or 'price') against a range of spot prices for both
    call and put.

    Parameters
    ----------
    greek : One of 'delta', 'gamma', 'vega', 'theta', 'rho', or 'price'.
    show, save : Display / save the chart.
    """
    valid = set(_GREEK_LABELS.keys())
    if greek not in valid:
        raise ValueError(f"greek must be one of {sorted(valid)}, got '{greek}'")

    spots = _spot_range(spot)

    def values(option_type: str) -> np.ndarray:
        out = []
        for s in spots:
            if greek == "price":
                out.append(black_scholes_price(s, strike, vol, rate,
                                               time_to_expiry, option_type))
            else:
                out.append(black_scholes_greeks(s, strike, vol, rate,
                                                time_to_expiry, option_type)[greek])
        return np.array(out)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(spots, values("call"), color=_COLOUR_CALL, linewidth=2, label="Call")
    ax.plot(spots, values("put"),  color=_COLOUR_PUT,  linewidth=2, label="Put")

    ax.axvline(strike, color="black", linewidth=0.8, linestyle=":", alpha=0.6,
               label=f"Strike ({strike})")
    ax.axvline(spot,   color="grey",  linewidth=0.8, linestyle=":", alpha=0.6,
               label=f"Spot ({spot})")
    ax.axhline(0, color="black", linewidth=0.5, alpha=0.3)

    ax.set_xlabel("Spot price ($)")
    ax.set_ylabel(_GREEK_LABELS[greek])
    ax.set_title(f"{_GREEK_LABELS[greek]} vs Spot\n"
                 f"K={strike}, σ={vol:.0%}, r={rate:.1%}, T={time_to_expiry}y")
    ax.legend()

    _finalise(fig, f"{greek}_vs_spot.png", show, save)


def plot_all_greeks(spot: float, strike: float, vol: float,
                    rate: float, time_to_expiry: float,
                    option_type: str,
                    show: bool = True, save: bool = False) -> None:
    """
    2×3 grid showing price + all five Greeks vs spot for a single option type.

    Layout:
      [Price]  [Delta]  [Gamma]
      [Vega]   [Theta]  [Rho]

    Parameters
    ----------
    option_type : 'call' or 'put'.
    show, save  : Display / save the chart.
    """
    metrics = ["price", "delta", "gamma", "vega", "theta", "rho"]
    spots = _spot_range(spot)
    colour = _COLOUR_CALL if option_type == "call" else _COLOUR_PUT

    def series(metric: str) -> np.ndarray:
        out = []
        for s in spots:
            if metric == "price":
                out.append(black_scholes_price(s, strike, vol, rate,
                                               time_to_expiry, option_type))
            else:
                out.append(black_scholes_greeks(s, strike, vol, rate,
                                                time_to_expiry, option_type)[metric])
        return np.array(out)

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    fig.suptitle(
        f"European {option_type.capitalize()} — Price & Greeks vs Spot\n"
        f"K={strike}, σ={vol:.0%}, r={rate:.1%}, T={time_to_expiry}y",
        fontsize=13
    )

    for ax, metric in zip(axes.flat, metrics):
        ax.plot(spots, series(metric), color=colour, linewidth=1.8)
        ax.axvline(strike, color="black", linewidth=0.7, linestyle=":", alpha=0.5)
        ax.axvline(spot,   color="grey",  linewidth=0.7, linestyle=":", alpha=0.5)
        ax.axhline(0,      color="black", linewidth=0.4, alpha=0.3)
        ax.set_title(_GREEK_LABELS[metric], fontsize=10)
        ax.set_xlabel("Spot ($)", fontsize=8)
        ax.tick_params(labelsize=8)

    _finalise(fig, f"all_greeks_{option_type}.png", show, save)


def plot_greek_vs_vol(spot: float, strike: float,
                      rate: float, time_to_expiry: float,
                      greek: str,
                      vol_range: tuple[float, float] = (0.05, 0.80),
                      show: bool = True, save: bool = False) -> None:
    """
    Plot a single Greek (or 'price') against a range of implied volatilities
    for both call and put.

    Useful for visualising how an option's sensitivity changes as the market's
    volatility estimate moves — particularly relevant for vega and theta.

    Parameters
    ----------
    greek     : One of 'delta', 'gamma', 'vega', 'theta', 'rho', or 'price'.
    vol_range : (low_vol, high_vol) as decimals, default (0.05, 0.80).
    show, save : Display / save the chart.
    """
    valid = set(_GREEK_LABELS.keys())
    if greek not in valid:
        raise ValueError(f"greek must be one of {sorted(valid)}, got '{greek}'")

    vols = np.linspace(vol_range[0], vol_range[1], 200)

    def values(option_type: str) -> np.ndarray:
        out = []
        for v in vols:
            if greek == "price":
                out.append(black_scholes_price(spot, strike, v, rate,
                                               time_to_expiry, option_type))
            else:
                out.append(black_scholes_greeks(spot, strike, v, rate,
                                                time_to_expiry, option_type)[greek])
        return np.array(out)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(vols * 100, values("call"), color=_COLOUR_CALL, linewidth=2, label="Call")
    ax.plot(vols * 100, values("put"),  color=_COLOUR_PUT,  linewidth=2, label="Put")
    ax.axhline(0, color="black", linewidth=0.5, alpha=0.3)

    ax.set_xlabel("Implied volatility (%)")
    ax.set_ylabel(_GREEK_LABELS[greek])
    ax.set_title(f"{_GREEK_LABELS[greek]} vs Implied Volatility\n"
                 f"S={spot}, K={strike}, r={rate:.1%}, T={time_to_expiry}y")
    ax.legend()

    _finalise(fig, f"{greek}_vs_vol.png", show, save)


def plot_vol_surface(strike: float, rate: float, time_to_expiry: float,
                     spot_range: tuple[float, float] = (70.0, 130.0),
                     vol_range:  tuple[float, float] = (0.05, 0.80),
                     option_type: str = "call",
                     show: bool = True, save: bool = False) -> None:
    """
    Heatmap of option price across a spot × implied-vol grid.

    Illustrates how the option price surface varies with both underlying
    price and volatility assumption simultaneously.

    Parameters
    ----------
    spot_range  : (min_spot, max_spot) for the x-axis grid.
    vol_range   : (min_vol, max_vol) for the y-axis grid (decimals).
    option_type : 'call' or 'put'.
    show, save  : Display / save the chart.
    """
    spots = np.linspace(spot_range[0], spot_range[1], 60)
    vols  = np.linspace(vol_range[0],  vol_range[1],  60)

    # Build price grid: rows = vol, columns = spot.
    price_grid = np.array([
        [black_scholes_price(s, strike, v, rate, time_to_expiry, option_type)
         for s in spots]
        for v in vols
    ])

    fig, ax = plt.subplots(figsize=(9, 6))
    mesh = ax.pcolormesh(spots, vols * 100, price_grid,
                         cmap="RdYlGn", shading="auto")
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_label("Option price ($)", fontsize=10)

    ax.axvline(strike, color="white", linewidth=1.2, linestyle="--",
               alpha=0.8, label=f"Strike ({strike})")
    ax.legend(fontsize=9)

    ax.set_xlabel("Spot price ($)")
    ax.set_ylabel("Implied volatility (%)")
    ax.set_title(f"European {option_type.capitalize()} Price Surface\n"
                 f"K={strike}, r={rate:.1%}, T={time_to_expiry}y")

    _finalise(fig, f"vol_surface_{option_type}.png", show, save)
