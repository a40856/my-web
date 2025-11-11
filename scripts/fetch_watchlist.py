#!/usr/bin/env python3
"""
Fetch watchlist tickers from scripts/watchlist_config.json using yfinance,
compute current price, market cap and 1-month change, then write to
docs/data/watchlist.json.

This script is safe to run in CI (GitHub Actions). It will overwrite the data file.
"""
import json
import os
from pathlib import Path
import traceback

try:
    import yfinance as yf
except Exception:
    raise

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / 'scripts' / 'watchlist_config.json'
OUT_PATH = ROOT / 'docs' / 'data' / 'watchlist.json'


def load_config():
    if not CONFIG_PATH.exists():
        return []
    with open(CONFIG_PATH, 'r', encoding='utf8') as f:
        return json.load(f)


def write_output(data):
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def safe_float(v):
    try:
        return float(v)
    except Exception:
        return None


def fetch_ticker(t):
    t = t.strip().upper()
    if not t:
        return None
    try:
        tk = yf.Ticker(t)
        # Current price - prefer fast_info if available
        price = None
        try:
            price = tk.fast_info.get('lastPrice')
        except Exception:
            pass
        if price is None:
            # fallback to last close
            hist = tk.history(period='1d')
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
        # One month history (also store series for frontend sparklines)
        one_month_change = None
        history = None
        try:
            hist_month = tk.history(period='1mo', interval='1d')
            closes = hist_month['Close'].dropna()
            if len(closes) >= 1 and price is not None:
                first = float(closes.iloc[0])
                if first != 0:
                    one_month_change = (float(price) - first) / first
            # keep last N closes (e.g., 30) as floats
            if len(closes) > 0:
                history = [float(x) for x in closes.tolist()]
                # limit to most recent 30
                if len(history) > 30:
                    history = history[-30:]
        except Exception:
            one_month_change = None
            history = None
        # info for name and marketCap
        info = {}
        try:
            info = tk.info or {}
        except Exception:
            info = {}
        name = info.get('shortName') or info.get('longName') or ''
        marketCap = info.get('marketCap')
        # percent change from previous close
        reg_prev = info.get('regularMarketPreviousClose')
        reg_pct = None
        if reg_prev and price is not None:
            try:
                reg_pct = (float(price) - float(reg_prev)) / float(reg_prev) * 100.0
            except Exception:
                reg_pct = None
        return {
            'symbol': t,
            'shortName': name,
            'regularMarketPrice': safe_float(price),
            'regularMarketChangePercent': safe_float(reg_pct),
            'marketCap': marketCap,
            'oneMonthChange': one_month_change,
            'history': history
        }
    except Exception:
        traceback.print_exc()
        return {
            'symbol': t,
            'shortName': '',
            'regularMarketPrice': None,
            'regularMarketChangePercent': None,
            'marketCap': None,
            'oneMonthChange': None,
            'error': 'fetch_failed'
        }


def main():
    tickers = load_config()
    if not isinstance(tickers, list):
        print('Config file malformed: expected list of tickers')
        return
    out = []
    for t in tickers:
        print('Fetching', t)
        row = fetch_ticker(t)
        if row:
            out.append(row)
    write_output(out)
    print('Wrote', OUT_PATH)


if __name__ == '__main__':
    main()
