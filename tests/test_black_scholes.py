"""
Unit tests for the Black-Scholes pricer.

All reference values come from external benchmarks, not internal consistency.
Tolerances are set to 4 decimal places (0.0001) for prices and Greeks, which
is tighter than any interview or practical use case demands.
"""

import math
import pytest
from pricer.black_scholes import black_scholes_price, black_scholes_greeks

# ---------------------------------------------------------------------------
# Reference benchmark (from CLAUDE.md)
# Inputs: spot=100, strike=100, vol=0.20, rate=0.05, time_to_expiry=1.0
# ---------------------------------------------------------------------------

REF = dict(spot=100.0, strike=100.0, vol=0.20, rate=0.05, time_to_expiry=1.0)
TOLERANCE = 1e-4  # absolute tolerance for all assertions


class TestReferenceBenchmark:
    """Validate against the hardcoded reference values from CLAUDE.md."""

    def test_call_price(self):
        price = black_scholes_price(**REF, option_type="call")
        assert abs(price - 10.4506) < TOLERANCE, f"Call price {price:.4f} != 10.4506"

    def test_put_price(self):
        price = black_scholes_price(**REF, option_type="put")
        assert abs(price - 5.5735) < TOLERANCE, f"Put price {price:.4f} != 5.5735"

    def test_put_call_parity(self):
        """C - P must equal S - K × e^{-r×T} (no-arbitrage identity)."""
        call = black_scholes_price(**REF, option_type="call")
        put = black_scholes_price(**REF, option_type="put")
        forward_pv = REF["spot"] - REF["strike"] * math.exp(-REF["rate"] * REF["time_to_expiry"])
        assert abs((call - put) - forward_pv) < TOLERANCE

    def test_call_delta(self):
        greeks = black_scholes_greeks(**REF, option_type="call")
        assert abs(greeks["delta"] - 0.6368) < TOLERANCE

    def test_put_delta(self):
        greeks = black_scholes_greeks(**REF, option_type="put")
        assert abs(greeks["delta"] - (-0.3632)) < TOLERANCE

    def test_gamma(self):
        greeks = black_scholes_greeks(**REF, option_type="call")
        assert abs(greeks["gamma"] - 0.0187) < TOLERANCE

    def test_vega_per_one_percent(self):
        """Vega is expressed per 1% move in vol, so raw vega / 100."""
        greeks = black_scholes_greeks(**REF, option_type="call")
        assert abs(greeks["vega"] - 0.3752) < TOLERANCE

    def test_theta_call_per_day(self):
        """Theta is daily (÷365) and negative for a long option."""
        greeks = black_scholes_greeks(**REF, option_type="call")
        assert greeks["theta"] < 0, "Theta must be negative for a long call"
        assert abs(greeks["theta"] - (-0.0176)) < TOLERANCE

    def test_rho_call_per_one_percent(self):
        """Rho is expressed per 1% move in the risk-free rate."""
        greeks = black_scholes_greeks(**REF, option_type="call")
        assert abs(greeks["rho"] - 0.5323) < TOLERANCE


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_atm_call_delta_near_half(self):
        """ATM call delta is above 0.5 due to log-normal skew (N(d1) > 0.5 when vol>0)."""
        greeks = black_scholes_greeks(
            spot=100, strike=100, vol=0.20, rate=0.0, time_to_expiry=1.0,
            option_type="call"
        )
        assert 0.50 < greeks["delta"] < 0.60

    def test_deep_itm_call_delta_near_one(self):
        greeks = black_scholes_greeks(
            spot=200, strike=100, vol=0.20, rate=0.05, time_to_expiry=1.0,
            option_type="call"
        )
        assert greeks["delta"] > 0.99

    def test_deep_itm_put_delta_near_minus_one(self):
        greeks = black_scholes_greeks(
            spot=50, strike=100, vol=0.20, rate=0.05, time_to_expiry=1.0,
            option_type="put"
        )
        assert greeks["delta"] < -0.99

    def test_deep_otm_price_near_zero(self):
        price = black_scholes_price(
            spot=50, strike=200, vol=0.20, rate=0.05, time_to_expiry=1.0,
            option_type="call"
        )
        assert price < 0.01

    def test_deep_otm_delta_near_zero(self):
        greeks = black_scholes_greeks(
            spot=50, strike=200, vol=0.20, rate=0.05, time_to_expiry=1.0,
            option_type="call"
        )
        assert greeks["delta"] < 0.01

    def test_short_expiry_itm_price_near_intrinsic(self):
        """Deep ITM, very short expiry: price ≈ intrinsic value."""
        spot, strike = 110.0, 100.0
        price = black_scholes_price(
            spot=spot, strike=strike, vol=0.20, rate=0.05, time_to_expiry=0.01,
            option_type="call"
        )
        intrinsic = spot - strike
        assert abs(price - intrinsic) < 0.15  # small time value only

    def test_long_expiry_greeks_bounded(self):
        greeks = black_scholes_greeks(
            spot=100, strike=100, vol=0.20, rate=0.05, time_to_expiry=5.0,
            option_type="call"
        )
        assert 0 < greeks["delta"] <= 1
        assert greeks["gamma"] > 0
        assert greeks["vega"] > 0
        assert greeks["theta"] < 0

    def test_put_call_parity_various_strikes(self):
        params = dict(vol=0.25, rate=0.03, time_to_expiry=0.5)
        for spot, strike in [(80, 100), (100, 100), (120, 100)]:
            call = black_scholes_price(spot=spot, strike=strike, option_type="call", **params)
            put = black_scholes_price(spot=spot, strike=strike, option_type="put", **params)
            forward_pv = spot - strike * math.exp(-params["rate"] * params["time_to_expiry"])
            assert abs((call - put) - forward_pv) < TOLERANCE, (
                f"Put-call parity failed for spot={spot}, strike={strike}"
            )

    def test_gamma_identical_for_call_and_put(self):
        """Gamma is the same for calls and puts at the same inputs."""
        call_g = black_scholes_greeks(**REF, option_type="call")["gamma"]
        put_g = black_scholes_greeks(**REF, option_type="put")["gamma"]
        assert abs(call_g - put_g) < 1e-10

    def test_vega_identical_for_call_and_put(self):
        """Vega is the same for calls and puts at the same inputs."""
        call_v = black_scholes_greeks(**REF, option_type="call")["vega"]
        put_v = black_scholes_greeks(**REF, option_type="put")["vega"]
        assert abs(call_v - put_v) < 1e-10


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_negative_vol_raises(self):
        with pytest.raises(ValueError, match="vol"):
            black_scholes_price(spot=100, strike=100, vol=-0.1,
                                rate=0.05, time_to_expiry=1.0, option_type="call")

    def test_zero_spot_raises(self):
        with pytest.raises(ValueError, match="spot"):
            black_scholes_price(spot=0, strike=100, vol=0.2,
                                rate=0.05, time_to_expiry=1.0, option_type="call")

    def test_invalid_option_type_raises(self):
        with pytest.raises(ValueError, match="option_type"):
            black_scholes_price(spot=100, strike=100, vol=0.2,
                                rate=0.05, time_to_expiry=1.0, option_type="binary")

    def test_zero_expiry_raises(self):
        with pytest.raises(ValueError, match="time_to_expiry"):
            black_scholes_price(spot=100, strike=100, vol=0.2,
                                rate=0.05, time_to_expiry=0.0, option_type="call")
