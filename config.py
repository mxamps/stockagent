import os

SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "SecurityAnalysis",
]

ASX_NZ_SUBREDDITS = [
    "ASX_Bets",
    "queenstreetbets",
]

POSTS_PER_SUB = 100

MIN_TICKER_MENTIONS  = 3
MIN_SENTIMENT_SCORE  = 0.05
MIN_POSITIVE_RATIO   = 0.50

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.1-8b-instant"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
LLM_TIMEOUT  = 60

MAX_TICKERS_TO_RESEARCH = 10

DB_PATH = "data/portfolio.db"
POSITIONS_PATH = "positions.json"
SITE_DIR = "docs"

TICKER_BLACKLIST = {
    "AI", "IT", "ON", "GO", "OR", "ARE", "FOR", "NEW", "NOW",
    "ALL", "OUT", "BIG", "RUN", "OIL", "GAS", "BUY", "CEO",
    "IMO", "TBH", "LOL", "DD", "EPS", "IPO", "ETF", "WSB",
}
