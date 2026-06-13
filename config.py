import os

# A curated watchlist of liquid, widely-followed tickers to scan each run.
# Finnhub gives us news sentiment + fundamentals for each; the most positive
# movers bubble up into the daily report.
WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "NFLX",
    "AVGO", "MU", "INTC", "QCOM", "ARM", "SMCI", "PLTR", "CRM", "ORCL",
    "ADBE", "NOW", "SHOP", "UBER", "ABNB", "COIN", "HOOD", "SOFI", "PYPL",
    "JPM", "BAC", "V", "MA", "DIS", "BABA", "NU", "MELI", "INCY", "MRVL",
    "MSTR", "SNOW", "DDOG", "NET", "CRWD", "PANW", "SMR", "VST", "CEG",
    "LLY", "UNH", "JNJ", "PFE", "MRNA", "XOM", "CVX", "BA", "GE", "F",
]

# Sentiment thresholds (tuned for Finnhub news sentiment, not VADER)
MIN_NEWS_ARTICLES   = 3      # need at least this many recent articles
MIN_SENTIMENT_SCORE = 0.0    # Finnhub sentiment is roughly -1..1; >0 = net positive

GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL     = "llama-3.1-8b-instant"
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
LLM_TIMEOUT    = 60

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")
FINNHUB_BASE    = "https://finnhub.io/api/v1"

MAX_TICKERS_TO_RESEARCH = 10

DB_PATH = "data/portfolio.db"
POSITIONS_PATH = "positions.json"
SITE_DIR = "docs"
