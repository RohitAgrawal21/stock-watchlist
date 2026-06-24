"""
scraper.py — Fetch fundamentals from screener.in + price data from yfinance.

Design goal: produce ONE flat dict of metrics per stock. The dashboard/config
just picks which keys to display, so you can "add a column" without touching
the parser as long as the underlying data exists on the screener page.

Sources
-------
- screener.in company page  -> top ratios, P&L (Revenue/EBITDA), shareholding
- yfinance                  -> live price + trailing returns (1M/3M/1Y/YTD)
"""

from __future__ import annotations

import re
import time
import datetime as dt
from typing import Optional

import requests
from bs4 import BeautifulSoup

try:
    import yfinance as yf
except Exception:  # yfinance optional at import time
    yf = None


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def clean_num(s: Optional[str]) -> Optional[float]:
    """'₹ 3,960 Cr.' / '44.4' / '18%' / '-' -> float or None."""
    if s is None:
        return None
    s = s.replace(",", "").replace("₹", "").replace("%", "")
    s = s.replace("Cr.", "").replace("Cr", "").strip()
    if s in ("", "-", "—"):
        return None
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group()) if m else None


def _norm_label(s: str) -> str:
    """Normalise a P&L / shareholding row label: strip trailing '+', spaces."""
    return s.replace("+", "").strip()


def pct_change(new: Optional[float], old: Optional[float]) -> Optional[float]:
    if new is None or old is None or old == 0:
        return None
    return round((new - old) / abs(old) * 100, 2)


# --------------------------------------------------------------------------- #
# screener.in
# --------------------------------------------------------------------------- #
def fetch_screener_html(symbol: str, consolidated: bool = True) -> str:
    """Fetch a screener company page, falling back from consolidated -> standalone."""
    paths = []
    if consolidated:
        paths.append(f"https://www.screener.in/company/{symbol}/consolidated/")
    paths.append(f"https://www.screener.in/company/{symbol}/")
    last_err = None
    for url in paths:
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            if r.status_code == 200 and len(r.text) > 5000:
                return r.text
            last_err = f"HTTP {r.status_code} for {url}"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        time.sleep(1)
    raise RuntimeError(f"Could not fetch screener page for {symbol}: {last_err}")


def _parse_top_ratios(soup: BeautifulSoup) -> dict:
    out = {}
    ul = soup.select_one("#top-ratios")
    if not ul:
        return out
    for li in ul.select("li"):
        name_el = li.select_one(".name")
        val_el = li.select_one(".value")
        if not name_el:
            continue
        label = name_el.get_text(" ", strip=True)
        value = val_el.get_text(" ", strip=True) if val_el else ""
        out[label] = value
    return out


def _table_rows(section: BeautifulSoup) -> dict:
    """Return {row_label: [cell_strings...]} for the first table in a section."""
    rows = {}
    if section is None:
        return rows
    table = section.select_one("table")
    if table is None:
        return rows
    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.select("td")]
        if not cells:
            continue
        label = _norm_label(cells[0])
        rows[label] = cells[1:]
    return rows


def _row_vals(rows: dict, *candidates: str) -> list:
    """Find a row by trying several label candidates; return numeric list."""
    for c in candidates:
        for label, cells in rows.items():
            if label.lower() == c.lower():
                return [clean_num(x) for x in cells]
    # loose contains-match fallback
    for c in candidates:
        for label, cells in rows.items():
            if c.lower() in label.lower():
                return [clean_num(x) for x in cells]
    return []


def parse_screener(html: str) -> dict:
    """Parse a screener company page into a flat metric dict."""
    soup = BeautifulSoup(html, "lxml")
    m: dict = {}

    # ---- Top ratios (valuation / returns / quality) ----
    top = _parse_top_ratios(soup)
    m["Market Cap (Cr)"] = clean_num(top.get("Market Cap"))
    m["Price"] = clean_num(top.get("Current Price"))
    m["Stock P/E"] = clean_num(top.get("Stock P/E"))
    m["Book Value"] = clean_num(top.get("Book Value"))
    m["Dividend Yield %"] = clean_num(top.get("Dividend Yield"))
    m["ROCE %"] = clean_num(top.get("ROCE"))
    m["ROE %"] = clean_num(top.get("ROE"))
    m["Face Value"] = clean_num(top.get("Face Value"))
    if top.get("High / Low"):
        hl = top["High / Low"].split("/")
        if len(hl) == 2:
            m["52W High"] = clean_num(hl[0])
            m["52W Low"] = clean_num(hl[1])
    # P/B if not directly given
    if m.get("Price") and m.get("Book Value"):
        m["P/B"] = round(m["Price"] / m["Book Value"], 2)

    # ---- Annual P&L (Revenue / EBITDA / Net Profit + YoY) ----
    pl = _table_rows(soup.select_one("section#profit-loss"))
    sales = _row_vals(pl, "Sales", "Revenue")
    op = _row_vals(pl, "Operating Profit")
    opm = _row_vals(pl, "OPM %")
    npf = _row_vals(pl, "Net Profit")
    eps = _row_vals(pl, "EPS in Rs", "EPS")
    if sales:
        m["Revenue (Cr)"] = sales[-1]
        m["Revenue YoY %"] = pct_change(sales[-1], sales[-2] if len(sales) > 1 else None)
    if op:
        m["EBITDA (Cr)"] = op[-1]
        m["EBITDA YoY %"] = pct_change(op[-1], op[-2] if len(op) > 1 else None)
    if opm:
        m["OPM %"] = opm[-1]
    if npf:
        m["Net Profit (Cr)"] = npf[-1]
        m["Net Profit YoY %"] = pct_change(npf[-1], npf[-2] if len(npf) > 1 else None)
    if eps:
        m["EPS"] = eps[-1]

    # ---- Quarterly (latest quarter Revenue + YoY/QoQ) ----
    q = _table_rows(soup.select_one("section#quarters"))
    qsales = _row_vals(q, "Sales", "Revenue")
    qop = _row_vals(q, "Operating Profit")
    if qsales:
        m["Revenue Qtr (Cr)"] = qsales[-1]
        m["Revenue QoQ %"] = pct_change(qsales[-1], qsales[-2] if len(qsales) > 1 else None)
        m["Revenue YoY Qtr %"] = pct_change(qsales[-1], qsales[-5] if len(qsales) > 4 else None)
    if qop:
        m["EBITDA Qtr (Cr)"] = qop[-1]
        m["EBITDA YoY Qtr %"] = pct_change(qop[-1], qop[-5] if len(qop) > 4 else None)

    # ---- Shareholding (latest quarter + QoQ delta in %-points) ----
    sh = _table_rows(soup.select_one("section#shareholding"))
    for key, label in [
        ("Promoters %", "Promoters"),
        ("FIIs %", "FIIs"),
        ("DIIs %", "DIIs"),
        ("Government %", "Government"),
        ("Public %", "Public"),
    ]:
        vals = _row_vals(sh, label)
        if vals:
            m[key] = vals[-1]
            if len(vals) > 1 and vals[-1] is not None and vals[-2] is not None:
                m[key.replace(" %", " Δ")] = round(vals[-1] - vals[-2], 2)
    nsh = _row_vals(sh, "No. of Shareholders")
    if nsh:
        m["No. of Shareholders"] = nsh[-1]

    return m


# --------------------------------------------------------------------------- #
# yfinance — price + trailing returns
# --------------------------------------------------------------------------- #
def fetch_price_metrics(yf_ticker: str) -> dict:
    if yf is None:
        return {}
    out: dict = {}
    try:
        hist = yf.Ticker(yf_ticker).history(period="1y", auto_adjust=True)
        if hist is None or hist.empty:
            return {}
        close = hist["Close"].dropna()
        last = float(close.iloc[-1])
        out["Price (live)"] = round(last, 2)

        def ret_over(days: int):
            if len(close) < 2:
                return None
            target = close.index[-1] - dt.timedelta(days=days)
            past = close[close.index <= target]
            if past.empty:
                return None
            base = float(past.iloc[-1])
            return round((last - base) / base * 100, 2) if base else None

        out["1M Return %"] = ret_over(30)
        out["3M Return %"] = ret_over(91)
        out["1Y Return %"] = ret_over(365)

        jan1 = dt.datetime(close.index[-1].year, 1, 1, tzinfo=close.index[-1].tz)
        ytd = close[close.index >= jan1]
        if not ytd.empty:
            base = float(ytd.iloc[0])
            out["YTD %"] = round((last - base) / base * 100, 2) if base else None
    except Exception:  # noqa: BLE001
        pass
    return out


# --------------------------------------------------------------------------- #
# Top-level: scrape one stock
# --------------------------------------------------------------------------- #
def scrape_stock(symbol: str, consolidated: bool = True,
                 yf_ticker: Optional[str] = None) -> dict:
    """Return a flat metric dict for one stock. Never raises for price errors."""
    data: dict = {"Symbol": symbol}
    try:
        html = fetch_screener_html(symbol, consolidated=consolidated)
        data.update(parse_screener(html))
        data["_screener_ok"] = True
    except Exception as e:  # noqa: BLE001
        data["_screener_ok"] = False
        data["_error"] = str(e)

    yft = yf_ticker or f"{symbol}.NS"
    data.update(fetch_price_metrics(yft))
    data["Updated"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    return data


if __name__ == "__main__":
    import json
    import sys

    sym = sys.argv[1] if len(sys.argv) > 1 else "KDDL"
    print(json.dumps(scrape_stock(sym), indent=2, ensure_ascii=False))
