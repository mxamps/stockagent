"""
financials.py — Fetch fundamental + price data via yfinance (free, no API key)
"""
import yfinance as yf


def get_stock_data(ticker: str) -> dict | None:
    """
    Return a dict of key financials for a ticker, or None if unavailable.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Bail out on empty responses (often means invalid ticker)
        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            print(f"[Financials] No data for {ticker}, skipping.")
            return None

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev_close = info.get("previousClose")
        day_change_pct = None
        if price and prev_close:
            day_change_pct = round((price - prev_close) / prev_close * 100, 2)

        # Recent price history (30 days) for trend context
        hist = stock.history(period="30d")
        price_30d_ago = float(hist["Close"].iloc[0]) if not hist.empty else None
        month_change_pct = None
        if price and price_30d_ago:
            month_change_pct = round((price - price_30d_ago) / price_30d_ago * 100, 2)

        return {
            "ticker":           ticker,
            "name":             info.get("longName", ticker),
            "sector":           info.get("sector", "Unknown"),
            "price":            round(price, 2) if price else None,
            "day_change_pct":   day_change_pct,
            "month_change_pct": month_change_pct,
            "market_cap":       info.get("marketCap"),
            "pe_ratio":         info.get("trailingPE"),
            "forward_pe":       info.get("forwardPE"),
            "peg_ratio":        info.get("pegRatio"),
            "pb_ratio":         info.get("priceToBook"),
            "week52_low":       info.get("fiftyTwoWeekLow"),
            "week52_high":      info.get("fiftyTwoWeekHigh"),
            "avg_volume":       info.get("averageVolume"),
            "volume":           info.get("volume"),
            "revenue_growth":   info.get("revenueGrowth"),
            "earnings_growth":  info.get("earningsGrowth"),
            "profit_margin":    info.get("profitMargins"),
            "debt_to_equity":   info.get("debtToEquity"),
            "short_ratio":      info.get("shortRatio"),
            "analyst_target":   info.get("targetMeanPrice"),
            "recommendation":   info.get("recommendationKey"),
            "summary":          (info.get("longBusinessSummary") or "")[:400],
        }

    except Exception as e:
        print(f"[Financials] Error fetching {ticker}: {e}")
        return None


def fmt_market_cap(val) -> str:
    if val is None:
        return "N/A"
    if val >= 1_000_000_000_000:
        return f"${val/1e12:.1f}T"
    if val >= 1_000_000_000:
        return f"${val/1e9:.1f}B"
    return f"${val/1e6:.0f}M"
