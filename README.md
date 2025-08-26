# Streamlit Trading Journal (India / US / Australia)

A professional yet beginner‑friendly **swing trading** journal with:
- Multi‑market support (**India, US, Australia**) and **multi‑currency** (INR, USD, AUD)
- Clean **Trade Entry Form** (sector, trade type, SL, target, notes)
- **Monthly Dashboard** (profit by month, per‑currency totals, best trades, ROI%, days held)
- **Goal tracker** (per‑currency, e.g., AUD 500/month)
- **AI Insights Panel** (optional OpenAI integration) to suggest SL/targets from planned entries
- **Storage**: SQLite (default) or CSV (toggle in Settings). Optional GitHub sync for CSV if you add a token.

## Quickstart

```bash
# 1) Clone and install
pip install -r requirements.txt

# 2) (Optional) Set OpenAI key for AI insights
export OPENAI_API_KEY=sk-...

# 3) Run
streamlit run app.py
```

### Streamlit Cloud (Deploy from GitHub)
- Push this repo to GitHub.
- In Streamlit Cloud, **Deploy** and set **secrets** if needed (see `.streamlit/secrets.toml.example`).

## Storage
- Default **SQLite** at `data/trades.db` (auto-created).
- Switch to **CSV** in **Settings** (stores at `data/trades.csv`).
- Optional GitHub commit of `data/trades.csv` if you set `secrets["github"]["token"]` and `secrets["github"]["repo"]` (e.g., `username/reponame`).

## Authentication (simplified)
- Default demo login: `demo / demo`.
- To restrict: set `secrets["auth"]["username"]` and `secrets["auth"]["password"]`; otherwise the demo credentials are used.

## Notes
- For **open trades P&L** the app **optionally** fetches LTP with `yfinance`. If network is blocked, it gracefully falls back to entry prices (shows warning).
- **FX conversion** is manual (enter rates in Settings). Choose your **base currency** and set `FX to Base` mapping (e.g., with base AUD: `USD: 1.55`, `INR: 0.0185`).

## Project Layout

```
.
├── app.py
├── requirements.txt
├── utils/
│   ├── storage.py
│   ├── reporting.py
│   ├── llm.py
│   ├── ui.py
│   └── github_sync.py
├── data/
│   ├── trades.db        # created at runtime if sqlite backend
│   ├── trades.csv       # created if csv backend
│   └── settings.json    # created at first run
└── .streamlit/
    └── secrets.toml.example
```

## License
MIT
