import re
import time
import requests
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_URL, LLM_TIMEOUT

SYSTEM_PROMPT = """You are a decisive, data-driven stock research analyst.
You receive recent news sentiment data and key financial metrics for a stock.
Your job is to write a SHORT (150-200 word) analyst note and commit to a verdict.

Rules:
- Be honest about risks, but COMMIT to a clear view. Do not default to WATCH out of caution.
- Weigh fundamentals (valuation, growth, margins, analyst view) together with news sentiment.
- Base your verdict ONLY on the data provided.
- Aim for a realistic spread: genuinely attractive setups are BUY, clearly troubled or
  overvalued ones are AVOID, and only truly mixed cases are WATCH.
- Always end with one of exactly these verdicts on its own line:
  VERDICT: BUY
  VERDICT: WATCH
  VERDICT: AVOID
- BUY = reasonable valuation AND (solid growth OR clearly positive catalyst) AND supportive news
- AVOID = stretched valuation with weak growth, deteriorating fundamentals, or negative news flow
- WATCH = genuinely mixed signals where neither BUY nor AVOID is justified"""


def _call_groq(prompt):
    if not GROQ_API_KEY:
        return "ERROR: GROQ_API_KEY environment variable is not set."
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 500,
    }
    for attempt in range(4):
        try:
            resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=LLM_TIMEOUT)
            if resp.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"[Agent]   Groq 429, waiting {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt == 3:
                return f"ERROR: {e}"
            time.sleep(3)
    return "ERROR: Groq rate limit exceeded after retries."


def _extract_verdict(text):
    match = re.search(r"VERDICT:\s*(BUY|WATCH|AVOID)", text, re.IGNORECASE)
    return match.group(1).upper() if match else "WATCH"


def _fmt_pct(val):
    if val is None:
        return "N/A"
    return f"{val:+.1f}%"


def research_ticker(ticker, sentiment, financials):
    snippets = "\n".join(f"  - {s}" for s in sentiment.get("sources", [])[:3])

    prompt = f"""
Research request for: {ticker} ({financials.get('name', ticker)})
Sector: {financials.get('sector', 'N/A')}
Market: {sentiment.get('market', 'US')}

=== NEWS SENTIMENT (last 7 days) ===
Articles analysed: {sentiment['mentions']}
Average headline sentiment (-1 to +1): {sentiment['sentiment_score']}
Positive headline ratio: {sentiment['positive_ratio']*100:.0f}%
Top headlines:
{snippets}

=== FINANCIALS (Yahoo Finance) ===
Price:          ${financials.get('price', 'N/A')}
Day change:     {_fmt_pct(financials.get('day_change_pct'))}
Month change:   {_fmt_pct(financials.get('month_change_pct'))}
Market cap:     {financials.get('market_cap', 'N/A')}
P/E (trailing): {financials.get('pe_ratio', 'N/A')}
P/E (forward):  {financials.get('forward_pe', 'N/A')}
PEG ratio:      {financials.get('peg_ratio', 'N/A')}
52w range:      ${financials.get('week52_low', '?')} - ${financials.get('week52_high', '?')}
Revenue growth: {_fmt_pct(financials.get('revenue_growth'))}
Earnings growth:{_fmt_pct(financials.get('earnings_growth'))}
Profit margin:  {_fmt_pct(financials.get('profit_margin'))}
Analyst target: ${financials.get('analyst_target', 'N/A')}
Analyst rec:    {financials.get('recommendation', 'N/A')}
Short ratio:    {financials.get('short_ratio', 'N/A')}
Debt/Equity:    {financials.get('debt_to_equity', 'N/A')}

Company: {financials.get('summary', 'N/A')}

Write your analyst note now, ending with VERDICT: BUY / WATCH / AVOID.
"""

    print(f"[Agent] Researching {ticker}...")
    response = _call_groq(prompt)
    verdict = _extract_verdict(response)

    return {
        "llm_summary": response,
        "verdict": verdict,
    }


def generate_sell_analysis(ticker, position, financials, recent_sentiment):
    avg_cost = position.get("avg_cost", 0)
    current_price = financials.get("price", 0)
    pnl_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost else 0

    sentiment_trend = "No recent data"
    if recent_sentiment:
        scores = [r["sentiment_score"] for r in recent_sentiment if r["sentiment_score"]]
        if scores:
            avg = sum(scores) / len(scores)
            sentiment_trend = f"Avg sentiment over last 30 days: {avg:.3f}"

    prompt = f"""
You are reviewing a held stock position for a potential SELL signal.

Ticker: {ticker}
Shares held: {position.get('shares')}
Avg buy price: ${avg_cost}
Current price: ${current_price}
Unrealised P&L: {pnl_pct:+.1f}%
Buy date: {position.get('buy_date', 'Unknown')}

Current financials:
- P/E: {financials.get('pe_ratio', 'N/A')}
- Month change: {_fmt_pct(financials.get('month_change_pct'))}
- Short ratio: {financials.get('short_ratio', 'N/A')}
- Analyst rec: {financials.get('recommendation', 'N/A')}

News sentiment trend: {sentiment_trend}

Should this position be sold? Write a 100-word note.
End with exactly one of:
SELL_SIGNAL: YES
SELL_SIGNAL: NO
SELL_SIGNAL: PARTIAL
"""

    response = _call_groq(prompt)
    match = re.search(r"SELL_SIGNAL:\s*(YES|NO|PARTIAL)", response, re.IGNORECASE)
    signal = match.group(1).upper() if match else "NO"

    return {
        "sell_analysis": response,
        "sell_signal": signal,
        "pnl_pct": round(pnl_pct, 2),
    }
