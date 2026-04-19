"""
Tests for the implied volatility solver.

Strategy: use black_scholes_price to generate a known price, then verify
implied_vol recovers the original vol. Also test no-arbitrage guard rails
and edge cases.
"""

import math
import pytest
from pricer.black_scholes import black_scholes_price
from pricer.implied_vol import implied_vol, IVSolverError

TOLERANCE = 1e-4  # vol recovered to 0.01% — consistent with test_black_scholes.py


# ---------------------------------------------------------------------------
# Round-trip: price → IV → price must recover the original vol
# ---------------------------------------------------------------------------

class TestRoundTrip:

    def _round_trip(self, spot, strike, vol, rate, time_to_expiry, option_type):
        price = black_scholes_price(spot, strike, vol, rate, time_to_expiry, option_type)
        recovered_vol = implied_vol(price, spot, strike, rate, time_to_expiry, option_type)
        assert abs(recovered_vol - vol) < TOLERANCE, (
            f"Round-trip failed: input vol={vol}, recovered={recovered_vol:.6f}"
        )

    def test_atm_call(self):
        self._round_trip(100, 100, 0.20, 0.05, 1.0, "call")

    def test_atm_put(self):
        self._round_trip(100, 100, 0.20, 0.05, 1.0, "put")

    def test_otm_call(self):
        self._round_trip(100, 110, 0.25, 0.03, 0.5, "call")

    def test_itm_call(self):
        self._round_trip(110, 100, 0.18, 0.05, 0.25, "call")

    def test_otm_put(self):
        self._round_trip(100, 90, 0.30, 0.02, 1.0, "put")

    def test_itm_put(self):
        self._round_trip(90, 100, 0.22, 0.05, 0.5, "put")

    def test_high_vol(self):
        self._round_trip(100, 100, 0.80, 0.05, 1.0, "call")

    def test_low_vol(self):
        self._round_trip(100, 100, 0.05, 0.05, 1.0, "call")

    def test_short_expiry(self):
        self._round_trip(100, 100, 0.20, 0.05, 0.05, "call")

    def test_long_expiry(self):
        self._round_trip(100, 100, 0.20, 0.05, 3.0, "call")

    def test_zero_rate(self):
        self._round_trip(100, 100, 0.20, 0.0, 1.0, "call")

    def test_negative_rate(self):
        self._round_trip(100, 100, 0.20, -0.01, 1.0, "put")


# ---------------------------------------------------------------------------
# Reference benchmark: recover vol from CLAUDE.md reference prices
# ---------------------------------------------------------------------------

class TestReferenceBenchmark:
    """Verify IV solver against the known benchmark from CLAUDE.md."""

    REF = dict(spot=100.0, strike=100.0, rate=0.05, time_to_expiry=1.0)

    def test_call_iv_from_reference_price(self):
        # Call price 10.4506 should imply vol ≈ 0.20
        iv = implied_vol(market_price=10.4506, option_type="call", **self.REF)
        assert abs(iv - 0.20) < TOLERANCE

    def test_put_iv_from_reference_price(self):
        # Put price 5.5735 should imply vol ≈ 0.20
        iv = implied_vol(market_price=5.5735, option_type="put", **self.REF)
        assert abs(iv - 0.20) < TOLERANCE

    def test_call_and_put_imply_same_vol(self):
        """Put-call parity guarantees calls and puts at the same strike share one IV."""
        iv_call = implied_vol(market_price=10.4506, option_type="call", **self.REF)
        iv_put = implied_vol(market_price=5.5735, option_type="put", **self.REF)
        assert abs(iv_call - iv_put) < TOLERANCE


# ---------------------------------------------------------------------------
# No-arbitrage guard rails
# ---------------------------------------------------------------------------

class TestNoArbitrageBounds:

    def test_price_below_intrinsic_call_raises(self):
        # Deep ITM call: intrinsic = 50, price of 1.0 is below lower bound
        with pytest.raises(IVSolverError, match="lower bound"):
            implied_vol(market_price=1.0, spot=150, strike=100,
                        rate=0.05, time_to_expiry=1.0, option_type="call")

    def test_price_above_spot_call_raises(self):
        # A call can never be worth more than the spot price
        with pytest.raises(IVSolverError, match="upper bound"):
            implied_vol(market_price=110.0, spot=100, strike=100,
                        rate=0.05, time_to_expiry=1.0, option_type="call")

    def test_price_below_intrinsic_put_raises(self):
        # Deep ITM put: intrinsic ≈ K×e^{-rT} - S > 0
        with pytest.raises(IVSolverError, match="lower bound"):
            implied_vol(market_price=0.01, spot=50, strike=100,
                        rate=0.0, time_to_expiry=1.0, option_type="put")

    def test_zero_price_raises(self):
        with pytest.raises(IVSolverError, match="positive"):
            implied_vol(market_price=0.0, spot=100, strike=100,
                        rate=0.05, time_to_expiry=1.0, option_type="call")

    def test_negative_price_raises(self):
        with pytest.raises(IVSolverError, match="positive"):
            implied_vol(market_price=-5.0, spot=100, strike=100,
                        rate=0.05, time_to_expiry=1.0, option_type="call")


# ---------------------------------------------------------------------------
# Input validation (propagated from black_scholes._validate_inputs)
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_invalid_option_type_raises(self):
        with pytest.raises(ValueError, match="option_type"):
            implied_vol(market_price=5.0, spot=100, strike=100,
                        rate=0.05, time_to_expiry=1.0, option_type="binary")

    def test_zero_spot_raises(self):
        with pytest.raises(ValueError, match="spot"):
            implied_vol(market_price=5.0, spot=0, strike=100,
                        rate=0.05, time_to_expiry=1.0, option_type="call")

    def test_zero_expiry_raises(self):
        with pytest.raises(ValueError):
            implied_vol(market_price=5.0, spot=100, strike=100,
                        rate=0.05, time_to_expiry=0.0, option_type="call")
