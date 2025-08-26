import os
import json
import sqlite3
from datetime import date, datetime
from typing import Dict, Any, Optional

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

from utils.storage import Storage, ensure_settings
from utils.reporting import (
    compute_closed_pnl, compute_open_pnl,
    monthly_summary, currency_totals, best_trades, goal_progress, days_held_col, roi_col
)
from utils.llm import get_trade_insights
from utils.ui import (
    app_header, sidebar_nav, currency_badge, show_toast,
    market_to_currency_default, sectors_list, trade_types_list
)
from utils.github_sync import maybe_sync_csv_to_github

st.set_page_config(page_title="Trading Journal", layout="wide", page_icon="📈")

# -------------------- AUTH (simplified) --------------------
def check_auth() -> bool:
    cfg_user = st.secrets.get("auth", {}).get("username", "demo")
    cfg_pwd  = st.secrets.get("auth", {}).get("password", "demo")
    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False
    if not st.session_state.auth_ok:
        with st.sidebar:
            st.markdown("### Login")
            u = st.text_input("Username", value="", key="auth_user")
            p = st.text_input("Password", value="", key="auth_pwd", type="password")
            if st.button("Sign in", type="primary", use_container_width=True):
                if u == cfg_user and p == cfg_pwd:
                    st.session_state.auth_ok = True
                    st.session_state.user = u
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        return False
    return True

if not check_auth():
    st.stop()

# -------------------- Init storage & settings --------------------
backend_default = "sqlite"
storage = Storage(backend=os.environ.get("JOURNAL_BACKEND", backend_default))
settings = ensure_settings(storage)

# -------------------- UI Header --------------------
app_header("My Trade Journal")

# -------------------- Sidebar Navigation --------------------
page = sidebar_nav()

# -------------------- Helper: load trades df --------------------
def load_trades_df() -> pd.DataFrame:
    df = storage.read_trades()
    if df.empty:
        # enforce dtypes/columns
        cols = ["id","user","market","symbol","currency","sector","trade_type",
                "entry_date","exit_date","qty","entry_price","exit_price",
                "capital_invested","sl","target","notes","created_at","updated_at"]
        return pd.DataFrame(columns=cols)
    return df

# -------------------- Page: Record Trade --------------------
if page == "Record Trade":
    with st.container(border=True):
        st.subheader("➕ Record a Trade")
        c1, c2, c3 = st.columns(3)
        with c1:
            market = st.selectbox("Market", ["India","US","Australia"], index=2)
            symbol = st.text_input("Stock/ETF Symbol", value="", placeholder="e.g., INFY, AAPL, BHP")
            sector = st.selectbox("Sector", sectors_list())
            trade_type = st.selectbox("Trade Type", trade_types_list(), index=0)
        with c2:
            entry_date = st.date_input("Entry Date", value=date.today())
            exit_date  = st.date_input("Exit Date (optional)", value=None, format="YYYY-MM-DD", key="exit_date_input")
            qty = st.number_input("Quantity", min_value=0, step=1, value=0)
            entry_price = st.number_input("Entry Price", min_value=0.0, format="%.4f")
        with c3:
            exit_price = st.number_input("Exit Price (optional)", min_value=0.0, format="%.4f")
            capital_invested = st.number_input("Capital Invested (optional)", min_value=0.0, format="%.2f")
            # Currency defaults from market; allow override
            default_ccy = market_to_currency_default(market)
            currency = st.selectbox("Trade Currency", ["INR","USD","AUD"], index=["INR","USD","AUD"].index(default_ccy))
        c4, c5, c6 = st.columns(3)
        with c4:
            sl = st.number_input("Planned Stop-loss (price, optional)", min_value=0.0, format="%.4f")
        with c5:
            target = st.number_input("Planned Target (price, optional)", min_value=0.0, format="%.4f")
        with c6:
            notes = st.text_area("Notes (optional)", placeholder="Catalyst, thesis, playbook, etc.")

        if st.button("Save Trade", type="primary", use_container_width=True):
            user = st.session_state.get("user", "local")
            payload = {
                "user": user, "market": market, "symbol": symbol.strip().upper(),
                "currency": currency, "sector": sector, "trade_type": trade_type,
                "entry_date": str(entry_date),
                "exit_date": str(exit_date) if exit_date else None,
                "qty": int(qty), "entry_price": float(entry_price) if entry_price else None,
                "exit_price": float(exit_price) if exit_price else None,
                "capital_invested": float(capital_invested) if capital_invested else None,
                "sl": float(sl) if sl else None, "target": float(target) if target else None,
                "notes": notes.strip() if notes else None
            }
            storage.insert_trade(payload)
            maybe_sync_csv_to_github(storage)  # if CSV backend & secrets provided
            show_toast("Trade saved ✅")
            st.rerun()

    # AI Insights panel
    with st.container(border=True):
        st.subheader("🤖 AI Insights (optional)")
        st.caption("Provide a planned trade to get suggested SL/targets & sentiment. Requires OpenAI key in secrets or environment; else uses rule-based fallback.")
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            mkt_ai = st.selectbox("Market (AI)", ["India","US","Australia"])
            sym_ai = st.text_input("Symbol (AI)", placeholder="e.g., INFY / AAPL / BHP")
        with cc2:
            entry_ai = st.number_input("Planned Entry (AI)", min_value=0.0, format="%.4f")
            type_ai = st.selectbox("Bias", ["Swing Long","Swing Short"])
        with cc3:
            risk_perc = st.slider("Baseline Risk %", 0.2, 3.0, 1.0, 0.1, help="Used by the heuristic when LLM is unavailable.")
        if st.button("Get AI Suggestion"):
            ai_text = get_trade_insights(mkt_ai, sym_ai, entry_ai, type_ai, baseline_risk_pct=risk_perc)
            st.markdown(ai_text)

# -------------------- Page: Monthly Report --------------------
elif page == "Monthly Report":
    st.subheader("📊 Dashboard & Monthly Report")
    df = load_trades_df()
    if df.empty:
        st.info("No trades yet. Record trades to see reports.")
    else:
        # derived fields
        df["entry_date"] = pd.to_datetime(df["entry_date"], errors="coerce")
        df["exit_date"]  = pd.to_datetime(df["exit_date"], errors="coerce")
        df["days_held"]  = days_held_col(df)
        df["roi_pct"]    = roi_col(df)

        # filters
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            month_opts = sorted(df["entry_date"].dropna().dt.to_period("M").unique().astype(str))
            sel_month = st.selectbox("Month (by entry)", month_opts, index=len(month_opts)-1 if month_opts else 0)
        with col2:
            rep_ccy = st.selectbox("Reporting Currency (base)", ["AUD","USD","INR"], index=["AUD","USD","INR"].index(settings["base_currency"]))
        with col3:
            show_open = st.checkbox("Include open trades (est. P&L)", value=True)
        with col4:
            goal_by_ccy = st.selectbox("Goal currency for progress", ["AUD","USD","INR"], index=0)

        # compute
        month_mask = df["entry_date"].dt.to_period("M").astype(str) == sel_month
        mdf = df.loc[month_mask].copy()
        closed_pnl = compute_closed_pnl(mdf)
        open_pnl   = compute_open_pnl(mdf) if show_open else 0.0

        # currency totals
        totals_native = currency_totals(mdf)
        progress = goal_progress(mdf, goal_by_ccy, settings)

        # top row metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Closed P&L (native currencies sum)", f"{closed_pnl:,.2f}")
        m2.metric("Open P&L (est.)", f"{open_pnl:,.2f}")
        m3.metric(f"Goal Progress ({goal_by_ccy})", f"{progress['progress_pct']:.1f}%",
                  help=f"Goal {progress['goal']} {goal_by_ccy}; Achieved {progress['achieved']} {goal_by_ccy}")
        m4.metric("Best Trade (ROI%)", f"{best_trades(mdf).get('best_roi_pct','N/A')}")

        st.divider()
        cA, cB = st.columns([1.2, 1.0])
        with cA:
            # By currency pie or bar
            cur_df = pd.DataFrame([{"currency":k, "pnl":v} for k,v in totals_native.items()])
            fig = px.bar(cur_df, x="currency", y="pnl", title="P&L by Currency (native)", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

        with cB:
            # Trades by month count
            df["ym"] = df["entry_date"].dt.to_period("M").astype(str)
            cnt = df.groupby("ym")["id"].count().reset_index().rename(columns={"id":"trades"})
            fig2 = px.line(cnt, x="ym", y="trades", markers=True, title="Trades per Month")
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Trades (this month)")
        st.dataframe(mdf.sort_values("entry_date", ascending=False), use_container_width=True, hide_index=True)

# -------------------- Page: Settings --------------------
elif page == "Settings":
    st.subheader("⚙️ Settings")
    # Backend
    be = st.selectbox("Storage backend", ["sqlite","csv"], index=["sqlite","csv"].index(storage.backend))
    if st.button("Switch Backend"):
        storage.backend = be
        storage.save_backend_choice(be)
        st.success(f"Backend switched to {be}.")
        st.rerun()

    # Base currency
    bc = st.selectbox("Base currency for reporting", ["AUD","USD","INR"],
                      index=["AUD","USD","INR"].index(settings["base_currency"]))
    # FX to base mapping
    st.caption("**FX to Base**: how many units of BASE currency for 1 unit of the listed currency (e.g., base AUD: USD→AUD=1.55; INR→AUD=0.0185).")
    fx_aud = st.number_input("AUD→Base (should be 1.0 if base=AUD)", value=float(settings["fx_to_base"].get("AUD", 1.0)))
    fx_usd = st.number_input("USD→Base", value=float(settings["fx_to_base"].get("USD", 1.55)))
    fx_inr = st.number_input("INR→Base", value=float(settings["fx_to_base"].get("INR", 0.0185)))

    # Goals
    g_aud = st.number_input("Monthly Goal (AUD)", value=float(settings["goals"].get("AUD", 0)))
    g_usd = st.number_input("Monthly Goal (USD)", value=float(settings["goals"].get("USD", 0)))
    g_inr = st.number_input("Monthly Goal (INR)", value=float(settings["goals"].get("INR", 0)))

    if st.button("Save Settings", type="primary"):
        new_settings = dict(settings)
        new_settings["base_currency"] = bc
        new_settings["fx_to_base"] = {"AUD": fx_aud, "USD": fx_usd, "INR": fx_inr}
        new_settings["goals"] = {"AUD": g_aud, "USD": g_usd, "INR": g_inr}
        storage.save_settings(new_settings)
        st.success("Settings saved.")
        st.rerun()

# -------------------- Footer --------------------
st.markdown("---")
st.caption("Built with ❤️ in Streamlit • SQLite/CSV storage • Optional OpenAI for insights")
