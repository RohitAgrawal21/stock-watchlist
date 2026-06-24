"""
refresh.py — Scrape every stock in the watchlist and persist a snapshot.

Used by both the dashboard's Refresh button and the daily scheduler.
Run directly:  python refresh.py
"""

from __future__ import annotations

import time

from scraper import scrape_stock
from storage import load_config, save_snapshot


def refresh_all(verbose: bool = True) -> dict:
    cfg = load_config()
    results = {}
    for s in cfg["watchlist"]:
        sym = s["symbol"]
        if verbose:
            print(f"  scraping {sym} ...", end=" ", flush=True)
        data = scrape_stock(
            sym,
            consolidated=s.get("consolidated", True),
            yf_ticker=s.get("yf_ticker") or f"{sym}.NS",
        )
        data["name"] = s.get("name", sym)
        save_snapshot(sym, data)
        results[sym] = data
        if verbose:
            ok = "OK" if data.get("_screener_ok") else f"SCREENER FAIL ({data.get('_error','')[:40]})"
            print(f"price={data.get('Price (live)')} | {ok}")
        time.sleep(1.5)  # be polite to screener.in
    return results


if __name__ == "__main__":
    import datetime as dt
    print(f"[{dt.datetime.now():%Y-%m-%d %H:%M}] Refreshing watchlist...")
    refresh_all()
    print("Done.")
