"""
storage.py — Config + SQLite persistence.

We store every scrape as a JSON blob keyed by (symbol, timestamp) so you keep
full history (useful for tracking how promoter holding / margins drift over
time). The dashboard reads the latest row per symbol.
"""

from __future__ import annotations

import json
import sqlite3
import datetime as dt
from pathlib import Path

BASE = Path(__file__).parent
CONFIG_PATH = BASE / "config.json"
DB_PATH = BASE / "stocks.db"


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def add_stock(symbol: str, name: str = "", consolidated: bool = True,
              yf_ticker: str = "") -> bool:
    cfg = load_config()
    symbol = symbol.strip().upper()
    if any(s["symbol"].upper() == symbol for s in cfg["watchlist"]):
        return False
    cfg["watchlist"].append({
        "symbol": symbol,
        "name": name or symbol,
        "consolidated": consolidated,
        "yf_ticker": yf_ticker or f"{symbol}.NS",
    })
    save_config(cfg)
    return True


def remove_stock(symbol: str) -> None:
    cfg = load_config()
    cfg["watchlist"] = [s for s in cfg["watchlist"]
                        if s["symbol"].upper() != symbol.strip().upper()]
    save_config(cfg)


def set_columns(columns: list) -> None:
    cfg = load_config()
    cfg["columns"] = columns
    save_config(cfg)


# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #
def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            symbol     TEXT NOT NULL,
            ts         TEXT NOT NULL,
            data       TEXT NOT NULL,
            PRIMARY KEY (symbol, ts)
        )
    """)
    return c


def save_snapshot(symbol: str, data: dict) -> None:
    ts = dt.datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO snapshots(symbol, ts, data) VALUES (?,?,?)",
                  (symbol, ts, json.dumps(data, ensure_ascii=False)))


def latest_snapshots() -> dict:
    """Return {symbol: data_dict} for the most recent snapshot of each symbol."""
    out = {}
    with _conn() as c:
        rows = c.execute("""
            SELECT s.symbol, s.data FROM snapshots s
            JOIN (SELECT symbol, MAX(ts) AS mts FROM snapshots GROUP BY symbol) m
              ON s.symbol = m.symbol AND s.ts = m.mts
        """).fetchall()
    for sym, blob in rows:
        out[sym] = json.loads(blob)
    return out


def history(symbol: str, metric: str) -> list:
    """Return [(ts, value)] for one metric of one symbol, oldest first."""
    pts = []
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, data FROM snapshots WHERE symbol=? ORDER BY ts", (symbol,)
        ).fetchall()
    for ts, blob in rows:
        d = json.loads(blob)
        if metric in d and d[metric] is not None:
            pts.append((ts, d[metric]))
    return pts
