"""DCF Valuation — QuantDesk page."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from dcf_fetcher import fetch_ticker_data
from dcf_engine import (
    DCFInputs,
    ValidationError,
    compute_wacc,
    run_dcf,
    sensitivity_table,
    sensitivity_table_exit_multiple,
)
from monte_carlo import MonteCarloInputs, run_simulation
from styles import (
    inject_css, build_sensitivity_html, section_header,
    _rgba, CALL_BLUE, TEXT_DIM, TEXT_MUTED, FONT_MONO, BORDER, TEXT_PRIMARY,
)
from dcf_utils import fmt_billions, fmt_currency, fmt_millions, fmt_pct
from dcf_visualization import (
    plot_ev_bridge,
    plot_fcff_waterfall,
    plot_football_field,
    plot_monte_carlo_histogram,
    plot_sensitivity_heatmap,
    plot_terminal_value_comparison,
)
from shared_sidebar import render_shared_sidebar

inject_css()

# ── Session state defaults ───────────────────────────────────────────────────
for k, v in {"wacc": 0.10, "valuation_run": False, "dcf_result": None, "dcf_inputs": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Sidebar ──────────────────────────────────────────────────────────────────
def render_sidebar() -> dict | None:
    """Render all sidebar inputs. Returns validated inputs dict or None if blocked."""
    with st.sidebar:
        render_shared_sidebar()

        st.markdown(
            f"<div style='font-family:{FONT_MONO};font-size:9px;text-transform:uppercase;"
            f"letter-spacing:0.08em;color:{TEXT_MUTED};margin-bottom:10px;'>"
            f"DCF Parameters</div>",
            unsafe_allow_html=True,
        )

        # ── Ticker fetch — reads ticker from shared session state ─────────
        st.markdown("---")
        st.markdown(
            f"<div style='font-family:{FONT_MONO};font-size:9px;text-transform:uppercase;"
            f"letter-spacing:0.08em;color:{TEXT_MUTED};margin-bottom:6px;'>Ticker Lookup</div>",
            unsafe_allow_html=True,
        )
        ticker_val = st.session_state.get("ticker", "AAPL")
        fetch_btn = st.button("Fetch Data", key="fetch_btn")

        fetched = {}
        if fetch_btn and ticker_val:
            with st.spinner("Fetching data\u2026"):
                fetched = fetch_ticker_data(ticker_val)
            if fetched.get("error"):
                st.warning(f"\u26a0\ufe0f {fetched['error']}")
            else:
                st.success(f"\u2713 {fetched['ticker']} loaded")
                st.session_state["fetched"] = fetched
        fetched = st.session_state.get("fetched", {})

        # ── Company inputs ────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**COMPANY BASICS**")

        default_revenue = fetched.get("revenue") or 1_000_000_000.0
        revenue = st.number_input(
            "Base Revenue ($)",
            min_value=1.0,
            max_value=1e12,
            value=float(default_revenue),
            step=1_000_000.0,
            format="%.0f",
        )
        if revenue <= 0:
            st.error("\u274c Revenue must be positive.")
            return None

        default_shares = fetched.get("shares_outstanding") or 100_000_000
        shares = st.number_input(
            "Shares Outstanding",
            min_value=1,
            max_value=int(1e12),
            value=int(default_shares),
            step=1_000_000,
        )
        if shares <= 0:
            st.error("\u274c Shares outstanding must be greater than zero.")
            return None

        default_price = fetched.get("current_price") or 50.0
        current_price = st.number_input(
            "Current Share Price ($)",
            min_value=0.01,
            max_value=1e6,
            value=float(default_price),
            step=0.01,
        )
        if current_price <= 0:
            st.error("\u274c Share price must be positive.")
            return None

        net_debt = st.number_input(
            "Net Debt ($)  [negative = net cash]",
            min_value=-1e12,
            max_value=1e12,
            value=float(fetched.get("net_debt") or 0.0),
            step=1_000_000.0,
            format="%.0f",
        )

        # ── Projection assumptions ────────────────────────────────────────
        st.markdown("---")
        st.markdown("**PROJECTION ASSUMPTIONS**")

        n_years = st.slider("Projection Years", min_value=3, max_value=10, value=5, step=1)

        st.markdown("*Annual Revenue Growth Rates*")
        growth_rates = []
        for i in range(n_years):
            g = st.number_input(
                f"Year {i+1} Growth (%)",
                min_value=-50.0,
                max_value=100.0,
                value=8.0 if i < 3 else 5.0,
                step=0.5,
                key=f"growth_{i}",
            )
            if g > 30:
                st.warning(f"\u26a0\ufe0f Year {i+1}: {g:.1f}% growth is unusually high \u2014 verify.")
            if g > 100 or g < -50:
                st.error(f"\u274c Year {i+1}: growth must be between -50% and 100%.")
                return None
            growth_rates.append(g / 100.0)

        ebitda_margin = st.slider(
            "EBITDA Margin (%)", min_value=-100.0, max_value=90.0, value=20.0, step=0.5
        )
        if ebitda_margin > 90:
            st.error("\u274c EBITDA margin > 90% is unrealistic.")
            return None
        if ebitda_margin < 0:
            st.warning("\u26a0\ufe0f Negative EBITDA \u2014 company is unprofitable. FCF may be negative.")

        da_pct = st.slider("D&A (% of Revenue)", min_value=0.0, max_value=50.0, value=5.0, step=0.5)
        if da_pct > 50:
            st.error("\u274c D&A > 50% of revenue is not allowed.")
            return None
        if da_pct == 0:
            st.warning("\u26a0\ufe0f No depreciation is unusual.")

        capex_pct = st.slider("CapEx (% of Revenue)", min_value=0.0, max_value=80.0, value=8.0, step=0.5)
        if capex_pct > 80:
            st.error("\u274c CapEx > 80% of revenue is not allowed.")
            return None
        if capex_pct < da_pct:
            st.warning("\u26a0\ufe0f CapEx < D&A \u2014 company may be underinvesting.")

        nwc_pct = st.slider("\u0394NWC (% of Revenue)", min_value=-30.0, max_value=30.0, value=2.0, step=0.5)
        if abs(nwc_pct) > 30:
            st.error("\u274c \u0394NWC outside \u00b130% range.")
            return None
        if nwc_pct < 0:
            st.warning("\u26a0\ufe0f Releasing working capital \u2014 is this sustainable?")

        tax_rate = st.slider("Tax Rate (%)", min_value=0.0, max_value=60.0, value=25.0, step=0.5)
        if tax_rate > 60 or tax_rate < 0:
            st.error("\u274c Tax rate must be between 0% and 60%.")
            return None
        if tax_rate == 0:
            st.warning("\u26a0\ufe0f 0% tax \u2014 verify jurisdiction.")

        # ── WACC inputs ───────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**WACC INPUTS**")

        rf = st.number_input("Risk-Free Rate (%)", min_value=0.0, max_value=20.0, value=4.5, step=0.1)
        if rf > 20:
            st.error("\u274c Risk-free rate > 20% blocked.")
            return None
        if rf > 10:
            st.warning("\u26a0\ufe0f Risk-free rate > 10% is unusually high.")

        default_beta = fetched.get("beta") or 1.0
        if fetched and fetched.get("beta") is None and fetched.get("ticker"):
            st.info("\u2139\ufe0f Beta not available \u2014 defaulting to 1.0. Adjust if needed.")
        beta = st.number_input("Beta", min_value=0.01, max_value=5.0, value=float(default_beta), step=0.05)
        if beta < 0 or beta > 5:
            st.error("\u274c Beta must be between 0 and 5.")
            return None
        if beta > 2.5:
            st.warning("\u26a0\ufe0f Very high systematic risk (\u03b2 > 2.5).")

        erp = st.number_input("Equity Risk Premium (%)", min_value=1.0, max_value=15.0, value=6.5, step=0.1)
        if erp < 1 or erp > 15:
            st.error("\u274c ERP must be between 1% and 15%.")
            return None

        cost_of_debt = st.number_input("Cost of Debt (%)", min_value=0.0, max_value=25.0, value=5.0, step=0.1)
        if cost_of_debt > 25:
            st.error("\u274c Cost of debt > 25% blocked.")
            return None
        if cost_of_debt > 15:
            st.warning("\u26a0\ufe0f Distressed-level cost of debt (> 15%).")

        debt_weight = st.slider("Debt Weight D/(D+E) (%)", min_value=0.0, max_value=95.0, value=30.0, step=1.0)
        if debt_weight > 95:
            st.error("\u274c D/V > 95% \u2014 equity is nearly wiped out.")
            return None

        wacc = compute_wacc(
            rf=rf / 100,
            beta=beta,
            erp=erp / 100,
            cost_of_debt=cost_of_debt / 100,
            tax_rate=tax_rate / 100,
            debt_weight=debt_weight / 100,
        )
        st.session_state["wacc"] = wacc

        if wacc < 0.03 or wacc > 0.25:
            st.warning(f"\u26a0\ufe0f WACC of {wacc:.2%} is unusual \u2014 double-check inputs.")

        st.markdown(
            f"<div style='background:{_rgba(CALL_BLUE, 0.08)};border:1px solid {_rgba(CALL_BLUE, 0.35)};"
            f"border-radius:2px;padding:10px;text-align:center;margin-top:8px'>"
            f"<span style='font-family:{FONT_MONO};color:{TEXT_MUTED};font-size:9px;"
            f"text-transform:uppercase;letter-spacing:0.1em'>Computed WACC</span><br>"
            f"<span style='font-family:{FONT_MONO};color:{CALL_BLUE};font-size:1.4rem;font-weight:700'>"
            f"{wacc:.2%}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # ── Terminal value inputs ─────────────────────────────────────────
        st.markdown("---")
        st.markdown("**TERMINAL VALUE**")

        use_perpetuity = st.radio(
            "Terminal Value Method",
            options=["Perpetuity Growth", "Exit Multiple"],
            index=0,
            horizontal=True,
        ) == "Perpetuity Growth"

        terminal_growth = st.number_input(
            "Terminal Growth Rate (%)", min_value=0.0, max_value=5.0, value=2.5, step=0.1
        )
        if terminal_growth > 5:
            st.error("\u274c Terminal growth > 5% exceeds long-run GDP growth.")
            return None
        if terminal_growth / 100 >= wacc:
            st.error(
                f"\u274c Terminal growth ({terminal_growth:.1f}%) must be strictly less than "
                f"WACC ({wacc:.2%}). Terminal value would be infinite or negative."
            )
            return None

        exit_multiple = st.number_input(
            "Exit EV/EBITDA Multiple", min_value=1.0, max_value=50.0, value=10.0, step=0.5
        )
        if exit_multiple < 1 or exit_multiple > 50:
            st.error("\u274c Exit multiple outside 1x\u201350x range.")
            return None
        if exit_multiple > 25:
            st.warning("\u26a0\ufe0f Very aggressive exit multiple (> 25x).")

        # ── Run button ────────────────────────────────────────────────────
        st.markdown("---")
        run_btn = st.button("\u25b6  RUN VALUATION", use_container_width=True, type="primary")

        params = {
            "revenue": revenue,
            "shares": shares,
            "current_price": current_price,
            "net_debt": net_debt,
            "n_years": n_years,
            "growth_rates": growth_rates,
            "ebitda_margin": ebitda_margin / 100,
            "da_pct": da_pct / 100,
            "capex_pct": capex_pct / 100,
            "nwc_pct": nwc_pct / 100,
            "tax_rate": tax_rate / 100,
            "rf": rf / 100,
            "beta": beta,
            "erp": erp / 100,
            "cost_of_debt": cost_of_debt / 100,
            "debt_weight": debt_weight / 100,
            "wacc": wacc,
            "terminal_growth": terminal_growth / 100,
            "exit_multiple": exit_multiple,
            "use_perpetuity": use_perpetuity,
            "run": run_btn,
            "ticker": fetched.get("ticker", ticker_val),
            "week52_high": fetched.get("week52_high"),
            "week52_low": fetched.get("week52_low"),
        }
        return params


# ── Tab renderers ─────────────────────────────────────────────────────────────

def render_tab_dcf(params: dict, result: dict) -> None:
    section_header("DCF MODEL", "Free Cash Flow to Firm \u2014 Projected Financials")

    df = result["df"]

    display_df = df.copy()
    for col in ["Revenue", "EBITDA", "D&A", "EBIT", "NOPAT", "CapEx", "\u0394NWC", "FCFF"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda v: fmt_currency(v))
    display_df["Year"] = display_df["Year"].apply(lambda y: f"Year {y}")
    st.dataframe(display_df.set_index("Year"), use_container_width=True)

    neg_years = df[df["FCFF"] < 0]["Year"].tolist()
    if neg_years:
        st.info(f"\u2139\ufe0f Negative free cash flow in years: {neg_years}. Valid but increases valuation risk.")

    st.plotly_chart(plot_fcff_waterfall(df), use_container_width=True)

    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    ev = result["ev"]
    equity = result["equity_value"]
    price = result["implied_price"]
    tv_pct = result["tv_pct_ev"]

    col1.metric("Enterprise Value", fmt_billions(ev))
    col2.metric("Equity Value", fmt_billions(equity))
    col3.metric("Implied Share Price", fmt_currency(price, 2))
    col4.metric("TV % of EV", fmt_pct(tv_pct))

    if tv_pct > 0.85:
        st.warning(f"\u26a0\ufe0f Terminal value represents {tv_pct:.0%} of EV \u2014 valuation heavily depends on long-term assumptions.")

    if equity < 0:
        st.error(f"\u274c Equity value is negative ({fmt_currency(equity, 0)}). Debt exceeds enterprise value.")

    upside = (price - params["current_price"]) / params["current_price"] if params["current_price"] > 0 else 0
    updown = "\u25b2" if upside >= 0 else "\u25bc"
    color = "green" if upside >= 0 else "red"
    st.markdown(
        f"<p style='text-align:center;font-size:1rem;font-family:{FONT_MONO}'>"
        f"Implied vs Current: <span style='color:{color};font-weight:700'>"
        f"{updown} {abs(upside):.1%}</span> "
        f"({fmt_currency(params['current_price'], 2)} \u2192 {fmt_currency(price, 2)})"
        f"</p>",
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        plot_ev_bridge(result["pv_fcfs"], result["pv_tv"], params["net_debt"]),
        use_container_width=True,
    )


def render_tab_wacc(params: dict) -> None:
    section_header("WACC CALCULATOR", "Weighted Average Cost of Capital \u2014 CAPM")

    rf = params["rf"]
    beta = params["beta"]
    erp = params["erp"]
    cd = params["cost_of_debt"]
    t = params["tax_rate"]
    dw = params["debt_weight"]
    ew = 1 - dw
    ce = rf + beta * erp
    wacc = params["wacc"]
    after_tax_cd = cd * (1 - t)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Cost of Equity (CAPM)")
        st.markdown(
            f"""
            | Component | Value |
            |---|---|
            | Risk-Free Rate (Rf) | {fmt_pct(rf)} |
            | Beta (\u03b2) | {beta:.2f} |
            | Equity Risk Premium (ERP) | {fmt_pct(erp)} |
            | **Cost of Equity = Rf + \u03b2 \u00d7 ERP** | **{fmt_pct(ce)}** |
            """
        )

    with col2:
        st.markdown("#### WACC Composition")
        st.markdown(
            f"""
            | Component | Weight | Rate | Contribution |
            |---|---|---|---|
            | Equity | {fmt_pct(ew)} | {fmt_pct(ce)} | {fmt_pct(ew * ce)} |
            | Debt (after-tax) | {fmt_pct(dw)} | {fmt_pct(after_tax_cd)} | {fmt_pct(dw * after_tax_cd)} |
            | **WACC** | **100%** | | **{fmt_pct(wacc)}** |
            """
        )

    st.markdown("---")
    st.markdown(
        f"<div style='background:{_rgba(CALL_BLUE, 0.08)};border:1px solid {_rgba(CALL_BLUE, 0.35)};"
        f"border-radius:2px;padding:20px;text-align:center'>"
        f"<p style='font-family:{FONT_MONO};color:{TEXT_MUTED};font-size:9px;"
        f"text-transform:uppercase;letter-spacing:0.12em;margin:0'>WEIGHTED AVERAGE COST OF CAPITAL</p>"
        f"<p style='font-family:{FONT_MONO};color:{CALL_BLUE};font-size:2.5rem;font-weight:700;margin:8px 0'>"
        f"{fmt_pct(wacc)}</p>"
        f"<p style='font-family:{FONT_MONO};color:{TEXT_DIM};font-size:9px;margin:0'>"
        f"Ce = {fmt_pct(rf)} + {beta:.2f} \u00d7 {fmt_pct(erp)} = {fmt_pct(ce)}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if wacc < 0.03 or wacc > 0.25:
        st.warning(f"\u26a0\ufe0f WACC of {fmt_pct(wacc)} is unusual \u2014 double-check inputs.")


def render_tab_tv(params: dict, result: dict) -> None:
    section_header("TERMINAL VALUE", "Perpetuity Growth vs Exit Multiple")

    df = result["df"]
    fcf_n = float(df["FCFF"].iloc[-1])
    ebitda_n = float(df["EBITDA"].iloc[-1])
    wacc = params["wacc"]
    g = params["terminal_growth"]
    multiple = params["exit_multiple"]
    n = params["n_years"]

    try:
        from dcf_engine import terminal_value_perpetuity, terminal_value_exit
        tv_perp = terminal_value_perpetuity(fcf_n, g, wacc)
        pv_perp = tv_perp / (1 + wacc) ** n
    except ValueError:
        tv_perp = float("nan")
        pv_perp = float("nan")

    tv_exit = ebitda_n * multiple
    pv_exit = tv_exit / (1 + wacc) ** n

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Perpetuity Growth Method")
        st.markdown(
            f"""
            | Item | Value |
            |---|---|
            | Final Year FCF (Year {n}) | {fmt_currency(fcf_n, 0)} |
            | Terminal Growth Rate (g) | {fmt_pct(g)} |
            | WACC | {fmt_pct(wacc)} |
            | Terminal Value = FCF \u00d7 (1+g) / (WACC-g) | **{fmt_billions(tv_perp) if not np.isnan(tv_perp) else 'N/A'}** |
            | PV of Terminal Value | **{fmt_billions(pv_perp) if not np.isnan(pv_perp) else 'N/A'}** |
            """
        )

    with col2:
        st.markdown("#### Exit Multiple Method")
        st.markdown(
            f"""
            | Item | Value |
            |---|---|
            | Final Year EBITDA (Year {n}) | {fmt_currency(ebitda_n, 0)} |
            | EV/EBITDA Exit Multiple | {multiple:.1f}x |
            | Terminal Value = EBITDA \u00d7 Multiple | **{fmt_billions(tv_exit)}** |
            | PV of Terminal Value | **{fmt_billions(pv_exit)}** |
            """
        )

    active = "Perpetuity Growth" if params["use_perpetuity"] else "Exit Multiple"
    st.info(f"\u2139\ufe0f Currently using: **{active}** method in the DCF model.")

    if not np.isnan(pv_perp) and not np.isnan(pv_exit):
        st.plotly_chart(
            plot_terminal_value_comparison(pv_perp, pv_exit),
            use_container_width=True,
        )

    active_pv_tv = result["pv_tv"]
    ev = result["ev"]
    tv_pct = active_pv_tv / ev if ev else 0
    st.metric("Active Terminal Value (PV)", fmt_billions(active_pv_tv), f"{tv_pct:.0%} of EV")
    if tv_pct > 0.85:
        st.warning(f"\u26a0\ufe0f Terminal value is {tv_pct:.0%} of EV \u2014 heavily sensitive to long-term assumptions.")


def render_tab_sensitivity(params: dict, result: dict) -> None:
    section_header("SENSITIVITY TABLE", "Implied Share Price \u2014 WACC \u00d7 Terminal Growth / Exit Multiple")

    wacc_base = params["wacc"]
    tg_base = params["terminal_growth"]
    n_steps = 5

    sens_mode = st.radio(
        "Sensitivity axes",
        ["WACC \u00d7 Terminal Growth Rate", "WACC \u00d7 Exit Multiple"],
        horizontal=True,
    )

    st.markdown(
        f"<p style='font-family:{FONT_MONO};font-size:9px;color:{TEXT_DIM}'>"
        f"\U0001f7e2 Green = above current price  "
        f"\U0001f534 Red = below current price  \u2b1b Highlighted = current assumption</p>",
        unsafe_allow_html=True,
    )

    wacc_range = [wacc_base + (i - n_steps // 2) * 0.01 for i in range(n_steps)]
    wacc_range = [max(0.03, w) for w in wacc_range]

    dcf_inputs = DCFInputs(
        base_revenue=params["revenue"],
        growth_rates=params["growth_rates"],
        ebitda_margin=params["ebitda_margin"],
        da_pct=params["da_pct"],
        capex_pct=params["capex_pct"],
        nwc_pct=params["nwc_pct"],
        tax_rate=params["tax_rate"],
        wacc=wacc_base,
        terminal_growth=tg_base,
        exit_multiple=params["exit_multiple"],
        use_perpetuity=params["use_perpetuity"],
        net_debt=params["net_debt"],
        shares=params["shares"],
        current_price=params["current_price"],
    )

    if sens_mode == "WACC \u00d7 Terminal Growth Rate":
        tg_range = [tg_base + (i - n_steps // 2) * 0.005 for i in range(n_steps)]
        tg_range = [max(0.0, min(0.049, g)) for g in tg_range]
        tg_range = [g for g in tg_range if g < min(wacc_range)]

        if not tg_range:
            st.warning("\u26a0\ufe0f Cannot generate sensitivity table \u2014 all terminal growth values exceed WACC.")
            return

        with st.spinner("Building sensitivity table\u2026"):
            table = sensitivity_table(dcf_inputs, wacc_range, tg_range)

        html = build_sensitivity_html(
            table, params["current_price"], wacc_base, tg_base,
            row_label="g", col_label="WACC"
        )
        st.markdown(html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        try:
            fig = plot_sensitivity_heatmap(table, params["current_price"])
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"\u26a0\ufe0f Chart could not render. Showing table only. ({e})")

    else:
        multiple_range = [max(1.0, params["exit_multiple"] + (i - n_steps // 2) * 2.0) for i in range(n_steps)]
        with st.spinner("Building sensitivity table\u2026"):
            table = sensitivity_table_exit_multiple(dcf_inputs, wacc_range, multiple_range)

        html = build_sensitivity_html(
            table, params["current_price"], wacc_base, tg_base,
            row_label="Exit Multiple", col_label="WACC"
        )
        st.markdown(html, unsafe_allow_html=True)


def render_tab_football(params: dict, result: dict) -> None:
    section_header("FOOTBALL FIELD", "Valuation Range Summary \u2014 Investment Banking Style")

    wacc_base = params["wacc"]
    dcf_inputs_low = DCFInputs(
        base_revenue=params["revenue"],
        growth_rates=params["growth_rates"],
        ebitda_margin=params["ebitda_margin"],
        da_pct=params["da_pct"],
        capex_pct=params["capex_pct"],
        nwc_pct=params["nwc_pct"],
        tax_rate=params["tax_rate"],
        wacc=max(0.03, wacc_base - 0.01),
        terminal_growth=params["terminal_growth"],
        exit_multiple=params["exit_multiple"],
        use_perpetuity=params["use_perpetuity"],
        net_debt=params["net_debt"],
        shares=params["shares"],
        current_price=params["current_price"],
    )
    dcf_inputs_high = DCFInputs(
        base_revenue=params["revenue"],
        growth_rates=params["growth_rates"],
        ebitda_margin=params["ebitda_margin"],
        da_pct=params["da_pct"],
        capex_pct=params["capex_pct"],
        nwc_pct=params["nwc_pct"],
        tax_rate=params["tax_rate"],
        wacc=min(0.30, wacc_base + 0.01),
        terminal_growth=params["terminal_growth"],
        exit_multiple=params["exit_multiple"],
        use_perpetuity=params["use_perpetuity"],
        net_debt=params["net_debt"],
        shares=params["shares"],
        current_price=params["current_price"],
    )

    ranges = []

    try:
        res_low = run_dcf(dcf_inputs_low)
        res_high = run_dcf(dcf_inputs_high)
        dcf_low = min(res_low["implied_price"], res_high["implied_price"])
        dcf_high = max(res_low["implied_price"], res_high["implied_price"])
        if dcf_low < dcf_high:
            ranges.append({"label": "DCF (WACC \u00b11%)", "low": dcf_low, "high": dcf_high})
    except Exception:
        pass

    st.markdown("---")
    st.markdown("**Comparable Companies (EV/EBITDA)**")
    cc1, cc2 = st.columns(2)
    comps_low = cc1.number_input("Comps Low Multiple", 1.0, 50.0, 8.0, 0.5)
    comps_high = cc2.number_input("Comps High Multiple", 1.0, 50.0, 14.0, 0.5)
    ebitda_n = float(result["df"]["EBITDA"].iloc[-1])
    net_debt = params["net_debt"]
    shares = params["shares"]
    if ebitda_n > 0 and shares > 0:
        comps_ev_low = ebitda_n * comps_low
        comps_ev_high = ebitda_n * comps_high
        comps_price_low = (comps_ev_low - net_debt) / shares
        comps_price_high = (comps_ev_high - net_debt) / shares
        if comps_price_low < comps_price_high:
            ranges.append({"label": "Comparable Companies", "low": comps_price_low, "high": comps_price_high})

    st.markdown("**Precedent Transactions (EV/EBITDA)**")
    pt1, pt2 = st.columns(2)
    prec_low = pt1.number_input("Precedents Low Multiple", 1.0, 50.0, 10.0, 0.5)
    prec_high = pt2.number_input("Precedents High Multiple", 1.0, 50.0, 18.0, 0.5)
    if ebitda_n > 0 and shares > 0:
        prec_ev_low = ebitda_n * prec_low
        prec_ev_high = ebitda_n * prec_high
        prec_price_low = (prec_ev_low - net_debt) / shares
        prec_price_high = (prec_ev_high - net_debt) / shares
        if prec_price_low < prec_price_high:
            ranges.append({"label": "Precedent Transactions", "low": prec_price_low, "high": prec_price_high})

    w52_high = params.get("week52_high")
    w52_low = params.get("week52_low")
    if w52_high and w52_low and w52_low < w52_high:
        ranges.append({"label": "52-Week Price Range", "low": w52_low, "high": w52_high})
    elif not (w52_high and w52_low):
        st.info("\u2139\ufe0f 52-week price range not available \u2014 enter a ticker and fetch data.")

    if not ranges:
        st.warning("\u26a0\ufe0f No valuation ranges available. Run a valuation first.")
        return

    try:
        fig = plot_football_field(ranges, params["current_price"])
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"\u26a0\ufe0f Chart could not render. ({e})")
        for r in ranges:
            st.write(f"**{r['label']}**: ${r['low']:,.2f} \u2013 ${r['high']:,.2f}")


def render_tab_monte_carlo(params: dict) -> None:
    section_header("MONTE CARLO SIMULATION", "Probabilistic Valuation \u2014 10,000 Simulations")

    n_sims = st.slider(
        "Number of Simulations",
        min_value=1_000,
        max_value=50_000,
        value=10_000,
        step=1_000,
    )
    if n_sims > 25_000:
        st.warning("\u26a0\ufe0f > 25,000 simulations may be slow.")

    run_mc = st.button("\u25b6  RUN MONTE CARLO", type="primary")
    if not run_mc:
        st.info("\u2139\ufe0f Configure parameters in the sidebar and click 'Run Monte Carlo' to simulate.")
        return

    mc_inputs = MonteCarloInputs(
        base_revenue=params["revenue"],
        growth_rate=params["growth_rates"][0] if params["growth_rates"] else 0.05,
        ebitda_margin=params["ebitda_margin"],
        da_pct=params["da_pct"],
        capex_pct=params["capex_pct"],
        nwc_pct=params["nwc_pct"],
        tax_rate=params["tax_rate"],
        wacc=params["wacc"],
        terminal_growth=params["terminal_growth"],
        exit_multiple=params["exit_multiple"],
        use_perpetuity=params["use_perpetuity"],
        net_debt=params["net_debt"],
        shares=params["shares"],
        current_price=params["current_price"],
        n_years=params["n_years"],
    )

    with st.spinner(f"Running {n_sims:,} simulations\u2026"):
        try:
            mc = run_simulation(mc_inputs, n_sims=n_sims)
        except Exception as e:
            st.error(f"\u274c Simulation failed: {e}")
            return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mean Price", fmt_currency(mc.mean, 2))
    col2.metric("Median Price", fmt_currency(mc.median, 2))
    col3.metric("Std Deviation", fmt_currency(mc.std, 2))
    col4.metric("Prob. of Upside", fmt_pct(mc.prob_upside))

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("P10 (Bear)", fmt_currency(mc.p10, 2))
    col6.metric("P25", fmt_currency(mc.p25, 2))
    col7.metric("P75", fmt_currency(mc.p75, 2))
    col8.metric("P90 (Bull)", fmt_currency(mc.p90, 2))

    st.metric("Value at Risk (5th pctile)", fmt_currency(mc.var5, 2))

    try:
        fig = plot_monte_carlo_histogram(
            mc.prices, mc.p10, mc.p25, mc.p50, mc.p75, mc.p90, params["current_price"]
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"\u26a0\ufe0f Histogram could not render. ({e})")

    percentile_df = pd.DataFrame({
        "Percentile": ["P10", "P25", "P50 (Median)", "P75", "P90"],
        "Implied Price": [
            fmt_currency(mc.p10, 2),
            fmt_currency(mc.p25, 2),
            fmt_currency(mc.p50, 2),
            fmt_currency(mc.p75, 2),
            fmt_currency(mc.p90, 2),
        ],
    })
    st.dataframe(percentile_df.set_index("Percentile"), use_container_width=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.markdown(
        f"<div style='text-align:center;font-family:{FONT_MONO};font-size:18px;"
        f"letter-spacing:0.1em;text-transform:uppercase;color:{TEXT_PRIMARY};"
        f"margin-bottom:0;padding:12px 0 8px 0;border-bottom:1px solid {BORDER};'>"
        f"DCF Valuation</div>"
        f"<div style='text-align:center;font-family:{FONT_MONO};font-size:9px;"
        f"color:{TEXT_MUTED};letter-spacing:0.15em;margin-top:4px;'>"
        f"DISCOUNTED CASH FLOW &nbsp;\u00b7&nbsp; WACC &nbsp;\u00b7&nbsp; TERMINAL VALUE &nbsp;\u00b7&nbsp; MONTE CARLO</div>",
        unsafe_allow_html=True,
    )

    params = render_sidebar()

    if params is None:
        st.stop()

    if params["run"]:
        with st.spinner("Running DCF model\u2026"):
            try:
                dcf_inputs = DCFInputs(
                    base_revenue=params["revenue"],
                    growth_rates=params["growth_rates"],
                    ebitda_margin=params["ebitda_margin"],
                    da_pct=params["da_pct"],
                    capex_pct=params["capex_pct"],
                    nwc_pct=params["nwc_pct"],
                    tax_rate=params["tax_rate"],
                    wacc=params["wacc"],
                    terminal_growth=params["terminal_growth"],
                    exit_multiple=params["exit_multiple"],
                    use_perpetuity=params["use_perpetuity"],
                    net_debt=params["net_debt"],
                    shares=params["shares"],
                    current_price=params["current_price"],
                )
                result = run_dcf(dcf_inputs)

                if np.isnan(result["ev"]) or np.isinf(result["ev"]):
                    st.error("\u274c Calculation produced invalid results. Check your inputs.")
                    st.stop()
                if abs(result["ev"]) > 1e15:
                    st.warning("\u26a0\ufe0f Enterprise value exceeds $1 quadrillion \u2014 inputs may be unrealistic.")

                st.session_state["dcf_result"] = result
                st.session_state["dcf_inputs"] = dcf_inputs
                st.session_state["valuation_run"] = True
                st.session_state["last_params"] = params

            except ValueError as e:
                st.error(f"\u274c {e}")
                st.stop()
            except Exception as e:
                st.error(f"\u274c Unexpected error: {e}")
                st.stop()

    if not st.session_state["valuation_run"]:
        st.info("\u2139\ufe0f Configure parameters in the sidebar and click **\u25b6 RUN VALUATION** to see results.")
        st.stop()

    result = st.session_state["dcf_result"]
    saved_params = st.session_state.get("last_params", params)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "\U0001f4ca DCF Model",
        "\u2696\ufe0f WACC Calculator",
        "\U0001f52d Terminal Value",
        "\U0001f5c2\ufe0f Sensitivity Table",
        "\U0001f3c8 Football Field",
        "\U0001f3b2 Monte Carlo",
    ])

    with tab1:
        try:
            render_tab_dcf(saved_params, result)
        except Exception as e:
            st.error(f"\u274c {e}")

    with tab2:
        try:
            render_tab_wacc(saved_params)
        except Exception as e:
            st.error(f"\u274c {e}")

    with tab3:
        try:
            render_tab_tv(saved_params, result)
        except Exception as e:
            st.error(f"\u274c {e}")

    with tab4:
        try:
            render_tab_sensitivity(saved_params, result)
        except Exception as e:
            st.error(f"\u274c {e}")

    with tab5:
        try:
            render_tab_football(saved_params, result)
        except Exception as e:
            st.error(f"\u274c {e}")

    with tab6:
        try:
            render_tab_monte_carlo(saved_params)
        except Exception as e:
            st.error(f"\u274c {e}")


main()
