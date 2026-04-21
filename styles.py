"""Shared Bloomberg terminal CSS, colour palette, and helpers for QuantDesk."""

import streamlit as st

# ---------------------------------------------------------------------------
# Colour palette — Bloomberg dark terminal
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


def inject_css() -> None:
    """Inject global Bloomberg dark terminal CSS across all QuantDesk pages."""
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

  /* ── Buttons ── */
  .stButton > button {{
    background-color: {_rgba(CALL_BLUE, 0.08)};
    color: {CALL_BLUE};
    border: 1px solid {_rgba(CALL_BLUE, 0.4)};
    border-radius: 2px;
    font-family: {FONT_MONO};
    font-size: 10px;
    letter-spacing: 0.08em;
    font-weight: 600;
    padding: 0.5rem 1.5rem;
    transition: all 0.15s ease;
    text-transform: uppercase;
  }}
  .stButton > button:hover {{
    background-color: {CALL_BLUE};
    color: {BG_PAGE};
  }}

  /* ── Header band (Options Pricer) ── */
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

  /* ── DCF sensitivity table ── */
  .sensitivity-table {{
    font-family: {FONT_MONO};
    font-size: 0.78rem;
    border-collapse: collapse;
    width: 100%;
  }}
  .sensitivity-table th {{
    background-color: {_rgba(CALL_BLUE, 0.12)};
    color: {TEXT_DIM};
    padding: 6px 10px;
    text-align: center;
    border: 1px solid {BORDER};
    letter-spacing: 0.06em;
  }}
  .sensitivity-table td {{
    padding: 5px 10px;
    text-align: center;
    border: 1px solid {BORDER};
    font-weight: 400;
  }}
  .sensitivity-table td.highlight {{
    border: 2px solid {CALL_BLUE} !important;
    font-weight: 700;
  }}
  .sensitivity-table tr:hover td {{
    filter: brightness(1.1);
  }}
</style>
""", unsafe_allow_html=True)


def section_header(title: str, subtitle: str = "") -> None:
    """Render a styled section header in Bloomberg monospace style."""
    st.markdown(
        f"<div style='font-family:{FONT_MONO};font-size:11px;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:0.12em;color:{TEXT_PRIMARY};"
        f"padding-bottom:6px;border-bottom:1px solid {BORDER};margin-bottom:12px;'>"
        f"{title}</div>",
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(
            f"<div style='font-family:{FONT_MONO};font-size:9px;color:{TEXT_MUTED};"
            f"letter-spacing:0.04em;margin-bottom:10px;'>{subtitle}</div>",
            unsafe_allow_html=True,
        )


def build_sensitivity_html(
    df,
    current_price: float,
    base_wacc: float,
    base_tg: float,
    row_label: str = "Terminal Growth",
    col_label: str = "WACC",
) -> str:
    """Build a color-coded HTML sensitivity table."""
    import math

    def cell_color(price: float):
        if math.isnan(price):
            return "#111111", "#4B5563"
        if current_price <= 0:
            return "#111111", "#E8E8E8"
        ratio = price / current_price
        if ratio >= 1.2:
            bg, fg = "#0D3320", "#4AE88A"
        elif ratio >= 1.05:
            bg, fg = "#0D2818", "#2ECC71"
        elif ratio >= 0.95:
            bg, fg = "#111111", "#E8E8E8"
        elif ratio >= 0.8:
            bg, fg = "#2E1010", "#E05555"
        else:
            bg, fg = "#3A0A0A", "#FF4444"
        return bg, fg

    rows = list(df.index)
    cols = list(df.columns)

    html = ['<table class="sensitivity-table">']
    html.append("<thead><tr>")
    html.append(f"<th>{row_label} \\ {col_label}</th>")
    for c in cols:
        html.append(f"<th>{c:.1%}</th>")
    html.append("</tr></thead><tbody>")
    for r in rows:
        html.append("<tr>")
        html.append(f"<th>{r:.1%}</th>")
        for c in cols:
            price = df.loc[r, c]
            bg, fg = cell_color(price)
            is_highlight = abs(r - base_tg) < 1e-6 and abs(c - base_wacc) < 1e-6
            cls = ' class="highlight"' if is_highlight else ""
            cell_text = "N/A" if math.isnan(price) else f"${price:,.2f}"
            html.append(f'<td{cls} style="background-color:{bg};color:{fg}">{cell_text}</td>')
        html.append("</tr>")
    html.append("</tbody></table>")
    return "\n".join(html)
