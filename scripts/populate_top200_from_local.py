#!/usr/bin/env python3
"""
Populate scripts/watchlist_config.json with top 200 tickers by market cap
using the latest local testing/history CSV in the repo.
"""
from pathlib import Path
import json
import re
import glob
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
HISTORY_DIR = ROOT / 'testing' / 'history'
CONFIG_PATH = ROOT / 'scripts' / 'watchlist_config.json'


def parse_market_cap(mc_raw):
    if mc_raw is None or (isinstance(mc_raw, float) and pd.isna(mc_raw)):
        return 0
    s = str(mc_raw).strip()
    # if contains letters like 'Invesco', return 0
    m = re.search(r'([0-9,.]+)\s*([TBM])', s, re.IGNORECASE)
    if m:
        num = float(m.group(1).replace(',', ''))
        unit = m.group(2).upper()
        if unit == 'T':
            return num * 1e12
        if unit == 'B':
            return num * 1e9
        if unit == 'M':
            return num * 1e6
    # maybe raw is like '3967.01B' without space
    m2 = re.search(r'^([0-9,.]+)([TBM])$', s, re.IGNORECASE)
    if m2:
        num = float(m2.group(1).replace(',', ''))
        unit = m2.group(2).upper()
        if unit == 'T':
            return num * 1e12
        if unit == 'B':
            return num * 1e9
        if unit == 'M':
            return num * 1e6
    # try to parse plain number
    try:
        return float(s.replace(',', ''))
    except Exception:
        return 0


def find_latest_csv():
    files = sorted(glob.glob(str(HISTORY_DIR / '*.csv')))
    if not files:
        return None
    return Path(files[-1])


def main():
    latest = find_latest_csv()
    if not latest:
        print('No local history CSV found in', HISTORY_DIR)
        return
    print('Using', latest)
    df = pd.read_csv(latest)
    if 'Ticker' not in df.columns or 'Market Cap' not in df.columns:
        print('CSV missing required columns')
        return
    df['mc_num'] = df['Market Cap'].apply(parse_market_cap)
    df_sorted = df.sort_values('mc_num', ascending=False)
    symbols = df_sorted['Ticker'].astype(str).tolist()
    top200 = [s.replace('.', '-').strip().upper() for s in symbols[:200]]
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf8') as f:
        json.dump(top200, f, ensure_ascii=False, indent=2)
    print('Wrote', CONFIG_PATH, 'with', len(top200), 'tickers')

if __name__ == '__main__':
    main()
