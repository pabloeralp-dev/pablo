"""Formatting helpers for the DCF valuation tool."""

from __future__ import annotations


def fmt_currency(value: float, decimals: int = 0) -> str:
    """Format a float as a dollar amount with thousands separators.

    Args:
        value: Monetary value in dollars.
        decimals: Decimal places to show.

    Returns:
        Formatted string, e.g. "$1,234,567".
    """
    if value is None:
        return "N/A"
    fmt = f"{{:,.{decimals}f}}"
    formatted = fmt.format(abs(value))
    return f"-${formatted}" if value < 0 else f"${formatted}"


def fmt_pct(value: float, decimals: int = 2) -> str:
    """Format a decimal as a percentage string.

    Args:
        value: Decimal fraction, e.g. 0.105 → "10.50%".
        decimals: Decimal places.

    Returns:
        Formatted percentage string.
    """
    if value is None:
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def fmt_ratio(value: float, decimals: int = 4) -> str:
    """Format a ratio to 4 decimal places.

    Args:
        value: Ratio value.
        decimals: Decimal places.

    Returns:
        Formatted ratio string.
    """
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}x"


def fmt_multiple(value: float, decimals: int = 1) -> str:
    """Format an EV/EBITDA or similar multiple.

    Args:
        value: Multiple value.
        decimals: Decimal places.

    Returns:
        Formatted string, e.g. "10.0x".
    """
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}x"


def fmt_millions(value: float, decimals: int = 1) -> str:
    """Format a large dollar value in millions.

    Args:
        value: Raw dollar value.
        decimals: Decimal places.

    Returns:
        Formatted string, e.g. "$1,234.5M".
    """
    if value is None:
        return "N/A"
    m = value / 1_000_000
    return f"${m:,.{decimals}f}M"


def fmt_billions(value: float, decimals: int = 2) -> str:
    """Format a large dollar value in billions.

    Args:
        value: Raw dollar value.
        decimals: Decimal places.

    Returns:
        Formatted string, e.g. "$1.23B".
    """
    if value is None:
        return "N/A"
    b = value / 1_000_000_000
    return f"${b:,.{decimals}f}B"
