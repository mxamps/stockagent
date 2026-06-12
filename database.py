import sqlite3
import json
import os
from datetime import datetime
from config import DB_PATH, POSITIONS_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS research_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date        TEXT    NOT NULL,
                ticker          TEXT    NOT NULL,
                market          TEXT,
                mentions        INTEGER,
                sentiment_score REAL,
                positive_ratio  REAL,
                llm_summary     TEXT,
                verdict         TEXT,
                price_at_run    REAL,
                pe_ratio        REAL,
                week52_low      REAL,
                week52_high     REAL
            );

            CREATE TABLE IF NOT EXISTS sell_signals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date    TEXT    NOT NULL,
                ticker      TEXT    NOT NULL,
                signal      TEXT,
                reason      TEXT,
                price       REAL,
                pnl_pct     REAL
            );
        """)
    print("[DB] Initialised.")


def get_portfolio():
    if not os.path.exists(POSITIONS_PATH):
        return []
    try:
        with open(POSITIONS_PATH) as f:
            data = json.load(f)
        return data.get("positions", [])
    except Exception as e:
        print(f"[DB] Could not read {POSITIONS_PATH}: {e}")
        return []


def log_research(run_date, ticker, data):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO research_log
                (run_date, ticker, market, mentions, sentiment_score, positive_ratio,
                 llm_summary, verdict, price_at_run, pe_ratio, week52_low, week52_high)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_date, ticker,
            data.get("market", "US"),
            data.get("mentions"), data.get("sentiment_score"), data.get("positive_ratio"),
            data.get("llm_summary"), data.get("verdict"),
            data.get("price"), data.get("pe_ratio"),
            data.get("week52_low"), data.get("week52_high"),
        ))


def log_sell_signal(run_date, ticker, signal, reason, price, pnl_pct):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO sell_signals (run_date, ticker, signal, reason, price, pnl_pct)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (run_date, ticker, signal, reason, price, pnl_pct))


def get_recent_research(ticker, days=30):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT * FROM research_log
            WHERE ticker = ?
              AND run_date >= date('now', ?)
            ORDER BY run_date DESC
        """, (ticker, f"-{days} days")).fetchall()]


def get_all_runs():
    with get_conn() as conn:
        return [r["run_date"] for r in conn.execute("""
            SELECT DISTINCT run_date FROM research_log ORDER BY run_date DESC
        """).fetchall()]


def get_run(run_date):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT * FROM research_log WHERE run_date = ? ORDER BY mentions DESC
        """, (run_date,)).fetchall()]


def get_sell_signals_for_run(run_date):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("""
            SELECT * FROM sell_signals WHERE run_date = ?
        """, (run_date,)).fetchall()]
