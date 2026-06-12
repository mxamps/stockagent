import time
import random
import requests
from collections import defaultdict
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from config import (
    TICKER_BLACKLIST,
    MIN_TICKER_MENTIONS, MIN_SENTIMENT_SCORE, MIN_POSITIVE_RATIO,
)

analyzer = SentimentIntensityAnalyzer()

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
]


def _headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }


# A watchlist of liquid, commonly-discussed tickers as a reliable backbone.
# StockTwits trending is layered on top of this each run.
WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "NFLX",
    "AVGO", "MU", "INTC", "QCOM", "ARM", "SMCI", "PLTR", "CRM", "ORCL",
    "ADBE", "NOW", "SHOP", "UBER", "ABNB", "COIN", "HOOD", "SOFI", "PYPL",
    "JPM", "BAC", "V", "MA", "DIS", "BABA", "NU", "MELI", "INCY", "MRVL",
    "MSTR", "SNOW", "DDOG", "NET", "CRWD", "PANW", "SMR", "VST", "CEG",
    "LLY", "UNH", "JNJ", "PFE", "MRNA", "XOM", "CVX", "BA", "GE", "F",
]


def _get_with_retry(url, max_retries=3, base_delay=2):
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=_headers(), timeout=15)
            if resp.status_code == 429:
                wait = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"[Scraper]   429, waiting {wait:.0f}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt == max_retries - 1:
                return None
            time.sleep(base_delay * (2 ** attempt))
    return None


def _score_text(text):
    return analyzer.polarity_scores(text)["compound"]


def _fetch_stocktwits_trending():
    url = "https://api.stocktwits.com/api/2/trending/symbols.json"
    resp = _get_with_retry(url)
    if not resp:
        print("[Scraper] StockTwits trending unavailable")
        return []
    try:
        symbols = resp.json().get("symbols", [])
        return [s.get("symbol", "") for s in symbols
                if s.get("symbol") and "." not in s.get("symbol", "")]
    except Exception:
        return []


def _fetch_stocktwits_stream(ticker):
    """Returns (messages, st_sentiment_counts) for a ticker."""
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
    resp = _get_with_retry(url, max_retries=2)
    if not resp:
        return [], {"bull": 0, "bear": 0}
    try:
        data = resp.json()
        messages = data.get("messages", [])
        bodies = []
        bull = bear = 0
        for m in messages[:30]:
            bodies.append(m.get("body", ""))
            # StockTwits has its own bull/bear labels we can use as signal
            entities = m.get("entities", {})
            sentiment = (entities or {}).get("sentiment") or {}
            basic = sentiment.get("basic")
            if basic == "Bullish":
                bull += 1
            elif basic == "Bearish":
                bear += 1
        return bodies, {"bull": bull, "bear": bear}
    except Exception:
        return [], {"bull": 0, "bear": 0}


def scrape_reddit():
    """Name kept for compatibility. Now sources from StockTwits + watchlist."""
    raw = defaultdict(list)
    st_labels = {}

    print("[Scraper] Fetching StockTwits trending...")
    trending = _fetch_stocktwits_trending()
    print(f"[Scraper] Trending: {trending[:10]}")

    # Combine trending + watchlist, dedup, keep order (trending first)
    targets = list(dict.fromkeys(trending + WATCHLIST))
    print(f"[Scraper] Scanning {len(targets)} tickers on StockTwits...")

    for ticker in targets:
        if ticker in TICKER_BLACKLIST:
            continue
        messages, labels = _fetch_stocktwits_stream(ticker)
        if messages:
            for msg in messages:
                score = _score_text(msg)
                raw[ticker].append((score, msg[:150]))
            st_labels[ticker] = labels
        time.sleep(random.uniform(0.4, 1.0))

    print(f"[Scraper] Tickers with data: {len(raw)}")

    results = {}
    for ticker, entries in raw.items():
        if len(entries) < MIN_TICKER_MENTIONS:
            continue
        scores = [s for s, _ in entries]
        avg_score = sum(scores) / len(scores)
        positive_ratio = sum(1 for s in scores if s > 0) / len(scores)

        # Blend VADER with StockTwits' own bull/bear labels if present
        labels = st_labels.get(ticker, {"bull": 0, "bear": 0})
        total_labels = labels["bull"] + labels["bear"]
        if total_labels >= 3:
            st_ratio = labels["bull"] / total_labels
            # require both VADER and ST labels to be non-negative
            positive_ratio = (positive_ratio + st_ratio) / 2

        if avg_score < MIN_SENTIMENT_SCORE:
            continue
        if positive_ratio < MIN_POSITIVE_RATIO:
            continue

        results[ticker] = {
            "mentions": len(entries),
            "sentiment_score": round(avg_score, 4),
            "positive_ratio": round(positive_ratio, 4),
            "sources": [text for _, text in entries[:5]],
            "market": "US",
            "st_bull": labels["bull"],
            "st_bear": labels["bear"],
        }

    results = dict(sorted(results.items(), key=lambda x: x[1]["mentions"], reverse=True))
    print(f"[Scraper] Tickers passing filters: {len(results)}")
    return results
