"""
Black-Scholes Option Pricer — Streamlit Dashboard

Run with:
    python -m streamlit run dashboard.py

All financial logic is imported from pricer/. This file is presentation only.
"""

import datetime
import hashlib
import os
import warnings
import anthropic as _anthropic
import numpy as np
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.subplots as psub
import yfinance as yf
warnings.filterwarnings("ignore")

from pricer.black_scholes import black_scholes_price, black_scholes_greeks
from pricer.implied_vol import implied_vol, IVSolverError

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
BG_PAGE      = "#0A0A0A"
BG_CARD      = "#111111"
BG_SIDEBAR   = "#0D0D0D"
BG_CHART     = "#0F0F0F"
BORDER       = "#1E1E1E"
TEXT_PRIMARY = "#E8E8E8"
TEXT_DIM     = "#6B7280"
TEXT_MUTED   = "#4B5563"
CALL_BLUE    = "#2563EB"
PUT_RED      = "#DC2626"
ACCENT_GOLD  = "#D97706"
ACCENT_TEAL  = "#0D9488"
FONT_MONO    = "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace"

def _rgba(hex6: str, alpha: float) -> str:
    """Convert '#rrggbb' + alpha to 'rgba(r,g,b,a)' for Plotly."""
    r = int(hex6[1:3], 16)
    g = int(hex6[3:5], 16)
    b = int(hex6[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"

def _chart_base(height: int = 420, title: str = "") -> dict:
    """Return a Plotly layout dict with the shared dark terminal theme."""
    return dict(
        title=dict(text=title, font=dict(family=FONT_MONO, size=13, color=TEXT_DIM), x=0),
        height=height,
        paper_bgcolor=BG_CHART,
        plot_bgcolor=BG_CHART,
        font=dict(family=FONT_MONO, size=11, color=TEXT_DIM),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor=BORDER,
            tickcolor=TEXT_MUTED,
            tickfont=dict(family=FONT_MONO, size=10, color=TEXT_MUTED),
            title_font=dict(family=FONT_MONO, size=11, color=TEXT_DIM),
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            linecolor=BORDER,
            tickcolor=TEXT_MUTED,
            tickfont=dict(family=FONT_MONO, size=10, color=TEXT_MUTED),
            title_font=dict(family=FONT_MONO, size=11, color=TEXT_DIM),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=BORDER,
            borderwidth=1,
            font=dict(family=FONT_MONO, size=10, color=TEXT_DIM),
        ),
        margin=dict(t=50, b=40, l=50, r=20),
        showlegend=True,
    )

def _apply_subplot_theme(fig, n: int):
    """Apply dark theme to all axes in a subplot figure with n panels."""
    axis_style = dict(
        showgrid=False, zeroline=False, linecolor=BORDER,
        tickcolor=TEXT_MUTED,
        tickfont=dict(family=FONT_MONO, size=9, color=TEXT_MUTED),
    )
    for i in range(1, n + 1):
        suffix = "" if i == 1 else str(i)
        fig.update_layout(**{
            f"xaxis{suffix}": axis_style,
            f"yaxis{suffix}": axis_style,
        })

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="BS Pricer",
    page_icon="▪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS — Bloomberg terminal aesthetic
# ---------------------------------------------------------------------------
st.markdown(f"""
<style>
  /* ── Import fonts ── */
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&display=swap');

  /* ── Root reset ── */
  html, body, [data-testid="stApp"] {{
    background-color: {BG_PAGE} !important;
    color: {TEXT_PRIMARY} !important;
    font-family: {FONT_MONO} !important;
  }}

  /* ── Main content area ── */
  [data-testid="stMain"], .main .block-container {{
    background-color: {BG_PAGE} !important;
    padding-top: 1rem !important;
  }}

  /* ── Sidebar ── */
  [data-testid="stSidebar"], [data-testid="stSidebar"] > div {{
    background-color: {BG_SIDEBAR} !important;
    border-right: 1px solid {BORDER} !important;
  }}
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] .stRadio label,
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span {{
    font-family: {FONT_MONO} !important;
    font-size: 11px !important;
    color: {TEXT_DIM} !important;
    letter-spacing: 0.02em !important;
  }}
  [data-testid="stSidebar"] .stSlider > label {{
    font-size: 10px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: {TEXT_MUTED} !important;
  }}

  /* ── Slider track ── */
  [data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {{
    background-color: {CALL_BLUE} !important;
    border-color: {CALL_BLUE} !important;
  }}

  /* ── Tabs ── */
  [data-testid="stTabs"] [role="tablist"] {{
    background-color: {BG_PAGE} !important;
    border-bottom: 1px solid {BORDER} !important;
    gap: 0 !important;
  }}
  [data-testid="stTabs"] button[role="tab"] {{
    background-color: transparent !important;
    color: {TEXT_MUTED} !important;
    font-family: {FONT_MONO} !important;
    font-size: 10px !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    padding: 8px 18px !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
  }}
  [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
    color: {TEXT_PRIMARY} !important;
    border-bottom: 2px solid {CALL_BLUE} !important;
  }}
  [data-testid="stTabs"] button[role="tab"]:hover {{
    color: {TEXT_DIM} !important;
    background-color: {BG_CARD} !important;
  }}

  /* ── Metric cards ── */
  [data-testid="metric-container"] {{
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 2px !important;
    padding: 14px 16px !important;
  }}
  [data-testid="metric-container"] label {{
    font-family: {FONT_MONO} !important;
    font-size: 9px !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: {TEXT_MUTED} !important;
  }}
  [data-testid="metric-container"] [data-testid="stMetricValue"] {{
    font-family: {FONT_MONO} !important;
    font-size: 22px !important;
    font-weight: 400 !important;
    color: {TEXT_PRIMARY} !important;
    letter-spacing: -0.02em !important;
  }}
  [data-testid="metric-container"] [data-testid="stMetricDelta"] {{
    font-family: {FONT_MONO} !important;
    font-size: 10px !important;
    color: {TEXT_MUTED} !important;
  }}

  /* ── Headings ── */
  h1, h2, h3, .stMarkdown h3 {{
    font-family: {FONT_MONO} !important;
    font-weight: 400 !important;
    color: {TEXT_PRIMARY} !important;
    letter-spacing: 0.02em !important;
  }}

  /* ── Subheaders inside tabs ── */
  [data-testid="stHeading"] h2 {{
    font-size: 12px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: {TEXT_MUTED} !important;
    border-bottom: 1px solid {BORDER} !important;
    padding-bottom: 6px !important;
    margin-bottom: 12px !important;
  }}

  /* ── Captions ── */
  [data-testid="stCaptionContainer"] p,
  .stCaption, small, caption {{
    font-family: {FONT_MONO} !important;
    font-size: 9px !important;
    color: {TEXT_MUTED} !important;
    letter-spacing: 0.04em !important;
  }}

  /* ── Number inputs ── */
  [data-testid="stNumberInput"] input {{
    font-family: {FONT_MONO} !important;
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT_PRIMARY} !important;
    border-radius: 2px !important;
  }}

  /* ── Text inputs ── */
  [data-testid="stTextInput"] input {{
    font-family: {FONT_MONO} !important;
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT_PRIMARY} !important;
    border-radius: 2px !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
  }}

  /* ── Selectbox ── */
  [data-testid="stSelectbox"] div[data-baseweb="select"] {{
    font-family: {FONT_MONO} !important;
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 2px !important;
  }}

  /* ── Radio ── */
  [data-testid="stRadio"] label {{
    font-family: {FONT_MONO} !important;
    font-size: 10px !important;
  }}

  /* ── Divider ── */
  hr {{
    border-color: {BORDER} !important;
    margin: 10px 0 !important;
  }}

  /* ── Alert / error ── */
  [data-testid="stAlert"] {{
    background-color: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    font-family: {FONT_MONO} !important;
    font-size: 11px !important;
    border-radius: 2px !important;
  }}

  /* ── Plotly chart container ── */
  [data-testid="stPlotlyChart"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 2px !important;
    overflow: hidden;
  }}

  /* ── Checkbox ── */
  [data-testid="stCheckbox"] label {{
    font-family: {FONT_MONO} !important;
    font-size: 10px !important;
    color: {TEXT_DIM} !important;
  }}

  /* ── Scrollbar ── */
  ::-webkit-scrollbar {{ width: 4px; height: 4px; }}
  ::-webkit-scrollbar-track {{ background: {BG_PAGE}; }}
  ::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 2px; }}

  /* ── Header band ── */
  .bs-header {{
    display: flex;
    align-items: baseline;
    gap: 16px;
    padding: 12px 0 10px 0;
    border-bottom: 1px solid {BORDER};
    margin-bottom: 16px;
  }}
  .bs-header-title {{
    font-family: {FONT_MONO};
    font-size: 15px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }}
  .bs-header-sub {{
    font-family: {FONT_MONO};
    font-size: 9px;
    color: {TEXT_MUTED};
    letter-spacing: 0.06em;
  }}
  .bs-tag {{
    font-family: {FONT_MONO};
    font-size: 9px;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 2px 7px;
    border-radius: 1px;
  }}
  .bs-tag-call {{ background: {_rgba(CALL_BLUE, 0.15)}; color: {CALL_BLUE}; border: 1px solid {_rgba(CALL_BLUE, 0.3)}; }}
  .bs-tag-put  {{ background: {_rgba(PUT_RED,  0.15)}; color: {PUT_RED};  border: 1px solid {_rgba(PUT_RED,  0.3)}; }}

  /* ── Greeks table ── */
  .greek-row {{
    display: flex;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid {BORDER};
    gap: 0;
  }}
  .greek-name {{
    font-family: {FONT_MONO};
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {TEXT_MUTED};
    width: 130px;
    flex-shrink: 0;
  }}
  .greek-val {{
    font-family: {FONT_MONO};
    font-size: 13px;
    font-weight: 500;
    color: {TEXT_PRIMARY};
    width: 110px;
    flex-shrink: 0;
    letter-spacing: -0.01em;
  }}
  .greek-desc {{
    font-family: {FONT_MONO};
    font-size: 9px;
    color: {TEXT_MUTED};
    letter-spacing: 0.02em;
  }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="bs-header">
  <span class="bs-header-title">Black-Scholes Pricer</span>
  <span class="bs-header-sub">European vanilla options &nbsp;·&nbsp; No dividends &nbsp;·&nbsp; Continuous compounding &nbsp;·&nbsp; BSM 1973</span>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — shared inputs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"""
    <div style="padding: 14px 0 8px 0; border-bottom: 1px solid {BORDER}; margin-bottom: 12px;">
      <div style="font-family:{FONT_MONO}; font-size:13px; font-weight:600;
                  color:{TEXT_PRIMARY}; letter-spacing:0.08em; text-transform:uppercase;">
        BS Pricer
      </div>
      <div style="font-family:{FONT_MONO}; font-size:9px; color:{TEXT_MUTED};
                  letter-spacing:0.04em; margin-top:4px;">
        Black-Scholes-Merton Model
      </div>
    </div>
    """, unsafe_allow_html=True)

    spot   = st.slider("Spot price (S)",      min_value=10.0,  max_value=500.0, value=100.0, step=1.0)
    strike = st.slider("Strike price (K)",    min_value=10.0,  max_value=500.0, value=100.0, step=1.0)
    vol_pct  = st.slider("Volatility σ (%)",  min_value=1,   max_value=150, value=20,  step=1)
    rate_pct = st.slider("Risk-free rate r (%)", min_value=-2,  max_value=20,  value=5,   step=1)
    vol  = vol_pct  / 100.0
    rate = rate_pct / 100.0
    time  = st.slider("Time to expiry T (y)", min_value=0.02, max_value=5.0, value=1.0, step=0.05)
    otype = st.radio("Option type", ["call", "put"], horizontal=True)

    st.markdown(f"""
    <div style="margin-top:16px; padding-top:10px; border-top:1px solid {BORDER};">
      <div style="font-family:{FONT_MONO}; font-size:9px; color:{TEXT_MUTED}; line-height:1.8;">
        Θ per calendar day<br>
        ν &amp; ρ per 1% move<br>
        Brent's method for IV
      </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Compute price + Greeks
# ---------------------------------------------------------------------------
price     = black_scholes_price(spot, strike, vol, rate, time, otype)
greeks    = black_scholes_greeks(spot, strike, vol, rate, time, otype)
intrinsic = max(spot - strike, 0) if otype == "call" else max(strike - spot, 0)
time_val  = price - intrinsic
colour    = CALL_BLUE if otype == "call" else PUT_RED
tag_cls   = "bs-tag-call" if otype == "call" else "bs-tag-put"

# ---------------------------------------------------------------------------
# News helpers
# ---------------------------------------------------------------------------
def _sentiment_badge(score, label) -> str:
    """Return an HTML badge string given a numeric score or a text label."""
    if label:
        label = label.lower()
        if label in ("bullish", "positive"):
            return f'<span style="font-family:{FONT_MONO};font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;padding:2px 7px;border-radius:1px;background:{_rgba(ACCENT_TEAL,0.15)};color:{ACCENT_TEAL};border:1px solid {_rgba(ACCENT_TEAL,0.35)};">BULL</span>'
        if label in ("bearish", "negative"):
            return f'<span style="font-family:{FONT_MONO};font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;padding:2px 7px;border-radius:1px;background:{_rgba(PUT_RED,0.15)};color:{PUT_RED};border:1px solid {_rgba(PUT_RED,0.35)};">BEAR</span>'
    if score is not None:
        if score > 0.15:
            return f'<span style="font-family:{FONT_MONO};font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;padding:2px 7px;border-radius:1px;background:{_rgba(ACCENT_TEAL,0.15)};color:{ACCENT_TEAL};border:1px solid {_rgba(ACCENT_TEAL,0.35)};">BULL</span>'
        if score < -0.15:
            return f'<span style="font-family:{FONT_MONO};font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;padding:2px 7px;border-radius:1px;background:{_rgba(PUT_RED,0.15)};color:{PUT_RED};border:1px solid {_rgba(PUT_RED,0.35)};">BEAR</span>'
    return f'<span style="font-family:{FONT_MONO};font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;padding:2px 7px;border-radius:1px;background:{_rgba(TEXT_MUTED,0.12)};color:{TEXT_MUTED};border:1px solid {_rgba(TEXT_MUTED,0.25)};">NEUT</span>'


@st.cache_data(ttl=60, show_spinner=False)
def fetch_finnhub_news(ticker: str) -> list:
    key = os.environ.get("FINNHUB_KEY", "")
    if not key:
        return []
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    url = "https://finnhub.io/api/v1/company-news"
    params = {"symbol": ticker, "from": str(week_ago), "to": str(today), "token": key}
    try:
        resp = requests.get(url, params=params, timeout=6)
        resp.raise_for_status()
        items = resp.json()[:12]
    except Exception:
        return []
    results = []
    for item in items:
        ts = datetime.datetime.fromtimestamp(item.get("datetime", 0)).strftime("%Y-%m-%d %H:%M")
        results.append({
            "headline": item.get("headline", ""),
            "source":   item.get("source", "Finnhub"),
            "url":      item.get("url", ""),
            "ts":       ts,
            "score":    item.get("sentiment", {}).get("score") if isinstance(item.get("sentiment"), dict) else None,
            "label":    None,
        })
    return results


@st.cache_data(ttl=60, show_spinner=False)
def fetch_marketaux_news(ticker: str) -> list:
    key = os.environ.get("MARKETAUX_KEY", "")
    if not key:
        return []
    url = "https://api.marketaux.com/v1/news/all"
    params = {"symbols": ticker, "filter_entities": "true", "language": "en",
              "api_token": key, "limit": 10}
    try:
        resp = requests.get(url, params=params, timeout=6)
        resp.raise_for_status()
        items = resp.json().get("data", [])
    except Exception:
        return []
    results = []
    for item in items:
        ts_raw = item.get("published_at", "")
        try:
            ts = datetime.datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        except Exception:
            ts = ts_raw[:16]
        entities = item.get("entities") or []
        sentiment_label = None
        for ent in entities:
            if ent.get("symbol", "").upper() == ticker.upper():
                sentiment_label = ent.get("sentiment_score_avg")
                break
        score = float(sentiment_label) if sentiment_label is not None else None
        results.append({
            "headline": item.get("title", ""),
            "source":   item.get("source", "Marketaux"),
            "url":      item.get("url", ""),
            "ts":       ts,
            "score":    score,
            "label":    None,
        })
    return results


def _render_news(articles: list):
    if not articles:
        return
    cards_html = ""
    for a in articles:
        badge = _sentiment_badge(a["score"], a["label"])
        headline_html = (
            f'<a href="{a["url"]}" target="_blank" style="color:{TEXT_PRIMARY};text-decoration:none;">'
            f'{a["headline"]}</a>' if a["url"] else a["headline"]
        )
        cards_html += f"""
        <div style="padding:10px 14px;border:1px solid {BORDER};border-radius:2px;
                    margin-bottom:6px;background:{BG_CARD};">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:5px;">
            {badge}
            <span style="font-family:{FONT_MONO};font-size:9px;color:{TEXT_MUTED};">
              {a['source']} &nbsp;·&nbsp; {a['ts']}
            </span>
          </div>
          <div style="font-family:{FONT_MONO};font-size:11px;color:{TEXT_PRIMARY};line-height:1.5;">
            {headline_html}
          </div>
        </div>"""
    st.markdown(cards_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# AI analyst helpers
# ---------------------------------------------------------------------------
def _params_hash(spot, strike, vol_pct, rate_pct, time, otype):
    key = f"{spot}|{strike}|{vol_pct}|{rate_pct}|{time}|{otype}"
    return hashlib.md5(key.encode()).hexdigest()


def _build_analyst_prompt(spot, strike, vol, rate, time, otype, call_p, put_p, g):
    ratio = spot / strike
    if ratio > 1.02:
        moneyness = "in-the-money" if otype == "call" else "out-of-the-money"
    elif ratio < 0.98:
        moneyness = "out-of-the-money" if otype == "call" else "in-the-money"
    else:
        moneyness = "at-the-money"
    return (
        f"Spot: ${spot:.2f}  Strike: ${strike:.2f}  Type: {otype.upper()}  "
        f"Moneyness: {moneyness}\n"
        f"IV: {vol*100:.2f}%  Rate: {rate*100:.2f}%  "
        f"Expiry: {time:.3f}y ({int(time*365)} days)\n"
        f"Call price: ${call_p:.4f}  Put price: ${put_p:.4f}\n"
        f"Δ {g['delta']:+.4f}  Γ {g['gamma']:+.4f}  "
        f"ν/1% {g['vega']:+.4f}  Θ/day {g['theta']:+.4f}  ρ/1% {g['rho']:+.4f}\n\n"
        f"Write 3-4 sentences of tight analyst prose — no headers, no bullets. Cover: "
        f"(1) moneyness and position implications, "
        f"(2) the most significant Greek risk(s) at these values, "
        f"(3) whether {vol*100:.1f}% IV appears cheap, expensive, or fair "
        f"for an equity option at this tenor and moneyness."
    )


def _analyst_box(text, accent, cursor=False):
    """Render a styled analyst commentary div."""
    suffix = "▋" if cursor else ""
    return (
        f'<div style="font-family:{FONT_MONO};font-size:11px;color:{TEXT_PRIMARY};'
        f'line-height:1.8;padding:14px 18px;border:1px solid {BORDER};'
        f'border-left:3px solid {accent};background:{BG_CARD};border-radius:2px;">'
        f'{text}{suffix}</div>'
    )


def _followup_box(text, cursor=False):
    suffix = "▋" if cursor else ""
    return (
        f'<div style="font-family:{FONT_MONO};font-size:11px;color:{TEXT_DIM};'
        f'line-height:1.8;padding:12px 18px;border:1px solid {BORDER};'
        f'border-left:3px solid {TEXT_MUTED};background:{BG_CARD};border-radius:2px;">'
        f'{text}{suffix}</div>'
    )


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_pricer, tab_payoff, tab_greeks, tab_iv, tab_live, tab_surface = st.tabs([
    "PRICER", "PAYOFF", "GREEKS", "IV SOLVER", "LIVE MARKET", "SURFACE"
])

# ── Tab 1: Pricer ──────────────────────────────────────────────────────────
with tab_pricer:
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:18px;">
      <span class="bs-tag {tag_cls}">European {otype.upper()}</span>
      <span style="font-family:{FONT_MONO}; font-size:10px; color:{TEXT_MUTED};">
        S={spot} &nbsp; K={strike} &nbsp; σ={vol_pct}% &nbsp; r={rate_pct}% &nbsp; T={time}y
      </span>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Price",           f"${price:.4f}")
    c2.metric("Intrinsic value", f"${intrinsic:.4f}")
    c3.metric("Time value",      f"${time_val:.4f}")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    col_g, col_bar = st.columns([1, 1])

    with col_g:
        st.markdown(f"""
        <div style="font-family:{FONT_MONO}; font-size:9px; text-transform:uppercase;
                    letter-spacing:0.1em; color:{TEXT_MUTED}; margin-bottom:8px;">
          Greeks
        </div>
        """, unsafe_allow_html=True)
        greek_rows = [
            ("Delta",      "Δ", greeks["delta"],  "∂V/∂S — change per $1 spot move"),
            ("Gamma",      "Γ", greeks["gamma"],  "∂²V/∂S² — change in delta per $1"),
            ("Vega/1%",    "ν", greeks["vega"],   "∂V/∂σ — change per 1% vol move"),
            ("Theta/day",  "Θ", greeks["theta"],  "∂V/∂t — daily time decay"),
            ("Rho/1%",     "ρ", greeks["rho"],    "∂V/∂r — change per 1% rate move"),
        ]
        rows_html = ""
        for name, sym, val, desc in greek_rows:
            val_color = TEXT_PRIMARY
            rows_html += f"""
            <div class="greek-row">
              <span class="greek-name">{sym}&nbsp;&nbsp;{name}</span>
              <span class="greek-val">{val:+.4f}</span>
              <span class="greek-desc">{desc}</span>
            </div>"""
        st.markdown(rows_html, unsafe_allow_html=True)

    with col_bar:
        fig = go.Figure(go.Bar(
            x=["Intrinsic", "Time value", "Total price"],
            y=[intrinsic, time_val, price],
            marker_color=[_rgba(colour, 0.25), _rgba(colour, 0.50), colour],
            marker_line_color=[_rgba(colour, 0.4), _rgba(colour, 0.7), colour],
            marker_line_width=1,
            text=[f"${v:.4f}" for v in [intrinsic, time_val, price]],
            textposition="outside",
            textfont=dict(family=FONT_MONO, size=10, color=TEXT_DIM),
        ))
        layout = _chart_base(height=280, title="Price decomposition")
        layout["yaxis"]["title"] = "Value ($)"
        layout["showlegend"] = False
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

    # ── AI Analyst Commentary ──────────────────────────────────────────────
    st.markdown(f"""
    <div style="font-family:{FONT_MONO};font-size:9px;text-transform:uppercase;
                letter-spacing:0.1em;color:{TEXT_MUTED};margin-top:24px;
                padding-top:14px;border-top:1px solid {BORDER};margin-bottom:10px;
                display:flex;align-items:center;gap:12px;">
      AI Analyst
      <span style="text-transform:none;letter-spacing:0;color:{_rgba(TEXT_MUTED,0.6)};">
        claude-sonnet-4-6 &nbsp;·&nbsp; streams on every parameter change
      </span>
    </div>
    """, unsafe_allow_html=True)

    _anthr_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not _anthr_key:
        st.markdown(
            f'<div style="font-family:{FONT_MONO};font-size:10px;color:{TEXT_MUTED};'
            f'padding:10px 14px;border:1px solid {BORDER};border-radius:2px;">'
            f'Set <code style="color:{TEXT_DIM};">ANTHROPIC_API_KEY</code> to enable AI analyst commentary.'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        _call_p = black_scholes_price(spot, strike, vol, rate, time, "call")
        _put_p  = black_scholes_price(spot, strike, vol, rate, time, "put")
        _ctx    = _build_analyst_prompt(spot, strike, vol, rate, time, otype, _call_p, _put_p, greeks)
        _hash   = _params_hash(spot, strike, vol_pct, rate_pct, time, otype)

        if "analyst_hash" not in st.session_state:
            st.session_state.analyst_hash = None
        if "analyst_text" not in st.session_state:
            st.session_state.analyst_text = ""
        if "analyst_followups" not in st.session_state:
            st.session_state.analyst_followups = {}

        _commentary_col, _ = st.columns([2, 1])
        with _commentary_col:
            _box = st.empty()
            if st.session_state.analyst_hash != _hash:
                _full = ""
                try:
                    _ai = _anthropic.Anthropic(api_key=_anthr_key)
                    with _ai.messages.stream(
                        model="claude-sonnet-4-6",
                        max_tokens=400,
                        system=(
                            "You are a senior equity derivatives analyst. "
                            "Respond with tight, precise analyst commentary. "
                            "No markdown, no bullet points — flowing prose only."
                        ),
                        messages=[{"role": "user", "content": _ctx}],
                    ) as _stream:
                        for _chunk in _stream.text_stream:
                            _full += _chunk
                            _box.markdown(_analyst_box(_full, colour, cursor=True),
                                          unsafe_allow_html=True)
                    _box.markdown(_analyst_box(_full, colour), unsafe_allow_html=True)
                    st.session_state.analyst_text = _full
                    st.session_state.analyst_hash = _hash
                    st.session_state.analyst_followups = {}
                except Exception as _e:
                    _box.error(f"Analyst: {_e}")
            else:
                _box.markdown(_analyst_box(st.session_state.analyst_text, colour),
                              unsafe_allow_html=True)

        # Ask the analyst
        st.markdown(f"""
        <div style="font-family:{FONT_MONO};font-size:9px;text-transform:uppercase;
                    letter-spacing:0.1em;color:{TEXT_MUTED};margin-top:14px;margin-bottom:6px;">
          Ask the analyst
        </div>
        """, unsafe_allow_html=True)

        _question = st.text_input(
            "follow-up",
            placeholder="e.g.  How does vega exposure change if I double the tenor?",
            label_visibility="collapsed",
            key="analyst_q",
        )

        if _question.strip():
            _qhash = hashlib.md5(f"{_hash}|{_question}".encode()).hexdigest()
            _fbox  = st.empty()
            if _qhash not in st.session_state.analyst_followups:
                _ftext = ""
                try:
                    _ai2 = _anthropic.Anthropic(api_key=_anthr_key)
                    with _ai2.messages.stream(
                        model="claude-sonnet-4-6",
                        max_tokens=400,
                        system=(
                            "You are a senior equity derivatives analyst. "
                            "Answer follow-up questions concisely and precisely. "
                            "No markdown, no bullet points — flowing prose only."
                        ),
                        messages=[
                            {"role": "user",      "content": _ctx},
                            {"role": "assistant", "content": st.session_state.analyst_text or "Acknowledged."},
                            {"role": "user",      "content": _question},
                        ],
                    ) as _fstream:
                        for _fc in _fstream.text_stream:
                            _ftext += _fc
                            _fbox.markdown(_followup_box(_ftext, cursor=True),
                                           unsafe_allow_html=True)
                    _fbox.markdown(_followup_box(_ftext), unsafe_allow_html=True)
                    st.session_state.analyst_followups[_qhash] = _ftext
                except Exception as _e:
                    _fbox.error(f"Analyst: {_e}")
            else:
                _fbox.markdown(_followup_box(st.session_state.analyst_followups[_qhash]),
                               unsafe_allow_html=True)

# ── Tab 2: Payoff ──────────────────────────────────────────────────────────
with tab_payoff:
    spots = np.linspace(spot * 0.5, spot * 1.5, 300)
    payoff_vals = np.maximum(spots - strike, 0) if otype == "call" else np.maximum(strike - spots, 0)
    bs_vals = np.array([black_scholes_price(float(s), strike, vol, rate, time, otype) for s in spots])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=spots, y=payoff_vals, name="Payoff at expiry",
        line=dict(color=TEXT_MUTED, dash="dash", width=1.5),
    ))
    fig.add_trace(go.Scatter(
        x=spots, y=bs_vals, name=f"BS price  T={time}y",
        line=dict(color=colour, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=np.concatenate([spots, spots[::-1]]),
        y=np.concatenate([bs_vals, payoff_vals[::-1]]),
        fill="toself", fillcolor=_rgba(colour, 0.07),
        line=dict(color="rgba(0,0,0,0)"), name="Time value",
    ))
    fig.add_vline(x=strike, line=dict(color=TEXT_MUTED, dash="dot", width=1),
                  annotation_text="K", annotation_font=dict(family=FONT_MONO, size=9, color=TEXT_MUTED))
    fig.add_vline(x=spot, line=dict(color=colour, dash="dot", width=1),
                  annotation_text="S", annotation_font=dict(family=FONT_MONO, size=9, color=colour))

    layout = _chart_base(height=460,
        title=f"European {otype.upper()} — Payoff vs Current Value")
    layout["xaxis"]["title"] = "Spot ($)"
    layout["yaxis"]["title"] = "Option value ($)"
    layout["yaxis"]["rangemode"] = "tozero"
    layout["legend"]["x"] = 0.02
    layout["legend"]["y"] = 0.96
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Shaded region = time value premium.  Reduce T toward zero to watch it collapse.")

# ── Tab 3: Greeks vs Spot ──────────────────────────────────────────────────
with tab_greeks:
    spots_g = np.linspace(spot * 0.5, spot * 1.5, 200)

    metrics = [
        ("price", "Price ($)"),
        ("delta", "Delta  Δ"),
        ("gamma", "Gamma  Γ"),
        ("vega",  "Vega  ν  /1%"),
        ("theta", "Theta  Θ  /day"),
        ("rho",   "Rho  ρ  /1%"),
    ]

    def greek_series(metric):
        if metric == "price":
            return [black_scholes_price(float(s), strike, vol, rate, time, otype) for s in spots_g]
        return [black_scholes_greeks(float(s), strike, vol, rate, time, otype)[metric] for s in spots_g]

    fig = psub.make_subplots(
        rows=2, cols=3,
        subplot_titles=[m[1] for m in metrics],
        vertical_spacing=0.14,
        horizontal_spacing=0.06,
    )

    xrefs = ["x", "x2", "x3", "x4", "x5", "x6"]
    yrefs = ["y", "y2", "y3", "y4", "y5", "y6"]

    for idx, (metric, label) in enumerate(metrics):
        row, col = divmod(idx, 3)
        vals = greek_series(metric)
        fig.add_trace(
            go.Scatter(x=spots_g, y=vals,
                       line=dict(color=colour, width=1.6),
                       showlegend=False, name=label),
            row=row + 1, col=col + 1,
        )
        for x_val, lc in [(strike, TEXT_MUTED), (spot, colour)]:
            fig.add_shape(
                type="line",
                x0=x_val, x1=x_val, y0=0, y1=1,
                xref=xrefs[idx], yref=yrefs[idx] + " domain",
                line=dict(color=lc, dash="dot", width=0.8),
            )

    fig.update_layout(
        paper_bgcolor=BG_CHART,
        plot_bgcolor=BG_CHART,
        font=dict(family=FONT_MONO, size=10, color=TEXT_DIM),
        title=dict(
            text=f"Price &amp; Greeks vs Spot  ·  K={strike}  σ={vol_pct}%  r={rate_pct}%  T={time}y",
            font=dict(family=FONT_MONO, size=12, color=TEXT_DIM), x=0,
        ),
        height=540,
        margin=dict(t=60, b=30, l=40, r=20),
        showlegend=False,
    )
    _apply_subplot_theme(fig, 6)
    for ann in fig.layout.annotations:
        ann.font = dict(family=FONT_MONO, size=9, color=TEXT_MUTED)
        ann.update(font_color=TEXT_MUTED)

    st.plotly_chart(fig, use_container_width=True)

# ── Tab 4: IV Solver ───────────────────────────────────────────────────────
with tab_iv:
    st.markdown(f"""
    <div style="font-family:{FONT_MONO}; font-size:9px; text-transform:uppercase;
                letter-spacing:0.1em; color:{TEXT_MUTED}; margin-bottom:4px;">
      Implied Volatility Solver
    </div>
    <div style="font-family:{FONT_MONO}; font-size:10px; color:{TEXT_MUTED}; margin-bottom:14px;">
      Input an observed market price — IV is extracted numerically via Brent's method.
    </div>
    """, unsafe_allow_html=True)

    col_in, col_out = st.columns(2)
    with col_in:
        market_price = st.number_input(
            "Market option price ($)", min_value=0.001,
            value=float(round(price, 4)), step=0.01, format="%.4f",
        )
        use_sidebar = st.checkbox("Use sidebar inputs", value=True)
        if not use_sidebar:
            iv_spot     = st.number_input("Spot",     value=100.0, format="%.2f")
            iv_strike   = st.number_input("Strike",   value=100.0, format="%.2f")
            iv_vol_pct  = st.number_input("Vol (%)",  value=20,    step=1)
            iv_rate_pct = st.number_input("Rate (%)", value=5,     step=1)
            iv_time     = st.number_input("Time (y)", value=1.0,   format="%.4f")
            iv_otype    = st.radio("Type", ["call", "put"], horizontal=True, key="iv_type")
            iv_rate, iv_vol = iv_rate_pct / 100, iv_vol_pct / 100
        else:
            iv_spot, iv_strike, iv_vol, iv_rate, iv_time, iv_otype = \
                spot, strike, vol, rate, time, otype

    with col_out:
        try:
            solved_iv = implied_vol(market_price, iv_spot, iv_strike, iv_rate, iv_time, iv_otype)
            bs_check  = black_scholes_price(iv_spot, iv_strike, solved_iv, iv_rate, iv_time, iv_otype)
            residual  = abs(bs_check - market_price)

            st.metric("Implied volatility", f"{solved_iv:.4%}")
            st.metric("BS price check",     f"${bs_check:.4f}",
                      delta=f"residual {residual:.2e}", delta_color="off")

            price_up   = black_scholes_price(iv_spot, iv_strike, solved_iv + 0.01, iv_rate, iv_time, iv_otype)
            price_down = black_scholes_price(iv_spot, iv_strike, max(solved_iv - 0.01, 0.001), iv_rate, iv_time, iv_otype)
            st.markdown(f"""
            <div style="font-family:{FONT_MONO}; font-size:9px; color:{TEXT_MUTED};
                        margin-top:8px; padding:8px; border:1px solid {BORDER};">
              σ+1% → ${price_up:.4f} &nbsp;&nbsp;&nbsp; σ-1% → ${price_down:.4f}
            </div>
            """, unsafe_allow_html=True)

            strikes_smile = np.linspace(iv_spot * 0.75, iv_spot * 1.25, 40)
            smile_prices  = [black_scholes_price(iv_spot, float(k), solved_iv, iv_rate, iv_time, iv_otype)
                             for k in strikes_smile]
            smile_ivs = []
            for k, p in zip(strikes_smile, smile_prices):
                try:
                    smile_ivs.append(implied_vol(p, iv_spot, float(k), iv_rate, iv_time, iv_otype) * 100)
                except (IVSolverError, ValueError):
                    smile_ivs.append(None)

            fig_smile = go.Figure()
            fig_smile.add_trace(go.Scatter(
                x=strikes_smile, y=smile_ivs,
                line=dict(color=ACCENT_TEAL, width=1.8),
                showlegend=False,
            ))
            fig_smile.add_hline(
                y=solved_iv * 100,
                line=dict(color=TEXT_MUTED, dash="dash", width=1),
                annotation_text=f"Solved IV  {solved_iv:.1%}",
                annotation_font=dict(family=FONT_MONO, size=9, color=TEXT_MUTED),
            )
            fig_smile.add_vline(x=iv_spot,   line=dict(color=TEXT_MUTED, dash="dot", width=0.8))
            fig_smile.add_vline(x=iv_strike, line=dict(color=colour,     dash="dot", width=0.8))

            layout = _chart_base(height=240, title="Vol smile  (flat by construction in BSM)")
            layout["xaxis"]["title"] = "Strike ($)"
            layout["yaxis"]["title"] = "IV (%)"
            layout["showlegend"] = False
            layout["margin"] = dict(t=40, b=30, l=50, r=20)
            fig_smile.update_layout(**layout)
            st.plotly_chart(fig_smile, use_container_width=True)

        except (IVSolverError, ValueError) as e:
            st.error(f"IV solver: {e}")

# ── Tab 5: Live Market ─────────────────────────────────────────────────────
with tab_live:
    st.markdown(f"""
    <div style="font-family:{FONT_MONO}; font-size:9px; text-transform:uppercase;
                letter-spacing:0.1em; color:{TEXT_MUTED}; margin-bottom:4px;">
      Live IV Smile — Market Data
    </div>
    <div style="font-family:{FONT_MONO}; font-size:10px; color:{TEXT_MUTED}; margin-bottom:14px;">
      Real options chain via yfinance · IV solved on each strike · Mid-price convention
    </div>
    """, unsafe_allow_html=True)

    @st.cache_data(ttl=300, show_spinner="Fetching from Yahoo Finance...")
    def fetch_ticker_data(ticker: str):
        tk = yf.Ticker(ticker)
        return float(tk.fast_info["lastPrice"]), list(tk.options)

    @st.cache_data(ttl=300, show_spinner="Loading options chain...")
    def fetch_chain_data(ticker: str, expiry: str, option_type: str):
        tk    = yf.Ticker(ticker)
        chain = tk.option_chain(expiry)
        df    = chain.calls if option_type == "call" else chain.puts
        return df[["strike", "bid", "ask", "lastPrice", "impliedVolatility"]].copy()

    col_tc, col_lt = st.columns([1, 1])
    with col_tc:
        ticker_input = st.text_input("Ticker", value="AAPL").strip().upper()
    with col_lt:
        live_otype = st.radio("Option type", ["call", "put"], horizontal=True, key="live_type")

    try:
        live_spot, expiries = fetch_ticker_data(ticker_input)
        st.markdown(f"""
        <div style="font-family:{FONT_MONO}; font-size:10px; color:{TEXT_MUTED};
                    padding:6px 10px; border:1px solid {BORDER}; display:inline-block;
                    margin-bottom:10px;">
          SPOT &nbsp;<span style="color:{TEXT_PRIMARY}; font-weight:500;">${live_spot:.2f}</span>
          &nbsp;&nbsp;·&nbsp;&nbsp;
          {len(expiries)} expiries available
        </div>
        """, unsafe_allow_html=True)

        col_exp, col_rate = st.columns([1, 1])
        with col_exp:
            chosen_expiry = st.selectbox("Expiry", expiries)
        with col_rate:
            live_rate_pct = st.slider("Risk-free rate (%)", -2, 20, rate_pct, 1, key="live_rate")
            live_rate = live_rate_pct / 100.0

        T_live = max((datetime.date.fromisoformat(chosen_expiry) - datetime.date.today()).days, 1) / 365.0

        df = fetch_chain_data(ticker_input, chosen_expiry, live_otype)
        df = df[(df["bid"] > 0) & (df["ask"] > 0)].copy()
        df["mid"] = (df["bid"] + df["ask"]) / 2.0
        df = df[(df["strike"] >= live_spot * 0.60) & (df["strike"] <= live_spot * 1.40)]

        solved_strikes, solved_ivs = [], []
        for _, row in df.iterrows():
            try:
                iv = implied_vol(float(row["mid"]), live_spot, float(row["strike"]),
                                 live_rate, T_live, live_otype)
                solved_strikes.append(float(row["strike"]))
                solved_ivs.append(iv * 100)
            except (IVSolverError, ValueError):
                pass

        if solved_strikes:
            atm_idx    = min(range(len(solved_strikes)), key=lambda i: abs(solved_strikes[i] - live_spot))
            atm_iv_pct = solved_ivs[atm_idx]
            otm_ivs    = [iv for s, iv in zip(solved_strikes, solved_ivs) if s < live_spot * 0.95]
            call_ivs   = [iv for s, iv in zip(solved_strikes, solved_ivs) if s > live_spot * 1.05]
            skew       = (np.mean(otm_ivs) - atm_iv_pct) if otm_ivs else float("nan")
            clive      = CALL_BLUE if live_otype == "call" else PUT_RED

            chart_col, stats_col = st.columns([2, 1])
            with chart_col:
                fig_live = go.Figure()
                fig_live.add_trace(go.Scatter(
                    x=solved_strikes, y=solved_ivs, mode="lines+markers",
                    line=dict(color=clive, width=2),
                    marker=dict(size=4, color=clive, line=dict(width=0)),
                    name=f"Market IV  ({live_otype}s · mid)",
                ))
                fig_live.add_hline(
                    y=atm_iv_pct,
                    line=dict(color=TEXT_MUTED, dash="dash", width=1),
                    annotation_text=f"BS flat  {atm_iv_pct:.1f}%  (ATM)",
                    annotation_font=dict(family=FONT_MONO, size=9, color=TEXT_MUTED),
                )
                fig_live.add_vline(
                    x=live_spot,
                    line=dict(color=TEXT_DIM, dash="dot", width=1),
                    annotation_text=f"S  ${live_spot:.2f}",
                    annotation_font=dict(family=FONT_MONO, size=9, color=TEXT_DIM),
                )
                fig_live.add_trace(go.Scatter(
                    x=solved_strikes + list(reversed(solved_strikes)),
                    y=solved_ivs + [atm_iv_pct] * len(solved_ivs),
                    fill="toself", fillcolor=_rgba(clive, 0.07),
                    line=dict(color="rgba(0,0,0,0)"), name="Smile vs BSM",
                ))
                layout = _chart_base(
                    height=400,
                    title=f"{ticker_input}  IV smile vs flat BSM  ·  {chosen_expiry}  T={T_live:.3f}y",
                )
                layout["xaxis"]["title"] = "Strike ($)"
                layout["yaxis"]["title"] = "Implied vol (%)"
                layout["legend"]["x"] = 0.02
                layout["legend"]["y"] = 0.97
                fig_live.update_layout(**layout)
                st.plotly_chart(fig_live, use_container_width=True)

            with stats_col:
                st.markdown(f"""
                <div style="font-family:{FONT_MONO}; font-size:9px; text-transform:uppercase;
                            letter-spacing:0.1em; color:{TEXT_MUTED}; margin-bottom:10px;">
                  Market snapshot
                </div>
                """, unsafe_allow_html=True)
                st.metric("Live spot",          f"${live_spot:.2f}")
                st.metric("ATM IV",             f"{atm_iv_pct:.1f}%")
                st.metric("OTM put avg IV",     f"{np.mean(otm_ivs):.1f}%"  if otm_ivs  else "—")
                st.metric("OTM call avg IV",    f"{np.mean(call_ivs):.1f}%" if call_ivs else "—")
                st.metric("Put skew (OTM–ATM)", f"{skew:+.1f}%"             if not np.isnan(skew) else "—")
                st.markdown(f"""
                <div style="font-family:{FONT_MONO}; font-size:9px; color:{TEXT_MUTED};
                            margin-top:12px; padding-top:10px; border-top:1px solid {BORDER};
                            line-height:2;">
                  DTE &nbsp; {int(T_live*365)}<br>
                  Strikes solved &nbsp; {len(solved_strikes)}<br><br>
                  <span style="color:{_rgba(TEXT_MUTED, 0.7)};">
                  Gap between market smile and dashed line
                  is the vol smile — the real-world failure
                  of Black-Scholes.
                  </span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No IV solutions found for this expiry. Try a different one.")

    except Exception as e:
        st.error(f"Could not fetch '{ticker_input}': {e}")

    # ── News feed ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="font-family:{FONT_MONO};font-size:9px;text-transform:uppercase;
                letter-spacing:0.1em;color:{TEXT_MUTED};margin-top:28px;
                padding-top:14px;border-top:1px solid {BORDER};margin-bottom:10px;">
      News &amp; Sentiment — {ticker_input}
      <span style="font-weight:400;text-transform:none;letter-spacing:0;">
        &nbsp;· cached 60s · Finnhub + Marketaux
      </span>
    </div>
    """, unsafe_allow_html=True)

    finnhub_articles   = fetch_finnhub_news(ticker_input)
    marketaux_articles = fetch_marketaux_news(ticker_input)
    all_articles = finnhub_articles + marketaux_articles
    all_articles.sort(key=lambda x: x["ts"], reverse=True)

    if not os.environ.get("FINNHUB_KEY") and not os.environ.get("MARKETAUX_KEY"):
        st.markdown(f"""
        <div style="font-family:{FONT_MONO};font-size:10px;color:{TEXT_MUTED};
                    padding:10px 14px;border:1px solid {BORDER};border-radius:2px;">
          Set <code style="color:{TEXT_DIM};">FINNHUB_KEY</code> and/or
          <code style="color:{TEXT_DIM};">MARKETAUX_KEY</code> environment variables to enable news.
        </div>
        """, unsafe_allow_html=True)
    elif not all_articles:
        st.caption("No recent articles found for this ticker.")
    else:
        news_col, _ = st.columns([2, 1])
        with news_col:
            _render_news(all_articles[:15])

# ── Tab 6: Price Surface ───────────────────────────────────────────────────
with tab_surface:
    st.markdown(f"""
    <div style="font-family:{FONT_MONO}; font-size:9px; text-transform:uppercase;
                letter-spacing:0.1em; color:{TEXT_MUTED}; margin-bottom:4px;">
      Option Price Surface
    </div>
    <div style="font-family:{FONT_MONO}; font-size:10px; color:{TEXT_MUTED}; margin-bottom:14px;">
      Spot × Volatility joint sensitivity — K={strike}  r={rate_pct}%  T={time}y
    </div>
    """, unsafe_allow_html=True)

    surf_spots = np.linspace(strike * 0.60, strike * 1.40, 60)
    surf_vols  = np.linspace(0.05, 0.80, 60)
    surf_grid  = np.array([
        [black_scholes_price(float(s), strike, float(v), rate, time, otype)
         for s in surf_spots]
        for v in surf_vols
    ])

    # Custom colorscale: dark → accent colour
    if otype == "call":
        colorscale = [
            [0.0,  "#0A0A0A"],
            [0.25, "#1E3A6E"],
            [0.5,  "#1D4ED8"],
            [0.75, "#3B82F6"],
            [1.0,  "#93C5FD"],
        ]
    else:
        colorscale = [
            [0.0,  "#0A0A0A"],
            [0.25, "#6B0000"],
            [0.5,  "#B91C1C"],
            [0.75, "#EF4444"],
            [1.0,  "#FCA5A5"],
        ]

    fig_surf = go.Figure(data=go.Heatmap(
        x=surf_spots, y=surf_vols * 100, z=surf_grid,
        colorscale=colorscale,
        colorbar=dict(
            title=dict(text="Price ($)", font=dict(family=FONT_MONO, size=10, color=TEXT_MUTED)),
            tickfont=dict(family=FONT_MONO, size=9, color=TEXT_MUTED),
            bgcolor=BG_CHART,
            bordercolor=BORDER,
            borderwidth=1,
            thickness=12,
        ),
        hovertemplate=(
            "<span style='font-family:monospace'>"
            "S: $%{x:.1f}<br>σ: %{y:.1f}%<br>Price: $%{z:.4f}"
            "</span><extra></extra>"
        ),
    ))
    fig_surf.add_vline(
        x=strike, line=dict(color=TEXT_PRIMARY, dash="dash", width=1),
        annotation_text=f"K={strike}",
        annotation_font=dict(family=FONT_MONO, size=9, color=TEXT_PRIMARY),
    )
    fig_surf.add_vline(
        x=spot, line=dict(color=colour, dash="dot", width=1),
        annotation_text=f"S={spot}",
        annotation_font=dict(family=FONT_MONO, size=9, color=colour),
    )

    layout = _chart_base(
        height=500,
        title=f"European {otype.upper()} price surface  ·  K={strike}  r={rate_pct}%  T={time}y",
    )
    layout["xaxis"]["title"] = "Spot price ($)"
    layout["yaxis"]["title"] = "Volatility (%)"
    layout["showlegend"] = False
    fig_surf.update_layout(**layout)
    st.plotly_chart(fig_surf, use_container_width=True)
