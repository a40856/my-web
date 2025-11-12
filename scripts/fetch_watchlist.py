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
        # History series and multi-period changes (1M/3M/6M)
        one_month_change = None
        three_month_change = None
        six_month_change = None
        history = None
        try:
            hist_6mo = tk.history(period='6mo', interval='1d')
            closes = hist_6mo['Close'].dropna()
            closes_list = [float(x) for x in closes.tolist()]
            if len(closes_list) > 0 and price is not None:
                # 1M ~ 21 trading days, 3M ~63, 6M ~126
                def pct_change_from_n(n):
                    if len(closes_list) > n:
                        base = closes_list[-(n+1)]
                        if base and base != 0:
                            return (float(price) - base) / base
                    return None

                one_month_change = pct_change_from_n(21)
                three_month_change = pct_change_from_n(63)
                six_month_change = pct_change_from_n(126)
            # keep last N closes (e.g., 30) as floats for sparkline
            if len(closes_list) > 0:
                # keep last N closes (e.g., 30) as floats for sparkline
                history = closes_list[-30:]
                # extract the corresponding dates as ISO strings and volumes
                try:
                    idx = hist_6mo.index
                    dates = [d.strftime('%Y-%m-%d') for d in idx.tolist()]
                    history_dates = dates[-30:]
                except Exception:
                    history_dates = None
                try:
                    vols = hist_6mo['Volume'].dropna().tolist()
                    volumes = [int(v) for v in vols][-30:]
                except Exception:
                    volumes = None
                # extract OHLC arrays for precise candlesticks (keep full length matching hist_6mo)
                try:
                    opens = hist_6mo['Open'].dropna().tolist()
                    highs = hist_6mo['High'].dropna().tolist()
                    lows = hist_6mo['Low'].dropna().tolist()
                    closes = hist_6mo['Close'].dropna().tolist()
                    # build list of ohlc dicts aligned by index
                    ohlc = []
                    L = min(len(opens), len(highs), len(lows), len(closes))
                    for i in range(L):
                        try:
                            ohlc.append({
                                'open': float(opens[i]),
                                'high': float(highs[i]),
                                'low': float(lows[i]),
                                'close': float(closes[i])
                            })
                        except Exception:
                            # skip malformed row
                            continue
                except Exception:
                    ohlc = None
            else:
                history_dates = None
        except Exception:
            one_month_change = None
            three_month_change = None
            six_month_change = None
            history = None
            history_dates = None
        # info for name and marketCap
        info = {}
        try:
            info = tk.info or {}
        except Exception:
            info = {}
        name = info.get('shortName') or info.get('longName') or ''
        marketCap = info.get('marketCap')
        # percent change and absolute price change from previous close
        reg_prev = info.get('regularMarketPreviousClose')
        reg_pct = None
        price_change = None
        if reg_prev and price is not None:
            try:
                price_change = float(price) - float(reg_prev)
                reg_pct = (float(price_change) / float(reg_prev)) * 100.0
            except Exception:
                reg_pct = None
                price_change = None
        out_row = {
            'symbol': t,
            'shortName': name,
            'regularMarketPrice': safe_float(price),
            'regularMarketChangePercent': safe_float(reg_pct),
            'priceChange': safe_float(price_change),
            'marketCap': marketCap,
            'oneMonthChange': one_month_change,
            'threeMonthChange': three_month_change,
            'sixMonthChange': six_month_change,
            'history': history,
            'historyDates': history_dates,
            'volumes': volumes if 'volumes' in locals() else None
        }
        # include OHLC if available (keep as list of dicts): backward-compatible
        if 'ohlc' in locals() and ohlc:
            out_row['ohlc'] = ohlc
        return out_row
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
