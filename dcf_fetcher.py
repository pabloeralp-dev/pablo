"""yfinance data fetcher — wraps all external data calls with graceful fallbacks."""

from __future__ import annotations

import re
import time
from typing import Optional

import yfinance as yf


def _clean_ticker(ticker: str) -> str:
    """Sanitise and normalise a ticker symbol.

    Args:
        ticker: Raw user input.

    Returns:
        Uppercase, stripped ticker.

    Raises:
        ValueError: If the ticker is empty or contains invalid characters.
    """
    cleaned = ticker.strip().upper()[:10]
    if not cleaned:
        raise ValueError("Ticker symbol cannot be empty.")
    if not re.match(r"^[A-Z0-9.]+$", cleaned):
        raise ValueError(f"Invalid ticker symbol: '{ticker}'. Use letters, numbers, and dots only.")
    return cleaned


def fetch_ticker_data(ticker: str) -> dict:
    """Fetch financial data for a given ticker from yfinance.

    Retries once on failure. Returns a dictionary with all fields set to None
    if the ticker cannot be found — never raises.

    Args:
        ticker: Stock ticker symbol (e.g. "AAPL").

    Returns:
        Dictionary with keys:
            ticker (str), beta (float|None), current_price (float|None),
            week52_high (float|None), week52_low (float|None),
            shares_outstanding (int|None), net_debt (float|None),
            revenue (float|None), ebitda (float|None),
            error (str|None)
    """
    result: dict = {
        "ticker": ticker,
        "beta": None,
        "current_price": None,
        "week52_high": None,
        "week52_low": None,
        "shares_outstanding": None,
        "net_debt": None,
        "revenue": None,
        "ebitda": None,
        "error": None,
    }

    try:
        cleaned = _clean_ticker(ticker)
    except ValueError as e:
        result["error"] = str(e)
        return result

    result["ticker"] = cleaned

    for attempt in range(2):
        try:
            stock = yf.Ticker(cleaned)
            info = stock.info or {}

            # Check the ticker returned real data
            if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
                # Try fast_info as fallback
                try:
                    fi = stock.fast_info
                    result["current_price"] = _safe_float(getattr(fi, "last_price", None))
                    result["week52_high"] = _safe_float(getattr(fi, "year_high", None))
                    result["week52_low"] = _safe_float(getattr(fi, "year_low", None))
                    result["shares_outstanding"] = _safe_int(getattr(fi, "shares", None))
                except Exception:
                    pass
                if result["current_price"] is None:
                    result["error"] = f"Ticker '{cleaned}' not found or has no price data."
                    return result
            else:
                result["current_price"] = _safe_float(
                    info.get("currentPrice") or info.get("regularMarketPrice")
                )
                result["week52_high"] = _safe_float(info.get("fiftyTwoWeekHigh"))
                result["week52_low"] = _safe_float(info.get("fiftyTwoWeekLow"))
                result["shares_outstanding"] = _safe_int(info.get("sharesOutstanding"))
                result["beta"] = _safe_float(info.get("beta"))
                result["revenue"] = _safe_float(info.get("totalRevenue"))
                result["ebitda"] = _safe_float(info.get("ebitda"))

                # Net debt = totalDebt - cashAndCashEquivalents
                total_debt = _safe_float(info.get("totalDebt")) or 0.0
                cash = _safe_float(info.get("cashAndCashEquivalents") or info.get("totalCash")) or 0.0
                result["net_debt"] = total_debt - cash

            break  # success — exit retry loop

        except Exception as exc:
            if attempt == 0:
                time.sleep(2)
            else:
                result["error"] = f"Could not fetch data for '{cleaned}': {exc}"

    return result


def _safe_float(value) -> Optional[float]:
    """Return a float or None, swallowing conversion errors."""
    try:
        v = float(value)
        return v if not (v != v) else None  # NaN check
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> Optional[int]:
    """Return an int or None, swallowing conversion errors."""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
