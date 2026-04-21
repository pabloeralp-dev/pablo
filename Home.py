"""QuantDesk — Home page and entry point."""

import streamlit as st

from shared_sidebar import _fetch_live_price, render_shared_sidebar
from styles import (
    ACCENT_GOLD, BORDER, CALL_BLUE, FONT_MONO,
    TEXT_DIM, TEXT_MUTED, TEXT_PRIMARY,
    inject_css, _rgba,
)

# ── Page config — only called here, never in pages/ ──────────────────────────
st.set_page_config(
    page_title="QuantDesk",
    page_icon="▪",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── Session state bootstrap ───────────────────────────────────────────────────
st.session_state.setdefault("ticker", "AAPL")
st.session_state.setdefault("wacc", 0.10)
st.session_state.setdefault("valuation_run", False)
st.session_state.setdefault("dcf_result", None)
st.session_state.setdefault("dcf_inputs", None)
st.session_state.setdefault("analyst_hash", None)
st.session_state.setdefault("analyst_text", "")
st.session_state.setdefault("analyst_followups", {})

# ── Shared sidebar ────────────────────────────────────────────────────────────
with st.sidebar:
    render_shared_sidebar()
    st.markdown(
        f"<div style='font-family:{FONT_MONO};font-size:9px;color:{TEXT_MUTED};margin-top:4px;'>"
        f"Navigate using the pages above</div>",
        unsafe_allow_html=True,
    )

# ── Hero header ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding:24px 0 16px 0;border-bottom:1px solid {BORDER};margin-bottom:24px;">
  <div style="font-family:{FONT_MONO};font-size:20px;font-weight:600;
              color:{TEXT_PRIMARY};letter-spacing:0.12em;text-transform:uppercase;">
    QuantDesk
  </div>
  <div style="font-family:{FONT_MONO};font-size:10px;color:{TEXT_MUTED};
              letter-spacing:0.08em;margin-top:6px;">
    Quantitative Finance Workstation &nbsp;·&nbsp; Options Pricing &nbsp;·&nbsp; DCF Valuation
  </div>
</div>
""", unsafe_allow_html=True)

# ── Ticker search bar + live price ────────────────────────────────────────────
ticker = st.session_state.get("ticker", "AAPL")
col_t, col_p, col_spacer = st.columns([2, 2, 4])

with col_t:
    entered = st.text_input(
        "Search ticker",
        value=ticker,
        max_chars=10,
        key="home_ticker_search",
    ).strip().upper()
    if entered and entered != ticker:
        st.session_state["ticker"] = entered
        st.session_state.pop("fetched", None)
        st.rerun()

with col_p:
    price, source = _fetch_live_price(st.session_state.get("ticker", "AAPL"))
    display = st.session_state.get("ticker", "AAPL")
    if price is not None:
        st.metric(display, f"${price:,.2f}", f"via {source}")
    else:
        st.metric(display, "—")

# ── Module cards ──────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
card1, card2 = st.columns(2)

with card1:
    st.markdown(f"""
    <div style="background:{_rgba(CALL_BLUE,0.06)};border:1px solid {_rgba(CALL_BLUE,0.25)};
                border-radius:2px;padding:20px 22px;min-height:110px;">
      <div style="font-family:{FONT_MONO};font-size:11px;font-weight:600;
                  color:{CALL_BLUE};letter-spacing:0.1em;text-transform:uppercase;
                  margin-bottom:8px;">Options Pricer</div>
      <div style="font-family:{FONT_MONO};font-size:10px;color:{TEXT_DIM};line-height:1.8;">
        Black-Scholes-Merton pricing &nbsp;·&nbsp; Full Greeks<br>
        IV solver &nbsp;·&nbsp; Live market smile &nbsp;·&nbsp; AI analyst
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/1_Options_Pricer.py", label="Open Options Pricer \u2192")

with card2:
    st.markdown(f"""
    <div style="background:{_rgba(ACCENT_GOLD,0.06)};border:1px solid {_rgba(ACCENT_GOLD,0.25)};
                border-radius:2px;padding:20px 22px;min-height:110px;">
      <div style="font-family:{FONT_MONO};font-size:11px;font-weight:600;
                  color:{ACCENT_GOLD};letter-spacing:0.1em;text-transform:uppercase;
                  margin-bottom:8px;">DCF Valuation</div>
      <div style="font-family:{FONT_MONO};font-size:10px;color:{TEXT_DIM};line-height:1.8;">
        Discounted cash flow &nbsp;·&nbsp; WACC calculator<br>
        Sensitivity &nbsp;·&nbsp; Football field &nbsp;·&nbsp; Monte Carlo
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/2_DCF_Valuation.py", label="Open DCF Valuation \u2192")
