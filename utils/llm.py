import os, textwrap
import yfinance as yf

def _atr_like(symbol: str, market: str) -> float:
    t = symbol
    if market == "India":
        t = f"{symbol}.NS"
    elif market == "Australia":
        t = f"{symbol}.AX"
    try:
        df = yf.Ticker(t).history(period="3mo")
        if df.shape[0] < 15:
            return None
        # simple ATR proxy
        tr = (df["High"] - df["Low"]).abs()
        return float(tr.rolling(14).mean().iloc[-1])
    except Exception:
        return None

def _heuristic(market: str, symbol: str, entry: float, bias: str, baseline_risk_pct: float = 1.0) -> str:
    atr = _atr_like(symbol, market)
    # Fallback to % risk on price if ATR unavailable
    risk_per_share = (baseline_risk_pct/100.0) * entry
    if atr is not None and atr > 0:
        risk_per_share = max(risk_per_share, 0.8 * atr)
    if bias.startswith("Swing Long"):
        sl = round(entry - risk_per_share, 2)
        t1 = round(entry + 1.5 * risk_per_share, 2)
        t2 = round(entry + 2.5 * risk_per_share, 2)
    else:
        sl = round(entry + risk_per_share, 2)
        t1 = round(entry - 1.5 * risk_per_share, 2)
        t2 = round(entry - 2.5 * risk_per_share, 2)
    text = f"""**Heuristic Suggestion**
- Market: {market} | Symbol: **{symbol}** | Bias: **{bias}**
- Planned entry: **{entry}**
- Suggested SL: **{sl}**
- T1: **{t1}**, T2: **{t2}**
- Rationale: uses a basic ATR-like risk proxy (if available) or {baseline_risk_pct}% of price.
"""
    return text

def get_trade_insights(market: str, symbol: str, planned_entry: float, bias: str, baseline_risk_pct: float = 1.0) -> str:
    api_key = os.getenv("OPENAI_API_KEY", None)
    if not api_key:
        return _heuristic(market, symbol, planned_entry, bias, baseline_risk_pct)
    try:
        # Lazy import to avoid hard dependency if not used
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = f"""
You are a cautious swing-trading assistant.
Market: {market}; Symbol: {symbol}; Planned entry: {planned_entry}; Bias: {bias}.
Return JSON with fields: sl, t1, t2, rationale (50 words), risk_per_share.
"""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":"You output concise, practical risk-first trading suggestions."},
                      {"role":"user","content":prompt}],
            temperature=0.3,
        )
        content = resp.choices[0].message.content
        return f"**LLM Suggestion**\n\n{content}"
    except Exception as e:
        return _heuristic(market, symbol, planned_entry, bias, baseline_risk_pct)
