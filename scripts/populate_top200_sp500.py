#!/usr/bin/env python3
"""
Populate scripts/watchlist_config.json with top 200 S&P500 tickers by market cap.
Fetches S&P500 list from Wikipedia, queries marketCap using yfinance in batches,
sorts and writes top 200 tickers.
"""
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / 'scripts' / 'watchlist_config.json'

try:
    import pandas as pd
    import yfinance as yf
except Exception as e:
    print('Missing dependency:', e)
    raise

WIKI_URL = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'


def load_sp500():
    print('Fetching S&P 500 list from Wikipedia...')
    tables = pd.read_html(WIKI_URL)
    # The first table is the constituents
    df = tables[0]
    # The ticker symbol column is 'Symbol'
    symbols = df['Symbol'].astype(str).tolist()
    # Clean tickers: some have dots e.g., BRK.B -> BRK-B for yfinance
    cleaned = [s.replace('.', '-') .strip() for s in symbols]
    return cleaned


def chunked(iterable, n):
    for i in range(0, len(iterable), n):
        yield iterable[i:i+n]


def fetch_market_caps(symbols):
    out = {}
    for batch in chunked(symbols, 50):
        tickers = ' '.join(batch)
        print('Query batch:', batch[:3], '...')
        tk = yf.Tickers(tickers)
        # tk.tickers is dict-like with each attribute
        for s in batch:
            try:
                t = tk.tickers.get(s)
                if not t:
                    # fallback to individual
                    tt = yf.Ticker(s)
                    info = tt.info or {}
                else:
                    info = t.info or {}
                mc = info.get('marketCap')
                out[s] = mc if mc is not None else 0
            except Exception as e:
                print('Error fetching', s, e)
                out[s] = 0
        time.sleep(1)
    return out


def main():
    symbols = load_sp500()
    market_caps = fetch_market_caps(symbols)
    # Sort symbols by market cap desc
    sorted_syms = sorted(symbols, key=lambda s: market_caps.get(s, 0) or 0, reverse=True)
    top200 = sorted_syms[:200]
    print('Top 10:', top200[:10])
    # write to config
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf8') as f:
        json.dump(top200, f, ensure_ascii=False, indent=2)
    print('Wrote', CONFIG_PATH)

if __name__ == '__main__':
    main()
