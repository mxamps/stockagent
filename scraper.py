import re
import time
import requests
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from collections import defaultdict
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from config import (
    SUBREDDITS, ASX_NZ_SUBREDDITS, TICKER_BLACKLIST,
    MIN_TICKER_MENTIONS, MIN_SENTIMENT_SCORE, MIN_POSITIVE_RATIO,
)

analyzer = SentimentIntensityAnalyzer()
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

NOISE_WORDS = TICKER_BLACKLIST | {
    "TO", "OF", "IS", "IN", "BY", "AT", "BE", "DO", "IF", "NO", "SO", "UP",
    "WE", "ME", "MY", "HE", "IT", "AN", "AS", "AM", "US", "VS", "RE", "MR",
    "THE", "AND", "NOT", "BUT", "WITH", "FROM", "THIS", "THAT", "THEY", "HAVE",
    "WILL", "WHAT", "WHEN", "YOUR", "JUST", "LIKE", "SOME", "MORE", "THAN",
    "INTO", "OVER", "ALSO", "DOES", "AFTER", "BACK", "MUCH", "WELL", "EVEN",
    "MOST", "SUCH", "TAKE", "MAKE", "GOOD", "HIGH", "LAST", "LONG", "LOOK",
    "COME", "ONLY", "YEAR", "WEEK", "DAYS", "TIME", "SAID", "EACH", "MANY",
    "SAME", "VERY", "FREE", "REAL", "NEXT", "NEAR", "BEST", "KEEP", "OPEN",
    "CASH", "RATE", "FUND", "PLAN", "BEAT", "HELP", "HOLD", "RISK", "LOSS",
    "GAIN", "CALL", "PUTS", "MOVE", "PLAY", "BEAR", "BULL", "WIFE", "YOLO",
    "FOMO", "HODL", "THEIR", "ABOUT", "WOULD", "THERE", "WHICH", "WERE",
    "BEEN", "THEN", "THEM", "THESE", "THOSE", "HTTPS", "HTTP", "HTML",
    "HREF", "USER", "DIV", "TABLE", "LINK", "POST", "VOTE", "EDIT", "TAGS",
    "SEC", "FDA", "FED", "GDP", "CPI", "NYSE", "DJIA", "CNBC", "IMF",
    "USA", "USD", "EUR", "GBP", "AUD", "CAD", "JPY", "NZD", "YTD", "TTM",
    "LEAPS", "CALLS", "PUTS", "YOLO", "MEME", "MOON", "DUMP", "PUMP",
    "ATH", "ATL", "RSI", "EMA", "SMA", "MACD", "VWAP", "SPDR", "ARKK",
    "SAAS", "CORP", "INC", "LTD", "PLC", "LLC", "MKT", "CAP", "EPS",
    "YOY", "QOQ", "CAGR", "ROIC", "WACC", "DCF", "MGMT", "CEO", "CFO",
    "CTO", "COO", "BOD", "AGM", "EGM", "OTC", "AH", "PM", "EU", "AI",
    "IPO", "ETF", "REIT", "SPAC", "EBITDA", "DD", "WSB", "WSJ",
    "ASX", "NZX", "AFR", "RBA", "APRA", "ASIC", "ATO", "NBN",
    "ATM", "PIN", "GST", "CGT", "SMSF", "NRL", "AFL", "ABC", "SBS",
    "FOR", "ARE", "HAS", "HAD", "ITS", "WAS", "ONE", "TWO", "GET",
    "GOT", "PUT", "SET", "LET", "OLD", "WAY", "MAY", "DAY", "NOW",
    "HOW", "WHO", "WHY", "ANY", "TOO", "OFF", "OUR", "USE", "DID",
    "TRY", "SEE", "HIT", "TOP", "WIN", "FIT", "SIT", "CUT", "PAY",
    "TAX", "WAR", "LAW", "YOU", "CAN", "VE", "HERE", "DOWN", "TERM",
    "LONG", "PART", "WELL", "WORK", "NEED", "WANT", "WENT", "TOLD",
    "FEEL", "KNEW", "SURE", "LESS", "ZERO", "BOTH", "SIDE", "WEEK",
    "TAKE", "GIVE", "SHOW", "READ", "HEAR", "SELL", "HOLD", "WAIT",
    "STOP", "GROW", "FALL", "RISE", "DROP", "JUMP", "PUSH", "PULL",
}


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_text(self):
        return " ".join(self.text)


def _strip_html(html):
    s = _HTMLStripper()
    try:
        s.feed(html)
        return s.get_text()
    except Exception:
        return re.sub(r'<[^>]+>', ' ', html)


def _extract_dollar_tickers(text):
    tickers = set()
    for m in re.finditer(r'\$([A-Z]{1,5})\b', text):
        t = m.group(1)
        if t not in NOISE_WORDS and not t.endswith('.X'):
            tickers.add(t)
    return list(tickers)


def _extract_asx_tickers(text):
    tickers = set()

    for m in re.finditer(r'\$([A-Z]{2,4})\b', text):
        t = m.group(1)
        if t not in NOISE_WORDS:
            tickers.add(t)

    for m in re.finditer(r'\bASX:\s*([A-Z]{2,4})\b', text):
        t = m.group(1)
        if t not in NOISE_WORDS:
            tickers.add(t)

    for m in re.finditer(r'\bNZX:\s*([A-Z]{2,4})\b', text):
        t = m.group(1)
        if t not in NOISE_WORDS:
            tickers.add(t)

    for m in re.finditer(r'\b([A-Z]{2,4})\.ASX\b', text):
        t = m.group(1)
        if t not in NOISE_WORDS:
            tickers.add(t)

    for m in re.finditer(r'\b([A-Z]{2,4})\.NZX\b', text):
        t = m.group(1)
        if t not in NOISE_WORDS:
            tickers.add(t)

    return list(tickers)


def _score_text(text):
    return analyzer.polarity_scores(text)["compound"]


def _fetch_subreddit_rss(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/hot.rss?limit=50"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        posts = []
        for entry in entries:
            title = entry.findtext("atom:title", "", ns)
            content = _strip_html(entry.findtext("atom:content", "", ns))
            posts.append(f"{title} {content}")
        print(f"[Scraper] r/{subreddit}: got {len(posts)} posts")
        return posts
    except Exception as e:
        print(f"[Scraper] RSS failed for r/{subreddit}: {e}")
        return []


def _fetch_stocktwits_stream(ticker):
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            messages = resp.json().get("messages", [])
            return [m.get("body", "") for m in messages[:30]]
    except Exception:
        pass
    return []


def _fetch_stocktwits_trending():
    url = "https://api.stocktwits.com/api/2/trending/symbols.json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            symbols = resp.json().get("symbols", [])
            return [
                s.get("symbol", "") for s in symbols
                if s.get("symbol") and "." not in s.get("symbol", "")
            ]
    except Exception:
        pass
    return []


def scrape_reddit():
    raw = defaultdict(list)
    asx_raw = defaultdict(list)

    for sub_name in SUBREDDITS:
        print(f"[Scraper] Scanning r/{sub_name} ...")
        posts = _fetch_subreddit_rss(sub_name)
        for text in posts:
            tickers = _extract_dollar_tickers(text.upper())
            score = _score_text(text)
            for ticker in tickers:
                raw[ticker].append((score, text[:120]))
        time.sleep(2)

    for sub_name in ASX_NZ_SUBREDDITS:
        print(f"[Scraper] Scanning r/{sub_name} (AU/NZ) ...")
        posts = _fetch_subreddit_rss(sub_name)
        for text in posts:
            tickers = _extract_asx_tickers(text.upper())
            score = _score_text(text)
            for ticker in tickers:
                asx_raw[ticker].append((score, text[:120]))
        time.sleep(2)

    print(f"[Scraper] Adding StockTwits trending data...")
    trending = _fetch_stocktwits_trending()
    print(f"[Scraper] StockTwits trending: {trending[:10]}")

    for ticker in trending[:20]:
        if ticker in NOISE_WORDS:
            continue
        messages = _fetch_stocktwits_stream(ticker)
        for msg in messages:
            score = _score_text(msg)
            raw[ticker].append((score, msg[:120]))
        time.sleep(0.5)

    def _filter(source_raw, label):
        results = {}
        for ticker, entries in source_raw.items():
            if len(entries) < MIN_TICKER_MENTIONS:
                continue
            scores = [s for s, _ in entries]
            avg_score = sum(scores) / len(scores)
            positive_ratio = sum(1 for s in scores if s > 0) / len(scores)
            if avg_score < MIN_SENTIMENT_SCORE:
                continue
            if positive_ratio < MIN_POSITIVE_RATIO:
                continue
            results[ticker] = {
                "mentions": len(entries),
                "sentiment_score": round(avg_score, 4),
                "positive_ratio": round(positive_ratio, 4),
                "sources": [text for _, text in entries[:5]],
                "market": label,
            }
        return results

    us_results  = _filter(raw, "US")
    asx_results = _filter(asx_raw, "AU/NZ")

    combined = dict(sorted(
        {**us_results, **asx_results}.items(),
        key=lambda x: x[1]["mentions"],
        reverse=True,
    ))

    print(f"[Scraper] US tickers passing filters: {len(us_results)}")
    print(f"[Scraper] AU/NZ tickers passing filters: {len(asx_results)}")
    print(f"[Scraper] Total: {len(combined)}")
    return combined
