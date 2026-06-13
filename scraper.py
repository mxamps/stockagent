import time
import requests
from datetime import datetime, timedelta
from config import (
    WATCHLIST, FINNHUB_API_KEY, FINNHUB_BASE,
    MIN_NEWS_ARTICLES, MIN_SENTIMENT_SCORE,
)

# Lightweight positive/negative word lists for scoring headlines, used as a
# fallback when Finnhub's premium sentiment endpoint isn't available on the
# free tier. Applied to company-news headlines we CAN fetch for free.
POSITIVE_WORDS = {
    "beat", "beats", "surge", "surges", "soar", "soars", "jump", "jumps",
    "rally", "rallies", "gain", "gains", "rise", "rises", "upgrade",
    "upgraded", "outperform", "buy", "bullish", "record", "high", "growth",
    "profit", "strong", "boost", "boosts", "win", "wins", "approval",
    "approved", "breakthrough", "expand", "expands", "raise", "raised",
    "top", "tops", "exceed", "exceeds", "momentum", "rebound", "optimistic",
}
NEGATIVE_WORDS = {
    "miss", "misses", "fall", "falls", "drop", "drops", "plunge", "plunges",
    "slump", "crash", "decline", "declines", "downgrade", "downgraded",
    "sell", "bearish", "low", "loss", "losses", "weak", "cut", "cuts",
    "lawsuit", "investigation", "probe", "warn", "warns", "warning",
    "concern", "concerns", "risk", "risks", "slowdown", "layoff", "layoffs",
    "recall", "delay", "delays", "fraud", "scandal", "tumble", "sink",
}


def _get(endpoint, params):
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
        except Exception as e:
            if attempt == 2:
                print(f"[Scraper]   {endpoint} error for {params.get('symbol','')}: {e}")
                return None
            time.sleep(1.5)
    return None


def _score_headline(text):
    words = set(text.lower().replace(",", " ").replace(".", " ").split())
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def _fetch_company_news(ticker):
    """Free endpoint: company news from the last 7 days."""
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    data = _get("company-news", {
        "symbol": ticker,
        "from": week_ago.isoformat(),
        "to": today.isoformat(),
    })
    if not isinstance(data, list):
        return []
    return data


def scrape_reddit():
    """Name kept for pipeline compatibility. Sources sentiment from Finnhub news."""
    if not FINNHUB_API_KEY:
        print("[Scraper] ERROR: FINNHUB_API_KEY not set.")
        return {}

    results = {}
    print(f"[Scraper] Scanning {len(WATCHLIST)} tickers via Finnhub company news...")

    for ticker in WATCHLIST:
        news = _fetch_company_news(ticker)
        if len(news) < MIN_NEWS_ARTICLES:
            time.sleep(0.2)
            continue

        # Score the most recent ~20 headlines
        recent = news[:20]
        scores = []
        headlines = []
        for article in recent:
            headline = article.get("headline", "")
            if not headline:
                continue
            scores.append(_score_headline(headline))
            headlines.append(headline)

        if len(scores) < MIN_NEWS_ARTICLES:
            time.sleep(0.2)
            continue

        avg_score = sum(scores) / len(scores)
        positive_ratio = sum(1 for s in scores if s > 0) / len(scores)

        if avg_score < MIN_SENTIMENT_SCORE:
            time.sleep(0.2)
            continue

        # Keep the most positive headlines as sources for the LLM
        ranked = sorted(zip(scores, headlines), key=lambda x: x[0], reverse=True)
        top_headlines = [h for _, h in ranked[:5]]

        results[ticker] = {
            "mentions": len(scores),          # number of news articles
            "sentiment_score": round(avg_score, 4),
            "positive_ratio": round(positive_ratio, 4),
            "sources": top_headlines,
            "market": "US",
            "article_count": len(news),
        }
        print(f"[Scraper]   {ticker}: {len(scores)} articles, sentiment {avg_score:+.2f}")
        time.sleep(0.3)

    # Sort by sentiment strength, then article volume
    results = dict(sorted(
        results.items(),
        key=lambda x: (x[1]["sentiment_score"], x[1]["mentions"]),
        reverse=True,
    ))
    print(f"[Scraper] Tickers with positive news sentiment: {len(results)}")
    return results
