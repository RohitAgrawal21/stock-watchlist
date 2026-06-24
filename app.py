"""
app.py — Streamlit dashboard for the screener watchlist.

Run:  streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from storage import (
    load_config, latest_snapshots, add_stock, remove_stock, set_columns, history,
)
from refresh import refresh_all

st.set_page_config(page_title="Stock Watchlist", layout="wide")

PCT_COLS_HINT = ("%", "Return", "Δ", "YoY", "QoQ", "YTD")


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def build_dataframe(cfg: dict) -> pd.DataFrame:
    snaps = latest_snapshots()
    rows = []
    for s in cfg["watchlist"]:
        d = snaps.get(s["symbol"], {})
        row = {"Symbol": s["symbol"]}
        row.update(d)
        rows.append(row)
    return pd.DataFrame(rows)


def available_metrics(df: pd.DataFrame) -> list:
    skip = {"Symbol", "_screener_ok", "_error"}
    return [c for c in df.columns if c not in skip and not c.startswith("_")]


def style_df(df: pd.DataFrame):
    color_cols = [c for c in df.columns
                  if any(h in c for h in ("Return", "Δ", "YoY", "QoQ", "YTD"))]

    def col_color(val):
        if isinstance(val, (int, float)):
            if val > 0:
                return "color: #18794e; font-weight: 600"
            if val < 0:
                return "color: #cd2b31; font-weight: 600"
        return ""

    sty = df.style
    if color_cols:
        sty = sty.map(col_color, subset=color_cols)
    num_fmt = {c: "{:,.2f}" for c in df.columns
               if df[c].dtype.kind in "fi" and c != "Symbol"}
    return sty.format(num_fmt, na_rep="—")


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #
cfg = load_config()

# First visit (e.g. fresh cloud deploy with no DB yet): auto-fetch once so the
# page isn't blank. Guarded by session_state so it only runs once per session.
if cfg.get("watchlist") and not latest_snapshots() and not st.session_state.get("_bootstrapped"):
    st.session_state["_bootstrapped"] = True
    with st.spinner("First load — fetching data from screener.in + yfinance ..."):
        refresh_all(verbose=False)

st.title("📈 Stock Watchlist Dashboard")

top = st.columns([1, 1, 3])
with top[0]:
    if st.button("🔄 Refresh now", type="primary", width="stretch"):
        with st.spinner("Scraping screener.in + yfinance ..."):
            refresh_all(verbose=False)
        st.success("Updated.")
        st.rerun()

df = build_dataframe(cfg)
metrics = available_metrics(df)

if not df.empty and "Updated" in df.columns:
    last = df["Updated"].dropna()
    with top[1]:
        st.metric("Last updated", last.max() if not last.empty else "never")

# ----- Sidebar: manage watchlist & columns -----
with st.sidebar:
    st.header("⚙️ Manage")

    st.subheader("Add stock")
    new_sym = st.text_input("Screener / NSE symbol", placeholder="e.g. TITAN").strip().upper()
    new_name = st.text_input("Display name", placeholder="optional")
    new_cons = st.checkbox("Consolidated", value=True)
    if st.button("➕ Add", width="stretch") and new_sym:
        if add_stock(new_sym, new_name, new_cons):
            with st.spinner(f"Fetching {new_sym} ..."):
                refresh_all(verbose=False)
            st.success(f"Added {new_sym}")
            st.rerun()
        else:
            st.warning(f"{new_sym} already in watchlist.")

    st.subheader("Remove stock")
    syms = [s["symbol"] for s in cfg["watchlist"]]
    if syms:
        rm = st.selectbox("Pick", syms, index=None, placeholder="select…")
        if st.button("🗑️ Remove", width="stretch") and rm:
            remove_stock(rm)
            st.rerun()

    st.subheader("Columns")
    chosen = st.multiselect(
        "Show these metrics",
        options=metrics,
        default=[c for c in cfg.get("columns", []) if c in metrics],
    )
    if st.button("💾 Save columns", width="stretch"):
        set_columns(chosen)
        st.success("Saved.")
        st.rerun()

# ----- Main table -----
if df.empty:
    st.info("Watchlist is empty or not yet scraped. Add a stock or press Refresh.")
else:
    cols = [c for c in cfg.get("columns", []) if c in df.columns]
    show = df[["Symbol"] + [c for c in cols if c != "Symbol"]]
    st.dataframe(style_df(show), width="stretch", hide_index=True,
                 height=min(600, 80 + 38 * len(show)))

    # flag any scraping failures
    bad = df[df.get("_screener_ok") == False] if "_screener_ok" in df else pd.DataFrame()
    if not bad.empty:
        st.warning("Screener fetch failed for: " + ", ".join(bad["Symbol"]))

    # ----- History chart -----
    st.divider()
    st.subheader("📉 Metric history")
    hc = st.columns([1, 1])
    with hc[0]:
        h_sym = st.selectbox("Stock", df["Symbol"].tolist())
    with hc[1]:
        num_metrics = [m for m in metrics
                       if pd.api.types.is_numeric_dtype(df[m]) if m in df]
        h_met = st.selectbox("Metric", num_metrics,
                             index=num_metrics.index("Price (live)")
                             if "Price (live)" in num_metrics else 0)
    pts = history(h_sym, h_met)
    if len(pts) > 1:
        hist_df = pd.DataFrame(pts, columns=["ts", h_met]).set_index("ts")
        st.line_chart(hist_df)
    else:
        st.caption("Need ≥2 snapshots to chart history. It builds up as you refresh daily.")
