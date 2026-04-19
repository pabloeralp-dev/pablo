"""
Entry point for the Black-Scholes option pricer.

Usage
-----
Run with defaults (ATM 1-year call):
    python main.py

Override any input via flags:
    python main.py --spot 105 --strike 100 --vol 0.25 --rate 0.03 \
                   --time 0.5 --type put

Save plots:
    python main.py --save-plots

Skip plots entirely:
    python main.py --no-plots

Output
------
Pricing results are always written to outputs/results.json.
Plots are saved to outputs/plots/ when --save-plots is passed.
"""

import argparse
import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")  # non-interactive backend; overridden below if --show-plots

from pricer.black_scholes import black_scholes_price, black_scholes_greeks
from pricer.visualise import (
    plot_payoff,
    plot_greek_vs_spot,
    plot_all_greeks,
    plot_greek_vs_vol,
    plot_vol_surface,
)

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")
RESULTS_PATH = os.path.join(OUTPUTS_DIR, "results.json")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Black-Scholes European option pricer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--spot",       type=float, default=100.0,
                   help="Current underlying price")
    p.add_argument("--strike",     type=float, default=100.0,
                   help="Option strike price")
    p.add_argument("--vol",        type=float, default=0.20,
                   help="Annualised implied volatility (decimal, e.g. 0.20 = 20%%)")
    p.add_argument("--rate",       type=float, default=0.05,
                   help="Continuously compounded risk-free rate (decimal)")
    p.add_argument("--time",       type=float, default=1.0,
                   dest="time_to_expiry",
                   help="Time to expiry in years (e.g. 0.25 = 3 months)")
    p.add_argument("--type",       type=str,   default="call",
                   dest="option_type", choices=["call", "put"],
                   help="Option type")
    p.add_argument("--save-plots", action="store_true",
                   help="Save all plots to outputs/plots/")
    p.add_argument("--show-plots", action="store_true",
                   help="Display plots interactively (requires a display)")
    p.add_argument("--no-plots",   action="store_true",
                   help="Skip all plotting")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Core pricing logic
# ---------------------------------------------------------------------------

def _intrinsic_value(spot: float, strike: float, option_type: str) -> float:
    if option_type == "call":
        return max(spot - strike, 0.0)
    return max(strike - spot, 0.0)


def run_pricer(spot: float, strike: float, vol: float, rate: float,
               time_to_expiry: float, option_type: str) -> dict:
    """
    Price a European option and compute all Greeks. Return a structured dict
    matching the outputs/results.json schema from CLAUDE.md.
    """
    price    = black_scholes_price(spot, strike, vol, rate, time_to_expiry, option_type)
    greeks   = black_scholes_greeks(spot, strike, vol, rate, time_to_expiry, option_type)
    intrinsic = _intrinsic_value(spot, strike, option_type)
    time_val  = price - intrinsic

    return {
        "inputs": {
            "spot":           spot,
            "strike":         strike,
            "vol":            vol,
            "rate":           rate,
            "time_to_expiry": time_to_expiry,
            "option_type":    option_type,
        },
        "pricing": {
            "price":           round(price,     4),
            "intrinsic_value": round(intrinsic,  4),
            "time_value":      round(time_val,   4),
        },
        "greeks": {k: round(v, 6) for k, v in greeks.items()},
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _save_json(result: dict) -> None:
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(result, f, indent=2)


def _print_results(result: dict) -> None:
    inp = result["inputs"]
    pri = result["pricing"]
    grk = result["greeks"]

    print()
    print("=" * 52)
    print(f"  European {inp['option_type'].upper()}  --  Black-Scholes Pricer")
    print("=" * 52)
    print(f"  Spot:            {inp['spot']:>10.4f}")
    print(f"  Strike:          {inp['strike']:>10.4f}")
    print(f"  Vol:             {inp['vol']:>10.1%}")
    print(f"  Rate:            {inp['rate']:>10.1%}")
    print(f"  Time to expiry:  {inp['time_to_expiry']:>9.4f}y")
    print("-" * 52)
    print(f"  Price:           {pri['price']:>10.4f}")
    print(f"  Intrinsic value: {pri['intrinsic_value']:>10.4f}")
    print(f"  Time value:      {pri['time_value']:>10.4f}")
    print("-" * 52)
    print(f"  Delta:           {grk['delta']:>10.4f}")
    print(f"  Gamma:           {grk['gamma']:>10.4f}")
    print(f"  Vega  (per 1%):  {grk['vega']:>10.4f}")
    print(f"  Theta (per day): {grk['theta']:>10.4f}")
    print(f"  Rho   (per 1%):  {grk['rho']:>10.4f}")
    print("=" * 52)
    print(f"  Results saved -> {RESULTS_PATH}")
    print()


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _run_plots(spot: float, strike: float, vol: float, rate: float,
               time_to_expiry: float, option_type: str,
               show: bool, save: bool) -> None:
    kwargs = dict(show=show, save=save)

    plot_payoff(spot, strike, vol, rate, time_to_expiry, option_type, **kwargs)
    plot_all_greeks(spot, strike, vol, rate, time_to_expiry, option_type, **kwargs)

    for greek in ["delta", "gamma", "vega", "theta", "rho"]:
        plot_greek_vs_spot(spot, strike, vol, rate, time_to_expiry, greek, **kwargs)

    plot_greek_vs_vol(spot, strike, rate, time_to_expiry, greek="vega",  **kwargs)
    plot_greek_vs_vol(spot, strike, rate, time_to_expiry, greek="price", **kwargs)

    plot_vol_surface(strike, rate, time_to_expiry, option_type=option_type, **kwargs)

    if save:
        print(f"  Plots saved  -> outputs/plots/")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()

    result = run_pricer(
        spot=args.spot,
        strike=args.strike,
        vol=args.vol,
        rate=args.rate,
        time_to_expiry=args.time_to_expiry,
        option_type=args.option_type,
    )

    _save_json(result)
    _print_results(result)

    if not args.no_plots:
        if args.show_plots:
            matplotlib.use("TkAgg")   # switch to interactive backend
        _run_plots(
            spot=args.spot,
            strike=args.strike,
            vol=args.vol,
            rate=args.rate,
            time_to_expiry=args.time_to_expiry,
            option_type=args.option_type,
            show=args.show_plots,
            save=args.save_plots,
        )


if __name__ == "__main__":
    main()
