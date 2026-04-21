"""Shared sidebar component for QuantDesk — ticker widget, live price, market status."""

import datetime
import os

import requests
import streamlit as st
import yfinance as yf

from styles import (
    ACCENT_GOLD, BORDER, CALL_BLUE, FONT_MONO,
    TEXT_DIM, TEXT_MUTED, TEXT_PRIMARY, _rgba,
)

try:
    import pytz
    _HAS_PYTZ = True
except ImportError:
    _HAS_PYTZ = False


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_live_price(ticker: str):
    """Return (price, source_label). Tries Finnhub first, falls back to yfinance."""
    if not ticker:
        return None, ""
    key = os.environ.get("FINNHUB_KEY", "")
    if key:
        try:
            resp = requests.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": ticker, "token": key},
                timeout=4,
            )
            data = resp.json()
            price = data.get("c")
            if price and float(price) > 0:
                return float(price), "Finnhub"
        except Exception:
            pass
    try:
        fi = yf.Ticker(ticker).fast_info
        p = getattr(fi, "last_price", None)
        if p and float(p) > 0:
            return float(p), "yfinance"
    except Exception:
        pass
    return None, ""


def _market_status():
    """Return (label, color) for US equity market open/closed status."""
    try:
        if _HAS_PYTZ:
            et = datetime.datetime.now(pytz.timezone("America/New_York"))
        else:
            et = datetime.datetime.utcnow() - datetime.timedelta(hours=5)
        if et.weekday() < 5 and datetime.time(9, 30) <= et.time() <= datetime.time(16, 0):
            return "MARKET OPEN", ACCENT_GOLD
    except Exception:
        pass
    return "MARKET CLOSED", TEXT_MUTED


def render_shared_sidebar() -> None:
    """
    Render QuantDesk branding + shared ticker widget + live price.

    Must be called inside `with st.sidebar:` — does NOT open its own sidebar context.
    On ticker change: writes st.session_state["ticker"], clears "fetched", calls st.rerun().
    """
    current = st.session_state.get("ticker", "AAPL")
    status_label, status_color = _market_status()

    st.markdown(f"""
    <div style="padding:14px 0 10px 0;border-bottom:1px solid {BORDER};margin-bottom:12px;">
      <div style="font-family:{FONT_MONO};font-size:14px;font-weight:600;
                  color:{TEXT_PRIMARY};letter-spacing:0.1em;text-transform:uppercase;">
        QuantDesk
      </div>
      <div style="font-family:{FONT_MONO};font-size:9px;color:{TEXT_MUTED};
                  letter-spacing:0.06em;margin-top:3px;">
        Options Pricer &nbsp;·&nbsp; DCF Valuation
      </div>
      <div style="font-family:{FONT_MONO};font-size:8px;font-weight:600;
                  letter-spacing:0.12em;color:{status_color};
                  text-transform:uppercase;margin-top:5px;">
        &#9679; {status_label}
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        f"<div style='font-family:{FONT_MONO};font-size:9px;text-transform:uppercase;"
        f"letter-spacing:0.1em;color:{TEXT_MUTED};margin-bottom:4px;'>Ticker</div>",
        unsafe_allow_html=True,
    )
    new_ticker = st.text_input(
        "ticker_shared_label",
        value=current,
        max_chars=10,
        label_visibility="collapsed",
        key="ticker_input_shared",
    ).strip().upper()

    if new_ticker and new_ticker != current:
        st.session_state["ticker"] = new_ticker
        st.session_state.pop("fetched", None)
        st.rerun()

    display_ticker = st.session_state.get("ticker", "AAPL")
    price, source = _fetch_live_price(display_ticker)
    if price is not None:
        st.metric(
            label=f"{display_ticker}  ·  {source}",
            value=f"${price:,.2f}",
        )
    else:
        st.caption(f"Price unavailable for {display_ticker}")

    st.markdown(
        f"<hr style='border-color:{BORDER};margin:10px 0 8px 0;'>",
        unsafe_allow_html=True,
    )
