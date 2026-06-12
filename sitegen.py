import os
import json
from datetime import datetime
from config import SITE_DIR
from database import get_all_runs, get_run, get_sell_signals_for_run, get_portfolio

FAVICON = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMiAzMiI+CiAgPHJlY3Qgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiByeD0iNiIgZmlsbD0iIzFkNGVkOCIvPgogIDxwb2x5bGluZSBwb2ludHM9IjQsMjIgMTAsMTQgMTYsMTggMjIsOCAyOCwxMCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMjJjNTVlIiBzdHJva2Utd2lkdGg9IjIuNSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+CiAgPGNpcmNsZSBjeD0iMjgiIGN5PSIxMCIgcj0iMiIgZmlsbD0iIzIyYzU1ZSIvPgo8L3N2Zz4="


def verdict_color(v):
    return {"BUY": "#16a34a", "WATCH": "#d97706", "AVOID": "#dc2626"}.get(v, "#6b7280")


def verdict_bg(v):
    return {"BUY": "#dcfce7", "WATCH": "#fef9c3", "AVOID": "#fee2e2"}.get(v, "#f3f4f6")


def pct_color(v):
    if v is None:
        return "#6b7280"
    return "#16a34a" if v >= 0 else "#dc2626"


def fmt_pct(v):
    if v is None:
        return "N/A"
    return f"{v:+.1f}%"


def _research_card(item):
    v = item.get("verdict", "WATCH")
    summary = item.get("llm_summary", "")
    clean = "\n".join(l for l in summary.split("\n") if not l.strip().startswith("VERDICT:")).strip()
    price = item.get("price_at_run")
    lo = item.get("week52_low")
    hi = item.get("week52_high")
    market = item.get("market", "US")

    bar = ""
    if lo and hi and price and hi != lo:
        pct = max(0, min(100, (price - lo) / (hi - lo) * 100))
        bar = f"""
        <div style="margin-top:12px">
          <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">52-week range &nbsp; ${lo} - ${hi}</div>
          <div style="background:#e5e7eb;border-radius:4px;height:6px;position:relative">
            <div style="background:#3b82f6;width:{pct:.0f}%;height:6px;border-radius:4px"></div>
          </div>
        </div>"""

    market_badge = ""
    if market == "AU/NZ":
        market_badge = '<span style="background:#e0f2fe;color:#0369a1;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;margin-left:8px">AU/NZ</span>'

    return f"""
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px 24px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.06)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px">
        <div>
          <span style="font-size:22px;font-weight:800;color:#111">{item['ticker']}</span>
          {market_badge}
        </div>
        <span style="background:{verdict_bg(v)};color:{verdict_color(v)};padding:4px 14px;border-radius:20px;font-weight:700;font-size:14px">{v}</span>
      </div>
      <div style="display:flex;gap:24px;margin-bottom:14px;flex-wrap:wrap">
        <div><div style="font-size:11px;color:#9ca3af;text-transform:uppercase">Price</div>
          <div style="font-size:18px;font-weight:700">${price or 'N/A'}</div></div>
        <div><div style="font-size:11px;color:#9ca3af;text-transform:uppercase">P/E</div>
          <div style="font-size:18px;font-weight:700">{round(item['pe_ratio'], 1) if item.get('pe_ratio') else 'N/A'}</div></div>
        <div><div style="font-size:11px;color:#9ca3af;text-transform:uppercase">Mentions</div>
          <div style="font-size:18px;font-weight:700">{item.get('mentions') or 'N/A'}</div></div>
        <div><div style="font-size:11px;color:#9ca3af;text-transform:uppercase">Sentiment</div>
          <div style="font-size:18px;font-weight:700;color:{pct_color(item.get('sentiment_score', 0))}">{item.get('sentiment_score') or 'N/A'}</div></div>
      </div>
      <div style="background:#f9fafb;border-left:4px solid {verdict_color(v)};border-radius:4px;padding:12px 16px;font-size:13px;color:#374151;line-height:1.6;white-space:pre-wrap">{clean}</div>
      {bar}
    </div>"""


def _sell_card(s):
    sig = s.get("signal", "NO")
    colors = {"YES": ("#dc2626", "#fee2e2"), "PARTIAL": ("#d97706", "#fef9c3")}
    fg, bg = colors.get(sig, ("#16a34a", "#dcfce7"))
    pnl = s.get("pnl_pct")
    return f"""
    <div style="background:#fff;border:1px solid #fca5a5;border-radius:10px;padding:16px 20px;margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <div>
          <span style="font-weight:700;font-size:16px">{s['ticker']}</span>
          <span style="background:{bg};color:{fg};padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700;margin-left:8px">{sig}</span>
        </div>
        <span style="font-size:13px;font-weight:700;color:{pct_color(pnl)}">P&L {fmt_pct(pnl)}</span>
      </div>
      <p style="font-size:13px;color:#374151;margin:8px 0 0;line-height:1.6;white-space:pre-wrap">{s.get('reason', '')}</p>
    </div>"""


def _portfolio_table(portfolio, live_prices):
    if not portfolio:
        return ""
    rows = ""
    for pos in portfolio:
        ticker = pos["ticker"]
        avg = pos.get("avg_cost", 0)
        shares = pos.get("shares", 0)
        curr = live_prices.get(ticker)
        if curr and avg:
            pnl_pct = (curr - avg) / avg * 100
            pnl_dollar = (curr - avg) * shares
            pnl_str = fmt_pct(pnl_pct)
            dollar_str = f"${pnl_dollar:+.0f}"
            color = pct_color(pnl_pct)
            curr_str = f"${curr}"
        else:
            pnl_str = dollar_str = curr_str = "N/A"
            color = "#6b7280"
        rows += f"""
        <tr style="border-bottom:1px solid #f3f4f6">
          <td style="padding:10px 8px;font-weight:700">{ticker}</td>
          <td style="padding:10px 8px">{shares}</td>
          <td style="padding:10px 8px">${avg}</td>
          <td style="padding:10px 8px">{curr_str}</td>
          <td style="padding:10px 8px;color:{color};font-weight:600">{pnl_str}</td>
          <td style="padding:10px 8px;color:{color};font-weight:600">{dollar_str}</td>
          <td style="padding:10px 8px;color:#9ca3af;font-size:12px">{pos.get('notes', '')}</td>
        </tr>"""

    return f"""
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px 24px;margin-bottom:28px;overflow-x:auto">
      <h2 style="margin:0 0 16px;font-size:16px;font-weight:700">My Portfolio</h2>
      <table style="width:100%;border-collapse:collapse;font-size:13px;min-width:560px">
        <thead>
          <tr style="border-bottom:2px solid #e5e7eb;color:#9ca3af;font-size:11px;text-transform:uppercase">
            <th style="padding:8px;text-align:left">Ticker</th>
            <th style="padding:8px;text-align:left">Shares</th>
            <th style="padding:8px;text-align:left">Avg Cost</th>
            <th style="padding:8px;text-align:left">Current</th>
            <th style="padding:8px;text-align:left">P&L %</th>
            <th style="padding:8px;text-align:left">P&L $</th>
            <th style="padding:8px;text-align:left">Notes</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""


def build_run_page(run_date, all_runs, portfolio, live_prices, is_index=False):
    items = get_run(run_date)
    sells = get_sell_signals_for_run(run_date)

    buy_cards   = "".join(_research_card(r) for r in items if r.get("verdict") == "BUY")   or "<p style='color:#9ca3af;padding:12px'>None this run.</p>"
    watch_cards = "".join(_research_card(r) for r in items if r.get("verdict") == "WATCH") or "<p style='color:#9ca3af;padding:12px'>None this run.</p>"
    avoid_cards = "".join(_research_card(r) for r in items if r.get("verdict") == "AVOID") or "<p style='color:#9ca3af;padding:12px'>None this run.</p>"
    sell_cards  = "".join(_sell_card(s) for s in sells)

    n_buy   = sum(1 for r in items if r.get("verdict") == "BUY")
    n_watch = sum(1 for r in items if r.get("verdict") == "WATCH")
    n_avoid = sum(1 for r in items if r.get("verdict") == "AVOID")

    run_options = "".join(
        f'<option value="{"index" if r == all_runs[0] else r}.html" {"selected" if r == run_date else ""}>{r}</option>'
        for r in all_runs
    )

    sell_section = ""
    if sell_cards:
        sell_section = f"""
        <h3>Portfolio Sell Signals</h3>
        {sell_cards}"""

    portfolio_section = _portfolio_table(portfolio, live_prices) if is_index else ""

    generated = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<link rel="icon" href="{FAVICON}">
<title>Stock Intelligence — {run_date}</title>
<style>
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f3f4f6;margin:0;padding:0;color:#111 }}
  .wrap {{ max-width:760px;margin:0 auto;padding:24px 16px }}
  select {{ background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:6px 12px;font-size:13px;cursor:pointer }}
  h3 {{ font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#9ca3af;margin:28px 0 12px }}
</style>
</head><body><div class="wrap">

  <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:14px 18px;margin-bottom:20px;font-size:12px;color:#92400e;line-height:1.6">
    <strong>Not financial advice.</strong> This page is generated automatically by an AI agent
    from social media sentiment (Reddit, StockTwits) and public financial data. Social sentiment
    is a noisy, unreliable signal and AI-generated analysis can be wrong. Nothing here is a
    recommendation to buy or sell any security. Always do your own research and consider
    consulting a licensed financial adviser.
  </div>

  <div style="background:linear-gradient(135deg,#1e3a5f,#1d4ed8);border-radius:14px;padding:28px;margin-bottom:24px;color:#fff">
    <div style="font-size:11px;opacity:.7;text-transform:uppercase;letter-spacing:.1em">Stock Intelligence Report</div>
    <div style="font-size:26px;font-weight:800;margin:6px 0">{run_date}</div>
    <div style="display:flex;align-items:center;gap:12px;margin-top:8px;flex-wrap:wrap">
      <div style="opacity:.8;font-size:13px">History:</div>
      <select onchange="window.location.href=this.value">{run_options}</select>
    </div>
    <div style="display:flex;gap:12px;margin-top:18px;flex-wrap:wrap">
      <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:8px 16px;text-align:center">
        <div style="font-size:20px;font-weight:800">{len(items)}</div>
        <div style="font-size:11px;opacity:.8">Tickers</div>
      </div>
      <div style="background:rgba(22,163,74,.3);border-radius:8px;padding:8px 16px;text-align:center">
        <div style="font-size:20px;font-weight:800">{n_buy}</div>
        <div style="font-size:11px;opacity:.8">BUY</div>
      </div>
      <div style="background:rgba(217,119,6,.3);border-radius:8px;padding:8px 16px;text-align:center">
        <div style="font-size:20px;font-weight:800">{n_watch}</div>
        <div style="font-size:11px;opacity:.8">WATCH</div>
      </div>
      <div style="background:rgba(220,38,38,.3);border-radius:8px;padding:8px 16px;text-align:center">
        <div style="font-size:20px;font-weight:800">{n_avoid}</div>
        <div style="font-size:11px;opacity:.8">AVOID</div>
      </div>
    </div>
  </div>

  {portfolio_section}
  {sell_section}

  <h3>Buy Recommendations</h3>
  {buy_cards}

  <h3>Watch List</h3>
  {watch_cards}

  <h3>Avoid</h3>
  {avoid_cards}

  <div style="margin-top:32px;padding:16px;background:#fff;border-radius:10px;font-size:11px;color:#9ca3af;line-height:1.6;border:1px solid #e5e7eb">
    Generated {generated} · Sources: r/wallstreetbets, r/stocks, r/investing, r/SecurityAnalysis,
    StockTwits trending, Yahoo Finance · Analysis: Groq llama-3.1-8b · Not financial advice.
  </div>

</div></body></html>"""


def generate_site(live_prices=None):
    live_prices = live_prices or {}
    os.makedirs(SITE_DIR, exist_ok=True)
    all_runs = get_all_runs()
    if not all_runs:
        print("[Sitegen] No runs in database yet.")
        return

    portfolio = get_portfolio()

    for i, run_date in enumerate(all_runs):
        is_latest = (i == 0)
        html = build_run_page(run_date, all_runs, portfolio, live_prices, is_index=is_latest)
        filename = "index.html" if is_latest else f"{run_date}.html"
        with open(os.path.join(SITE_DIR, filename), "w") as f:
            f.write(html)

    # .nojekyll stops GitHub Pages from processing the folder
    with open(os.path.join(SITE_DIR, ".nojekyll"), "w") as f:
        f.write("")

    print(f"[Sitegen] Generated {len(all_runs)} pages in {SITE_DIR}/")
