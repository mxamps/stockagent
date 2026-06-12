# Stock Intelligence Agent (Cloud Edition)

Runs entirely on GitHub Actions + GitHub Pages. No server, no laptop required.

- Scrapes Reddit + StockTwits sentiment every weekday at 7am NZT
- Researches top tickers with Groq (free LLM API)
- Tracks your portfolio (edit positions.json) and flags sell signals
- Publishes a static dashboard to GitHub Pages with full history
- Everything (code, database, reports) lives in this repo

## One-time setup

### 1. Create the repo

Go to github.com/new, name it `stockagent` (private or public — Pages works
on public repos for free; private repos need GitHub Pro for Pages).
Recommended: public, since the dashboard is meant to be public anyway.

Then from this folder:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/mxamps/stockagent.git
git push -u origin main
```

### 2. Add your Groq API key as a secret

Repo page -> Settings -> Secrets and variables -> Actions -> New repository secret
- Name: GROQ_API_KEY
- Value: gsk_... (your key)

### 3. Enable GitHub Pages

Repo page -> Settings -> Pages
- Source: "Deploy from a branch"
- Branch: main, folder: /docs
- Save

Your dashboard will be at: https://mxamps.github.io/stockagent/

### 4. Allow Actions to push commits

Repo page -> Settings -> Actions -> General -> Workflow permissions
- Select "Read and write permissions"
- Save

### 5. Test it

Repo page -> Actions -> "Daily Stock Report" -> Run workflow

Watch it run (~3-5 minutes). When it finishes, the dashboard will be live at
your Pages URL within a minute or two.

## Managing your portfolio

Edit positions.json (on github.com directly from your phone or laptop):

```json
{
  "positions": [
    { "ticker": "NVDA", "shares": 5, "avg_cost": 1180.50, "buy_date": "2026-06-01", "notes": "Bought on dip" },
    { "ticker": "INCY", "shares": 20, "avg_cost": 71.20, "buy_date": "2026-06-06", "notes": "" }
  ]
}
```

Commit the change. The next daily run will track P&L and check for sell signals.

## Schedule

The workflow runs at 19:00 UTC Sunday-Thursday, which is 7:00 AM Monday-Friday
NZST. When NZ daylight saving starts (late September, UTC+13), edit
.github/workflows/daily.yml and change "0 19" to "0 18" to keep 7am local.

Note: GitHub Actions cron can be delayed by up to ~15 minutes during busy
periods. The report will be there by ~7:15am worst case.

## Costs

- GitHub Actions: free (this uses ~100 of your 2,000 free minutes/month)
- GitHub Pages: free
- Groq API: free tier (14,400 requests/day; this uses ~15/day)
- Data sources: free (Reddit RSS, StockTwits public API, Yahoo Finance)

## Disclaimer

This tool aggregates social media sentiment, which is noisy and easily
manipulated. The AI-generated verdicts are not financial advice. Do your
own research.
