import time
import requests
from config import FINNHUB_API_KEY, FINNHUB_BASE


def _finnhub_get(endpoint, params):
    params["token"] = FINNHUB_API_KEY
    url = f"{FINNHUB_BASE}/{endpoint}"
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt == 2:
                return None
            time.sleep(1.5)
    return None


def get_stock_data(ticker):
    """Fetch quote + fundamentals from Finnhub. Returns None if unavailable."""
    if not FINNHUB_API_KEY:
        print("[Financials] FINNHUB_API_KEY not set.")
        return None

    quote = _finnhub_get("quote", {"symbol": ticker})
    if not quote or quote.get("c") in (None, 0):
        print(f"[Financials] No quote for {ticker}")
        return None

    profile = _finnhub_get("stock/profile2", {"symbol": ticker}) or {}
    metrics_resp = _finnhub_get("stock/metric", {"symbol": ticker, "metric": "all"}) or {}
    metrics = metrics_resp.get("metric", {}) if metrics_resp else {}

    price = quote.get("c")            # current price
    prev_close = quote.get("pc")      # previous close
    day_change_pct = quote.get("dp")  # daily percent change

    # Recommendation trends (free endpoint)
    rec = _finnhub_get("stock/recommendation", {"symbol": ticker})
    recommendation = "N/A"
    if isinstance(rec, list) and rec:
        latest = rec[0]
        buys = latest.get("strongBuy", 0) + latest.get("buy", 0)
        sells = latest.get("strongSell", 0) + latest.get("sell", 0)
        holds = latest.get("hold", 0)
        if buys > sells and buys > holds:
            recommendation = "buy"
        elif sells > buys:
            recommendation = "sell"
        else:
            recommendation = "hold"

    market_cap = profile.get("marketCapitalization")
    if market_cap:
        market_cap = market_cap * 1_000_000  # Finnhub gives millions

    return {
        "ticker":           ticker,
        "name":             profile.get("name", ticker),
        "sector":           profile.get("finnhubIndustry", "Unknown"),
        "price":            round(price, 2) if price else None,
        "day_change_pct":   round(day_change_pct, 2) if day_change_pct is not None else None,
        "month_change_pct": None,  # not directly available; left for future
        "market_cap":       market_cap,
        "pe_ratio":         metrics.get("peTTM"),
        "forward_pe":       metrics.get("peExclExtraTTM"),
        "peg_ratio":        None,
        "pb_ratio":         metrics.get("pbQuarterly"),
        "week52_low":       metrics.get("52WeekLow"),
        "week52_high":      metrics.get("52WeekHigh"),
        "avg_volume":       metrics.get("10DayAverageTradingVolume"),
        "volume":           None,
        "revenue_growth":   metrics.get("revenueGrowthTTMYoy"),
        "earnings_growth":  metrics.get("epsGrowthTTMYoy"),
        "profit_margin":    metrics.get("netProfitMarginTTM"),
        "debt_to_equity":   metrics.get("totalDebt/totalEquityQuarterly"),
        "short_ratio":      None,
        "analyst_target":   metrics.get("targetMeanPrice"),
        "recommendation":   recommendation,
        "summary":          f"{profile.get('name', ticker)} — {profile.get('finnhubIndustry', '')}. "
                            f"Listed on {profile.get('exchange', 'N/A')}.",
    }


def fmt_market_cap(val):
    if val is None:
        return "N/A"
    if val >= 1_000_000_000_000:
        return f"${val/1e12:.1f}T"
    if val >= 1_000_000_000:
        return f"${val/1e9:.1f}B"
    return f"${val/1e6:.0f}M"
