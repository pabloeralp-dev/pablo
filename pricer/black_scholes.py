"""
Black-Scholes pricing model for European options.

Model assumptions (articulate these in any derivatives interview):
  1. Lognormal returns — asset prices follow geometric Brownian motion.
  2. Constant volatility — vol is fixed over the option's life. In practice,
     implied vol varies by strike (vol smile) and expiry (term structure).
  3. Constant risk-free rate — no term structure of interest rates.
  4. No dividends — underlying pays no cash flows. See Merton (1973) extension
     note in _compute_d1_d2 for how to relax this assumption.
  5. Frictionless markets — no transaction costs, taxes, or bid-ask spread.
  6. Continuous trading — delta hedge can be rebalanced at any instant.

Where the model breaks down:
  - Constant vol fails immediately: real implied vol has a smile and skew.
  - Lognormal returns underestimate fat-tail probabilities; BS underprices
    deep OTM options.
  - Discrete hedging introduces slippage and realised gamma P&L.
"""

import math
from scipy.stats import norm

# Calendar days in a year — used to convert annual theta to daily decay.
# We use 365 (not 252 trading days) because options expire on calendar time.
CALENDAR_DAYS_PER_YEAR = 365

# Basis-point scaling for vega and rho: we express both Greeks per 1% move
# (vol 0.20 → 0.21, rate 0.05 → 0.06), so divide the raw formula by 100.
ONE_PERCENT = 100


def _validate_inputs(spot: float, strike: float, vol: float,
                     rate: float, time_to_expiry: float) -> None:
    """Raise ValueError with a clear message for any financially invalid input."""
    if spot <= 0:
        raise ValueError(f"spot must be positive, got {spot}")
    if strike <= 0:
        raise ValueError(f"strike must be positive, got {strike}")
    if vol <= 0:
        raise ValueError(f"vol must be positive, got {vol}")
    if time_to_expiry <= 0:
        raise ValueError(f"time_to_expiry must be positive, got {time_to_expiry}")
    # rate can be zero or negative (negative rates exist), so no lower-bound check.


def _compute_d1_d2(spot: float, strike: float, vol: float,
                   rate: float, time_to_expiry: float) -> tuple[float, float]:
    """
    Compute the d1 and d2 intermediate quantities used throughout Black-Scholes.

    d1 = [ln(S/K) + (r + 0.5 × σ²) × T] / (σ × √T)
    d2 = d1 − σ × √T

    These appear in both the price and every Greek. N(d1) is the delta of a
    call; N(d2) is the risk-neutral probability that the call expires in-the-money.
    """
    S = spot      # noqa: N806  (single-letter names kept only inside formulas)
    K = strike    # noqa: N806
    sigma = vol
    r = rate
    T = time_to_expiry  # noqa: N806

    sqrt_T = math.sqrt(T)

    # To extend for continuous dividend yield q, replace S with S * exp(-q * T) here.
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T

    return d1, d2


def black_scholes_price(spot: float, strike: float, vol: float,
                        rate: float, time_to_expiry: float,
                        option_type: str) -> float:
    """
    Price a European call or put option using the Black-Scholes formula.

    Parameters
    ----------
    spot           : Current price of the underlying asset (e.g. 100.0).
    strike         : Option strike price (e.g. 100.0).
    vol            : Annualised implied volatility as a decimal (e.g. 0.20 = 20%).
    rate           : Continuously compounded risk-free rate as a decimal (e.g. 0.05 = 5%).
    time_to_expiry : Time until expiry expressed in years (e.g. 0.25 = 3 months).
    option_type    : 'call' or 'put'.

    Returns
    -------
    float : Theoretical option price. Always non-negative.

    Notes
    -----
    Prices European options only. No dividends (see module docstring for extension).
    """
    if option_type not in ("call", "put"):
        raise ValueError(f"option_type must be 'call' or 'put', got '{option_type}'")

    _validate_inputs(spot, strike, vol, rate, time_to_expiry)

    S, K, sigma, r, T = spot, strike, vol, rate, time_to_expiry
    d1, d2 = _compute_d1_d2(S, K, sigma, r, T)
    discount = math.exp(-r * T)

    if option_type == "call":
        price = S * norm.cdf(d1) - K * discount * norm.cdf(d2)
    else:  # put
        price = K * discount * norm.cdf(-d2) - S * norm.cdf(-d1)

    return price


def black_scholes_greeks(spot: float, strike: float, vol: float,
                         rate: float, time_to_expiry: float,
                         option_type: str) -> dict[str, float]:
    """
    Compute the five main Black-Scholes Greeks for a European option.

    Parameters
    ----------
    spot           : Current price of the underlying asset.
    strike         : Option strike price.
    vol            : Annualised implied volatility as a decimal (e.g. 0.20 = 20%).
    rate           : Continuously compounded risk-free rate as a decimal.
    time_to_expiry : Time until expiry in years.
    option_type    : 'call' or 'put'.

    Returns
    -------
    dict with keys: delta, gamma, vega, theta, rho.

    Greek conventions (strictly enforced — see CLAUDE.md):
      delta : Change in option price per $1 move in spot.
              Positive for calls (0 to 1), negative for puts (-1 to 0).
      gamma : Change in delta per $1 move in spot.
              Always positive for long options (call or put).
      vega  : Change in option price per 1% move in implied vol
              (e.g. vol goes from 0.20 to 0.21). Raw formula divided by 100.
      theta : Change in option price per one calendar day passing.
              Negative for long options (time decay works against the holder).
              Raw annual theta divided by 365. Sign is NOT flipped.
      rho   : Change in option price per 1% move in the risk-free rate
              (e.g. rate goes from 0.05 to 0.06). Raw formula divided by 100.
    """
    if option_type not in ("call", "put"):
        raise ValueError(f"option_type must be 'call' or 'put', got '{option_type}'")

    _validate_inputs(spot, strike, vol, rate, time_to_expiry)

    S, K, sigma, r, T = spot, strike, vol, rate, time_to_expiry
    d1, d2 = _compute_d1_d2(S, K, sigma, r, T)
    sqrt_T = math.sqrt(T)
    discount = math.exp(-r * T)

    # --- Delta ---
    # Sensitivity of option price to a $1 move in the underlying.
    if option_type == "call":
        delta = norm.cdf(d1)
    else:
        delta = norm.cdf(d1) - 1  # equivalent to -N(-d1)

    # --- Gamma ---
    # Rate of change of delta with respect to spot. Identical for calls and puts.
    # Always positive for a long option position.
    gamma = norm.pdf(d1) / (S * sigma * sqrt_T)

    # --- Vega ---
    # Raw BS vega = S × N'(d1) × √T, which gives sensitivity per 1-point vol move.
    # We divide by 100 to express per 1% move in vol (market convention).
    raw_vega = S * norm.pdf(d1) * sqrt_T
    vega = raw_vega / ONE_PERCENT  # vega expressed per 1% change in vol (market convention)

    # --- Theta ---
    # Annual rate of option price decay due to passing time.
    # We divide by 365 to express as daily decay (calendar-day convention).
    # The result is negative for long options — do NOT flip the sign.
    raw_annual_theta_term1 = -(S * norm.pdf(d1) * sigma) / (2 * sqrt_T)
    if option_type == "call":
        raw_annual_theta = raw_annual_theta_term1 - r * K * discount * norm.cdf(d2)
    else:
        raw_annual_theta = raw_annual_theta_term1 + r * K * discount * norm.cdf(-d2)

    theta = raw_annual_theta / CALENDAR_DAYS_PER_YEAR  # daily theta, negative for longs

    # --- Rho ---
    # Raw BS rho gives sensitivity per 1-point move in rate.
    # We divide by 100 to express per 1% move in rate (market convention).
    if option_type == "call":
        raw_rho = K * T * discount * norm.cdf(d2)
    else:
        raw_rho = -K * T * discount * norm.cdf(-d2)

    rho = raw_rho / ONE_PERCENT  # rho expressed per 1% change in rate (market convention)

    return {
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta,
        "rho": rho,
    }
