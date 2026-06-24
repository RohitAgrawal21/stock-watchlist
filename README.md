# Stock Watchlist Scraper + Dashboard

Pulls fundamentals from **screener.in** and live price/returns from **yfinance**,
stores history in SQLite, and shows it in an interactive **Streamlit** dashboard.
Config-driven: add stocks and choose columns without editing code.

## Quick start

```
# 1. Launch the dashboard (double-click or run):
run_dashboard.bat

# 2. (Optional) keep data auto-updating daily at 18:30:
run_scheduler.bat
```

The dashboard opens at http://localhost:8501.

## Files

| File            | Purpose |
|-----------------|---------|
| `config.json`   | Your watchlist + which columns to show. Edit by hand or via the app sidebar. |
| `scraper.py`    | Fetches + parses screener.in and yfinance into one flat metric dict per stock. |
| `storage.py`    | Config helpers + SQLite history (`stocks.db`). |
| `refresh.py`    | Scrapes the whole watchlist and saves a snapshot. `python refresh.py`. |
| `app.py`        | Streamlit dashboard (table, add/remove stock, column picker, history chart). |
| `scheduler.py`  | APScheduler daily auto-refresh. |

## Adding stocks

- **In the app:** sidebar → *Add stock* → enter the screener/NSE symbol (e.g. `TITAN`).
- **By hand:** add an entry to `watchlist` in `config.json`:
  ```json
  { "symbol": "TITAN", "name": "Titan Co", "consolidated": true, "yf_ticker": "TITAN.NS" }
  ```
  `symbol` is the ticker as it appears in the screener URL
  (`screener.in/company/SYMBOL/`). For most NSE stocks it matches the NSE code.

## Adding / changing columns

The scraper produces **every** metric below for each stock. To show a column,
add its exact key to `columns` in `config.json` (or use the sidebar column picker):

**Valuation:** `Market Cap (Cr)`, `Price`, `Price (live)`, `Stock P/E`, `P/B`,
`Book Value`, `Dividend Yield %`, `Face Value`, `52W High`, `52W Low`

**Growth / P&L:** `Revenue (Cr)`, `Revenue YoY %`, `EBITDA (Cr)`, `EBITDA YoY %`,
`OPM %`, `Net Profit (Cr)`, `Net Profit YoY %`, `EPS`,
`Revenue Qtr (Cr)`, `Revenue QoQ %`, `Revenue YoY Qtr %`,
`EBITDA Qtr (Cr)`, `EBITDA YoY Qtr %`

**Returns:** `1M Return %`, `3M Return %`, `1Y Return %`, `YTD %`

**Quality:** `ROCE %`, `ROE %`

**Shareholding (latest quarter + QoQ Δ in %-points):**
`Promoters %`, `Promoters Δ`, `FIIs %`, `FIIs Δ`, `DIIs %`, `DIIs Δ`,
`Government %`, `Public %`, `No. of Shareholders`

Want a metric not listed (e.g. Debt/Equity)? It's usually one extra row pull in
`parse_screener()` — the table parsing helpers already expose every row.

## Auto-update options

- **On demand:** the *Refresh now* button in the app.
- **Daily:** `run_scheduler.bat` (refreshes at 18:30, editable in `scheduler.py`).
- **Hands-off at boot:** point Windows Task Scheduler at `run_scheduler.bat`,
  or run `python refresh.py` on a trigger.

## Notes

- screener.in public pages cover the listed metrics. A few items (full Debt
  schedule, detailed peers) need a free screener.in login — not used here.
- Be gentle: `refresh.py` sleeps 1.5s between stocks. Large watchlists take a
  little time but won't get you rate-limited.
- History accumulates every refresh, so the dashboard's *Metric history* chart
  fills in over the days/weeks (great for watching promoter/FII holding drift).
