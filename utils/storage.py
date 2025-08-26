import os, json, sqlite3, time
from typing import Dict, Any, Optional
import pandas as pd

DATA_DIR = "data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
CSV_FILE = os.path.join(DATA_DIR, "trades.csv")
SQLITE_FILE = os.path.join(DATA_DIR, "trades.db")
BACKEND_FILE = os.path.join(DATA_DIR, "backend.txt")

SCHEMA_COLUMNS = ["id","user","market","symbol","currency","sector","trade_type",
                  "entry_date","exit_date","qty","entry_price","exit_price",
                  "capital_invested","sl","target","notes","created_at","updated_at"]

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user TEXT,
  market TEXT,
  symbol TEXT,
  currency TEXT,
  sector TEXT,
  trade_type TEXT,
  entry_date TEXT,
  exit_date TEXT,
  qty INTEGER,
  entry_price REAL,
  exit_price REAL,
  capital_invested REAL,
  sl REAL,
  target REAL,
  notes TEXT,
  created_at TEXT,
  updated_at TEXT
);
"""

class Storage:
    def __init__(self, backend: str = "sqlite"):
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(BACKEND_FILE):
            try:
                with open(BACKEND_FILE, "r") as f:
                    saved = f.read().strip()
                    backend = saved if saved in ("sqlite","csv") else backend
            except Exception:
                pass
        self.backend = backend
        if self.backend == "sqlite":
            self._ensure_sqlite()
        else:
            self._ensure_csv()

    def save_backend_choice(self, backend: str):
        with open(BACKEND_FILE, "w") as f:
            f.write(backend)

    def _ensure_sqlite(self):
        conn = sqlite3.connect(SQLITE_FILE, check_same_thread=False)
        cur = conn.cursor()
        cur.execute(CREATE_SQL)
        conn.commit()
        cur.close()
        conn.close()

    def _ensure_csv(self):
        if not os.path.exists(CSV_FILE):
            df = pd.DataFrame(columns=SCHEMA_COLUMNS)
            df.to_csv(CSV_FILE, index=False)

    def insert_trade(self, payload: Dict[str, Any]):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        payload = {**payload, "created_at": now, "updated_at": now}
        if self.backend == "sqlite":
            conn = sqlite3.connect(SQLITE_FILE, check_same_thread=False)
            cur = conn.cursor()
            cols = [c for c in SCHEMA_COLUMNS if c != "id"]
            cols_sql = ",".join(cols)
            placeholders = ",".join(["?"]*len(cols))
            values = [payload.get(c) for c in cols]
            cur.execute(f"INSERT INTO trades ({cols_sql}) VALUES ({placeholders})", values)
            conn.commit()
            cur.close()
            conn.close()
        else:
            if not os.path.exists(CSV_FILE):
                self._ensure_csv()
            df = pd.read_csv(CSV_FILE)
            # assign id
            new_id = int(df["id"].max()) + 1 if "id" in df.columns and df.shape[0] > 0 else 1
            payload_row = {c: payload.get(c) for c in SCHEMA_COLUMNS if c != "id"}
            payload_row["id"] = new_id
            df = pd.concat([df, pd.DataFrame([payload_row])], ignore_index=True)
            df.to_csv(CSV_FILE, index=False)

    def read_trades(self) -> pd.DataFrame:
        if self.backend == "sqlite":
            conn = sqlite3.connect(SQLITE_FILE, check_same_thread=False)
            df = pd.read_sql_query("SELECT * FROM trades", conn)
            conn.close()
            return df
        else:
            if not os.path.exists(CSV_FILE):
                return pd.DataFrame(columns=SCHEMA_COLUMNS)
            return pd.read_csv(CSV_FILE)

    def save_settings(self, settings: Dict[str, Any]):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)

    def read_settings(self) -> Dict[str, Any]:
        if not os.path.exists(SETTINGS_FILE):
            return {}
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}

def ensure_settings(storage: "Storage") -> Dict[str, Any]:
    default_settings = {
        "base_currency": "AUD",
        "fx_to_base": {"AUD": 1.0, "USD": 1.55, "INR": 0.0185},
        "goals": {"AUD": 500, "USD": 0, "INR": 0}
    }
    s = storage.read_settings()
    if not s:
        storage.save_settings(default_settings)
        return default_settings
    # fill missing keys
    for k, v in default_settings.items():
        if k not in s:
            s[k] = v
    storage.save_settings(s)
    return s
