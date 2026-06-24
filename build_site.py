"""
build_site.py — Scrape the watchlist and render a static website (docs/index.html).

Used both locally (just run it and open docs/index.html) and by the GitHub
Action, which runs it daily and publishes the result to GitHub Pages.

Output is a single self-contained HTML file (inline CSS + a little vanilla JS for
click-to-sort) — no servers, no dependencies to load in the browser.
"""

from __future__ import annotations

import html
import datetime as dt
from pathlib import Path

from storage import load_config
from refresh import refresh_all

OUT = Path(__file__).parent / "docs" / "index.html"

# Columns whose values should be colour-coded green (+) / red (-)
COLOR_HINTS = ("Return", "Δ", "YoY", "QoQ", "YTD")


def fmt(col: str, val) -> tuple[str, str]:
    """Return (display_text, data-sort value) for a cell."""
    if val is None or val == "":
        return "—", ""
    if isinstance(val, (int, float)):
        sort = f"{val}"
        if abs(val) >= 1000:
            disp = f"{val:,.0f}"
        else:
            disp = f"{val:,.2f}".rstrip("0").rstrip(".")
        return disp, sort
    return html.escape(str(val)), html.escape(str(val))


def cell_class(col: str, val) -> str:
    if isinstance(val, (int, float)) and any(h in col for h in COLOR_HINTS):
        if val > 0:
            return "pos"
        if val < 0:
            return "neg"
    return ""


def build_html(cfg: dict, data: dict) -> str:
    # 'name' and 'Updated' are shown in the Stock column / header banner, so we
    # don't repeat them as data columns.
    columns = [c for c in cfg.get("columns", []) if c not in ("Updated", "name")]

    updated = "—"
    for d in data.values():
        if d.get("Updated"):
            updated = d["Updated"]

    # --- table head ---
    ths = ['<th data-col="Stock" onclick="sortBy(this,0)">Stock</th>']
    for i, c in enumerate(columns, start=1):
        ths.append(f'<th data-col="{html.escape(c)}" onclick="sortBy(this,{i})">{html.escape(c)}</th>')
    thead = "<tr>" + "".join(ths) + "</tr>"

    # --- table body ---
    rows_html = []
    for s in cfg["watchlist"]:
        sym = s["symbol"]
        d = data.get(sym, {})
        name = d.get("name") or s.get("name") or sym
        cells = [
            f'<td class="stock" data-sort="{html.escape(name)}">'
            f'<a href="https://www.screener.in/company/{html.escape(sym)}/" '
            f'target="_blank">{html.escape(str(name))}</a>'
            f'<span class="sym">{html.escape(sym)}</span></td>'
        ]
        for c in columns:
            disp, sortv = fmt(c, d.get(c))
            cls = cell_class(c, d.get(c))
            cells.append(f'<td class="{cls}" data-sort="{sortv}">{disp}</td>')
        if not d.get("_screener_ok", True):
            cells.append("")  # spacing safety
        rows_html.append("<tr>" + "".join(cells) + "</tr>")
    tbody = "\n".join(rows_html)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stock Watchlist</title>
<style>
  :root {{
    --bg:#f7f8fa; --card:#fff; --line:#e5e7eb; --txt:#111827; --muted:#6b7280;
    --head:#1f2937; --pos:#0a7d34; --neg:#c01919; --accent:#2563eb;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--txt);
    font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:1300px; margin:0 auto; padding:24px 16px 60px; }}
  h1 {{ font-size:22px; margin:0 0 2px; }}
  .meta {{ color:var(--muted); font-size:13px; margin-bottom:16px; }}
  .controls {{ margin-bottom:12px; }}
  input[type=search] {{ padding:8px 12px; border:1px solid var(--line);
    border-radius:8px; font-size:14px; width:240px; }}
  .btn {{ margin-left:8px; padding:8px 14px; border:1px solid var(--accent);
    background:var(--accent); color:#fff; border-radius:8px; font-size:14px;
    cursor:pointer; }}
  .btn:hover {{ background:#1d4ed8; }}
  .btn-alt {{ background:#fff; color:var(--accent); }}
  .btn-alt:hover {{ background:#eef2ff; }}
  .tablecard {{ background:var(--card); border:1px solid var(--line);
    border-radius:12px; overflow:auto; box-shadow:0 1px 2px rgba(0,0,0,.04); }}
  table {{ border-collapse:collapse; width:100%; font-size:13px; white-space:nowrap; }}
  th, td {{ padding:9px 12px; text-align:right; border-bottom:1px solid var(--line); }}
  th {{ position:sticky; top:0; background:var(--head); color:#fff; cursor:pointer;
    user-select:none; font-weight:600; }}
  th:hover {{ background:#374151; }}
  th:first-child, td:first-child {{ text-align:left; position:sticky; left:0; }}
  td:first-child {{ background:var(--card); }}
  tbody tr:hover td {{ background:#eef2ff; }}
  td.stock a {{ color:var(--accent); text-decoration:none; font-weight:600; }}
  td.stock .sym {{ display:block; color:var(--muted); font-size:11px; font-weight:400; }}
  td.pos {{ color:var(--pos); font-weight:600; }}
  td.neg {{ color:var(--neg); font-weight:600; }}
  .foot {{ color:var(--muted); font-size:12px; margin-top:14px; }}
  .foot a {{ color:var(--accent); }}
</style>
<script src="https://cdn.jsdelivr.net/npm/xlsx-js-style@1.2.0/dist/xlsx.bundle.js" defer></script>
</head>
<body>
<div class="wrap">
  <h1>📈 Stock Watchlist</h1>
  <div class="meta">Last updated: {html.escape(updated)} &middot;
    Fundamentals from screener.in &middot; Price from Yahoo Finance &middot;
    Click any column header to sort</div>
  <div class="controls">
    <input type="search" id="q" placeholder="Filter stocks…" oninput="filterRows()">
    <button class="btn" onclick="downloadXLSX()">⬇ Download Excel</button>
    <button class="btn btn-alt" onclick="downloadCSV()">⬇ CSV</button>
  </div>
  <div class="tablecard">
    <table id="t">
      <thead>{thead}</thead>
      <tbody>
{tbody}
      </tbody>
    </table>
  </div>
  <div class="foot">Auto-updates daily. Not investment advice.</div>
</div>
<script>
let sortState = {{}};
function sortBy(th, col) {{
  const table = document.getElementById('t');
  const tbody = table.tBodies[0];
  const rows = Array.from(tbody.rows);
  const asc = !(sortState[col] === 'asc');
  sortState = {{}}; sortState[col] = asc ? 'asc' : 'desc';
  rows.sort((a, b) => {{
    let x = a.cells[col].getAttribute('data-sort');
    let y = b.cells[col].getAttribute('data-sort');
    const nx = parseFloat(x), ny = parseFloat(y);
    const bothNum = !isNaN(nx) && !isNaN(ny);
    if (x === '' && y === '') return 0;
    if (x === '') return 1;          // blanks always sink
    if (y === '') return -1;
    let cmp = bothNum ? (nx - ny) : String(x).localeCompare(String(y));
    return asc ? cmp : -cmp;
  }});
  rows.forEach(r => tbody.appendChild(r));
  document.querySelectorAll('th').forEach(h => h.textContent = h.textContent.replace(/[ ▲▼]+$/,''));
  th.textContent = th.textContent + (asc ? ' ▲' : ' ▼');
}}
function filterRows() {{
  const q = document.getElementById('q').value.toLowerCase();
  document.querySelectorAll('#t tbody tr').forEach(r => {{
    r.style.display = r.cells[0].textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
function csvCell(v) {{
  v = (v == null ? '' : String(v));
  return /[",\\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
}}
function downloadCSV() {{
  const table = document.getElementById('t');
  const heads = Array.from(table.tHead.rows[0].cells).map(th => th.getAttribute('data-col'));
  // 'Stock' becomes two columns in the export: Name + Symbol
  const out = [['Name', 'Symbol'].concat(heads.slice(1)).map(csvCell).join(',')];
  Array.from(table.tBodies[0].rows).forEach(r => {{
    if (r.style.display === 'none') return;            // respect the filter
    const stock = r.cells[0];
    const name = (stock.querySelector('a') || stock).textContent.trim();
    const sym = (stock.querySelector('.sym') || {{textContent:''}}).textContent.trim();
    const rest = Array.from(r.cells).slice(1).map(td => {{
      const ds = td.getAttribute('data-sort');
      return ds !== null && ds !== '' ? ds : td.textContent.trim();
    }});
    out.push([name, sym].concat(rest).map(csvCell).join(','));
  }});
  const blob = new Blob([out.join('\\n')], {{type: 'text/csv;charset=utf-8;'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'stock-watchlist-' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}}
function downloadXLSX() {{
  if (typeof XLSX === 'undefined') {{ alert('Excel library is still loading — try again in a moment.'); return; }}
  const table = document.getElementById('t');
  const heads = Array.from(table.tHead.rows[0].cells).map(th => th.getAttribute('data-col'));
  const headerRow = ['Name', 'Symbol'].concat(heads.slice(1));
  const colorIdx = new Set();
  headerRow.forEach((h, i) => {{ if (/Return|Δ|YoY|QoQ|YTD/.test(h)) colorIdx.add(i); }});
  const aoa = [headerRow];
  Array.from(table.tBodies[0].rows).forEach(r => {{
    if (r.style.display === 'none') return;            // respect the filter
    const stock = r.cells[0];
    const name = (stock.querySelector('a') || stock).textContent.trim();
    const sym = (stock.querySelector('.sym') || {{textContent:''}}).textContent.trim();
    const row = [name, sym];
    Array.from(r.cells).slice(1).forEach(td => {{
      const ds = td.getAttribute('data-sort');
      const num = parseFloat(ds);
      const isNum = ds !== null && ds !== '' && !isNaN(num);
      const txt = td.textContent.trim();
      row.push(isNum ? num : (txt === '—' ? '' : txt));   // numbers stay numbers
    }});
    aoa.push(row);
  }});
  const ws = XLSX.utils.aoa_to_sheet(aoa);
  const nCols = headerRow.length, nRows = aoa.length;
  for (let c = 0; c < nCols; c++) {{
    const a = XLSX.utils.encode_cell({{r:0, c:c}});
    if (ws[a]) ws[a].s = {{ font:{{bold:true, color:{{rgb:'FFFFFF'}}}},
      fill:{{fgColor:{{rgb:'1F2937'}}}}, alignment:{{horizontal: c<2?'left':'right'}} }};
  }}
  for (let rr = 1; rr < nRows; rr++) {{
    for (let c = 0; c < nCols; c++) {{
      const a = XLSX.utils.encode_cell({{r:rr, c:c}});
      const cell = ws[a]; if (!cell) continue;
      cell.s = cell.s || {{}};
      if (c >= 2) cell.s.alignment = {{horizontal:'right'}};
      if (colorIdx.has(c) && typeof cell.v === 'number') {{
        cell.s.font = {{ bold:true, color:{{rgb: cell.v>0 ? '0A7D34' : (cell.v<0 ? 'C01919' : '000000')}} }};
      }}
    }}
  }}
  ws['!cols'] = headerRow.map((h, i) => ({{ wch: i===0 ? 24 : (i===1 ? 12 : Math.max(10, h.length+2)) }}));
  ws['!autofilter'] = {{ ref: XLSX.utils.encode_range({{s:{{r:0,c:0}}, e:{{r:nRows-1, c:nCols-1}}}}) }};
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Watchlist');
  XLSX.writeFile(wb, 'stock-watchlist-' + new Date().toISOString().slice(0,10) + '.xlsx');
}}
</script>
</body>
</html>
"""


def main():
    cfg = load_config()
    print(f"[{dt.datetime.now():%Y-%m-%d %H:%M}] Scraping for site build...")
    data = refresh_all(verbose=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_html(cfg, data), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
