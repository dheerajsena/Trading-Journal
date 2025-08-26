from typing import Dict, Any
import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st

def _is_closed(row):
    return pd.notna(row.get("exit_date")) and pd.notna(row.get("exit_price"))

def compute_closed_pnl(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    mask = df.apply(_is_closed, axis=1)
    if not mask.any():
        return 0.0
    pnl = (df.loc[mask, "exit_price"] - df.loc[mask, "entry_price"]) * df.loc[mask, "qty"]
    return float(pnl.sum())

def _fetch_ltp(symbol: str, market: str):
    # naive mapping to Yahoo tickers; user may need to adjust suffixes for some exchanges
    t = symbol
    if market == "India":
        # NSE tickers often require ".NS"
        t = f"{symbol}.NS"
    elif market == "Australia":
        t = f"{symbol}.AX"
    try:
        data = yf.Ticker(t).history(period="5d")
        if not data.empty:
            return float(data["Close"].iloc[-1])
    except Exception:
        pass
    return None

def compute_open_pnl(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    open_df = df[df["exit_price"].isna()]
    if open_df.empty:
        return 0.0
    total = 0.0
    warnings = 0
    for _, r in open_df.iterrows():
        ltp = _fetch_ltp(str(r["symbol"]), str(r["market"]))
        if ltp is None or pd.isna(ltp):
            warnings += 1
            continue
        total += (ltp - float(r["entry_price"])) * float(r["qty"])
    if warnings > 0:
        st.info(f"Open P&L estimated without LTP for {warnings} open trade(s) (no network or symbol mapping).")
    return float(total)

def currency_totals(df: pd.DataFrame) -> Dict[str, float]:
    if df.empty:
        return {}
    pnl_native = (df["exit_price"].fillna(df["entry_price"]) - df["entry_price"]) * df["qty"]
    out = {}
    for cur in ["INR","USD","AUD"]:
        mask = df["currency"] == cur
        if mask.any():
            out[cur] = float(pnl_native.loc[mask].sum())
    return out

def days_held_col(df: pd.DataFrame) -> pd.Series:
    ed = pd.to_datetime(df["entry_date"], errors="coerce")
    xd = pd.to_datetime(df["exit_date"], errors="coerce")
    today = pd.Timestamp.today().normalize()
    effective_exit = xd.fillna(today)
    return (effective_exit - ed).dt.days

def roi_col(df: pd.DataFrame) -> pd.Series:
    invested = df["capital_invested"]
    pnl = (df["exit_price"].fillna(df["entry_price"]) - df["entry_price"]) * df["qty"]
    with np.errstate(divide="ignore", invalid="ignore"):
        roi = np.where((invested > 0), pnl / invested * 100.0, np.nan)
    return pd.Series(roi, index=df.index)

def best_trades(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {}
    roi = roi_col(df)
    idx = np.nanargmax(roi.values) if np.any(~np.isnan(roi.values)) else None
    if idx is None:
        return {"best_roi_pct": "N/A"}
    try:
        return {"best_roi_pct": round(float(roi.iloc[idx]), 2),
                "symbol": str(df.iloc[idx]["symbol"])}
    except Exception:
        return {"best_roi_pct": "N/A"}

def goal_progress(df: pd.DataFrame, goal_ccy: str, settings: Dict[str,Any]) -> Dict[str, Any]:
    # Sum P&L for trades in that currency (closed only) this month
    if df.empty:
        return {"goal": settings["goals"].get(goal_ccy, 0.0), "achieved": 0.0, "progress_pct": 0.0}
    mask = df["currency"] == goal_ccy
    mdf = df.loc[mask].copy()
    closed_mask = mdf["exit_price"].notna()
    pnl = ((mdf.loc[closed_mask, "exit_price"] - mdf.loc[closed_mask, "entry_price"]) * mdf.loc[closed_mask, "qty"]).sum()
    goal = float(settings["goals"].get(goal_ccy, 0.0))
    pct = (float(pnl) / goal * 100.0) if goal > 0 else 0.0
    return {"goal": goal, "achieved": float(pnl), "progress_pct": pct}
