import sys
import logging
from datetime import datetime

from config import MAX_TICKERS_TO_RESEARCH
from database import (
    init_db, log_research, log_sell_signal,
    get_portfolio, get_recent_research,
)
from scraper import scrape_reddit
from financials import get_stock_data
from agent import research_ticker, generate_sell_analysis
from sitegen import generate_site

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def run():
    run_date = datetime.now().strftime("%Y-%m-%d")
    log.info(f"=== Stock Agent starting — {run_date} ===")

    init_db()

    log.info("Phase 1: Scraping sentiment sources...")
    try:
        sentiment_data = scrape_reddit()
    except Exception as e:
        log.error(f"Scraping failed: {e}")
        sentiment_data = {}

    log.info(f"Phase 2: Researching top {MAX_TICKERS_TO_RESEARCH} tickers...")
    researched = 0
    live_prices = {}

    for ticker, sentiment in list(sentiment_data.items())[:MAX_TICKERS_TO_RESEARCH]:
        log.info(f"  -> {ticker} ({sentiment['mentions']} mentions, score {sentiment['sentiment_score']})")

        financials = get_stock_data(ticker)
        if not financials:
            log.warning(f"  Skipping {ticker} — no financial data")
            continue

        analysis = research_ticker(ticker, sentiment, financials)
        if analysis["llm_summary"].startswith("ERROR"):
            log.error(f"  LLM error for {ticker}: {analysis['llm_summary']}")

        log_research(
            run_date=run_date,
            ticker=ticker,
            data={
                **sentiment,
                **analysis,
                "price":       financials.get("price"),
                "pe_ratio":    financials.get("pe_ratio"),
                "week52_low":  financials.get("week52_low"),
                "week52_high": financials.get("week52_high"),
            },
        )
        researched += 1
        log.info(f"  OK {ticker} -> {analysis['verdict']}")

    log.info("Phase 3: Reviewing portfolio for sell signals...")
    portfolio = get_portfolio()

    for position in portfolio:
        ticker = position["ticker"]
        log.info(f"  -> Reviewing held position: {ticker}")
        financials = get_stock_data(ticker)
        if not financials:
            continue

        live_prices[ticker] = financials.get("price")
        recent = get_recent_research(ticker, days=30)
        result = generate_sell_analysis(ticker, position, financials, recent)

        log_sell_signal(
            run_date=run_date,
            ticker=ticker,
            signal=result["sell_signal"],
            reason=result["sell_analysis"][:500],
            price=financials.get("price"),
            pnl_pct=result["pnl_pct"],
        )
        if result["sell_signal"] in ("YES", "PARTIAL"):
            log.info(f"  SELL SIGNAL for {ticker}: {result['sell_signal']}")

    log.info("Phase 4: Generating static site...")
    generate_site(live_prices)

    log.info(f"=== Run complete. Researched {researched} tickers. ===")


if __name__ == "__main__":
    run()
