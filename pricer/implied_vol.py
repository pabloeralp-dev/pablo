"""
Implied volatility solver for European options.

Given a market-observed option price, backs out the implied volatility (IV)
that makes the Black-Scholes model price equal to that market price.

Method: Brent's root-finding algorithm (scipy.optimize.brentq).
  - Brent's method combines bisection, secant, and inverse quadratic
    interpolation. It is guaranteed to converge if a root is bracketed
    and does not require derivatives (unlike Newton-Raphson).
  - Bounds: [1e-6, 10.0] — from near-zero vol to 1000% annualised.
    Prices outside this vol range are practically unobservable.

Raises IVSolverError (a subclass of ValueError) when:
  - The market price violates no-arbitrage bounds (below intrinsic or
    above the no-dividend upper bound).
  - No vol in [1e-6, 10.0] reproduces the market price (sign does not
    change across the bracket — Brent's precondition is not met).
"""

from scipy.optimize import brentq

from .black_scholes import black_scholes_price, _validate_inputs

# Brent's method search bounds for annualised volatility (decimal).
VOL_LOWER_BOUND = 1e-6   # effectively zero — avoids log(0) in d1/d2
VOL_UPPER_BOUND = 10.0   # 1000% annualised vol — no liquid option exceeds this

# brentq convergence tolerance on the function value (price difference in $).
PRICE_TOLERANCE = 1e-8

# Maximum iterations for Brent's method (default scipy value is 100; kept explicit).
MAX_ITERATIONS = 500


class IVSolverError(ValueError):
    """Raised when implied vol cannot be found for the given market price."""


def implied_vol(market_price: float, spot: float, strike: float,
                rate: float, time_to_expiry: float,
                option_type: str) -> float:
    """
    Compute the implied volatility of a European option from its market price.

    Uses Brent's root-finding method (scipy.optimize.brentq) to find the vol σ
    such that BS_price(σ) = market_price. The search is over [1e-6, 10.0].

    Parameters
    ----------
    market_price   : Observed market price of the option (must be > 0 and
                     respect no-arbitrage bounds).
    spot           : Current price of the underlying asset.
    strike         : Option strike price.
    rate           : Continuously compounded risk-free rate as a decimal.
    time_to_expiry : Time until expiry in years.
    option_type    : 'call' or 'put'.

    Returns
    -------
    float : Implied volatility as an annualised decimal (e.g. 0.20 = 20%).

    Raises
    ------
    IVSolverError : If the market price violates no-arbitrage bounds or if
                    Brent's method cannot bracket a root in [1e-6, 10.0].
    ValueError    : Propagated from _validate_inputs for bad spot/strike/etc.

    Notes
    -----
    Prices European options only. No dividends assumed in the base model.
    """
    if option_type not in ("call", "put"):
        raise ValueError(f"option_type must be 'call' or 'put', got '{option_type}'")

    # vol is not yet known, so we validate the other four inputs directly.
    _validate_inputs(spot, strike, vol=0.01, rate=rate,
                     time_to_expiry=time_to_expiry)

    if market_price <= 0:
        raise IVSolverError(
            f"market_price must be positive, got {market_price}. "
            "An option always has non-negative value."
        )

    _check_no_arbitrage_bounds(market_price, spot, strike, rate,
                               time_to_expiry, option_type)

    def objective(vol: float) -> float:
        """Difference between BS model price and the observed market price."""
        return black_scholes_price(spot, strike, vol, rate,
                                   time_to_expiry, option_type) - market_price

    # Check that a root is bracketed before calling brentq — gives a clear
    # error message rather than a cryptic scipy exception.
    price_at_low_vol = objective(VOL_LOWER_BOUND)
    price_at_high_vol = objective(VOL_UPPER_BOUND)

    if price_at_low_vol * price_at_high_vol > 0:
        raise IVSolverError(
            f"No implied vol found in [{VOL_LOWER_BOUND}, {VOL_UPPER_BOUND}]. "
            f"BS price at vol={VOL_LOWER_BOUND}: {market_price + price_at_low_vol:.4f}, "
            f"at vol={VOL_UPPER_BOUND}: {market_price + price_at_high_vol:.4f}. "
            f"Market price {market_price:.4f} may be outside the model's reachable range."
        )

    result: float = brentq(
        objective,
        VOL_LOWER_BOUND,
        VOL_UPPER_BOUND,
        xtol=PRICE_TOLERANCE,
        maxiter=MAX_ITERATIONS,
        full_output=False,
    )

    return float(result)


def _check_no_arbitrage_bounds(market_price: float, spot: float, strike: float,
                                rate: float, time_to_expiry: float,
                                option_type: str) -> None:
    """
    Raise IVSolverError if market_price violates model-free no-arbitrage bounds.

    For a call  (no dividends): max(S - K×e^{-rT}, 0) ≤ C ≤ S
    For a put   (no dividends): max(K×e^{-rT} - S, 0) ≤ P ≤ K×e^{-rT}

    A price outside these bounds cannot come from any vol in the Black-Scholes
    model — Brent's method would search forever without finding a root.
    """
    import math
    discount = math.exp(-rate * time_to_expiry)

    if option_type == "call":
        lower = max(spot - strike * discount, 0.0)
        upper = spot
    else:
        lower = max(strike * discount - spot, 0.0)
        upper = strike * discount

    if market_price < lower - 1e-6:
        raise IVSolverError(
            f"{option_type} price {market_price:.4f} is below no-arbitrage lower bound "
            f"{lower:.4f} (intrinsic value). IV cannot exist."
        )
    if market_price > upper + 1e-6:
        raise IVSolverError(
            f"{option_type} price {market_price:.4f} exceeds no-arbitrage upper bound "
            f"{upper:.4f}. IV cannot exist."
        )
