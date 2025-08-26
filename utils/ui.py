import streamlit as st

def app_header(title: str):
    st.title(title)
    st.caption("Multi-market (India/US/Australia) • Multi-currency (INR/USD/AUD) • Swing")

def sidebar_nav() -> str:
    with st.sidebar:
        st.markdown("## Navigation")
        return st.radio("Go to", ["Record Trade", "Monthly Report", "Settings"], index=0)

def currency_badge(ccy: str) -> str:
    colors = {"INR": "#e76f51", "USD": "#2a9d8f", "AUD": "#457b9d"}
    c = colors.get(ccy, "#888")
    return f'<span style="background:{c};color:white;padding:2px 6px;border-radius:6px;">{ccy}</span>'

def show_toast(msg: str):
    st.success(msg, icon="✅")

def market_to_currency_default(market: str) -> str:
    return {"India":"INR","US":"USD","Australia":"AUD"}.get(market, "AUD")

def sectors_list():
    return ["IT","Banking/Financials","Energy/Oil & Gas","Consumer","Auto/Auto Ancillaries",
            "Metals/Mining","Pharma/Healthcare","Utilities","Real Estate","Telecom","ETF/Index","Other"]

def trade_types_list():
    return ["Swing Long","Swing Short","Positional Long","Positional Short","Event/Earnings","Other"]
