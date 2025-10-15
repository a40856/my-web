import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from datetime import datetime

# RSI Calculation
def calculate_rsi(df, price_col="Close", window=14):
    delta = df[price_col].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# RSI divergence detection
def detect_rsi_divergence(df, rsi, price_col="Close"):
    bullish_div = False
    bearish_div = False
    if len(df) >= 5:
        recent_prices = df[price_col].iloc[-5:]
        recent_rsi = rsi.iloc[-5:]
        price_low = recent_prices.idxmin()
        rsi_low = recent_rsi.idxmin()
        price_high = recent_prices.idxmax()
        rsi_high = recent_rsi.idxmax()
        if price_low != rsi_low:
            bullish_div = True
        if price_high != rsi_high:
            bearish_div = True
    return bullish_div, bearish_div

# MACD Calculation & Scoring
def calculate_macd(df, price_col='Close'):
    ema12 = df[price_col].ewm(span=12, adjust=False).mean()
    ema26 = df[price_col].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    df['MACD'] = macd
    df['Signal'] = signal
    df['Hist'] = hist
    return df

def score_macd(df):
    df['MACD_Score'] = 0.0
    for i in range(1, len(df)):
        if (df['MACD'].iloc[i-1] < df['Signal'].iloc[i-1]) and (df['MACD'].iloc[i] > df['Signal'].iloc[i]) and (df['MACD'].iloc[i] < 0):
            df.at[df.index[i], 'MACD_Score'] += 1
        if (df['MACD'].iloc[i-1] > df['Signal'].iloc[i-1]) and (df['MACD'].iloc[i] < df['Signal'].iloc[i]) and (df['MACD'].iloc[i] > 0):
            df.at[df.index[i], 'MACD_Score'] -= 1
    return df

# Bollinger Bands & Scoring
def calculate_bollinger_bands(df, price_col="Close", window=20, num_std=2):
    df['BB_Middle'] = df[price_col].rolling(window=window).mean()
    std = df[price_col].rolling(window=window).std()
    df['BB_Upper'] = df['BB_Middle'] + num_std * std
    df['BB_Lower'] = df['BB_Middle'] - num_std * std
    return df

def score_bollinger_bands(df, price_col="Close"):
    df['BB_Score'] = 0.0
    for i in range(1, len(df)):
        price = df[price_col].iloc[i]
        prev_price = df[price_col].iloc[i-1]
        bb_middle = df['BB_Middle'].iloc[i]
        bb_upper = df['BB_Upper'].iloc[i]
        bb_lower = df['BB_Lower'].iloc[i]
        prev_bb_middle = df['BB_Middle'].iloc[i-1]
        prev_bb_upper = df['BB_Upper'].iloc[i-1]
        prev_bb_lower = df['BB_Lower'].iloc[i-1]
        if price <= bb_lower:
            df.at[df.index[i], 'BB_Score'] += 1
        if price >= bb_upper:
            df.at[df.index[i], 'BB_Score'] -= 1
        if prev_price < prev_bb_lower and price >= bb_lower:
            df.at[df.index[i], 'BB_Score'] += 1
        if prev_price > prev_bb_upper and price <= bb_upper:
            df.at[df.index[i], 'BB_Score'] -= 1
        if prev_price < prev_bb_middle and price >= bb_middle:
            df.at[df.index[i], 'BB_Score'] += 0.5
        if prev_price > prev_bb_middle and price <= bb_middle:
            df.at[df.index[i], 'BB_Score'] -= 0.5
        band_width = bb_upper - bb_lower
        prev_band_width = prev_bb_upper - prev_bb_lower
        if band_width < 0.5 * prev_band_width:
            df.at[df.index[i], 'BB_Score'] = 0
        if price > bb_upper and prev_price > prev_bb_upper:
            df.at[df.index[i], 'BB_Score'] = 2
        if price < bb_lower and prev_price < prev_bb_lower:
            df.at[df.index[i], 'BB_Score'] = -2
    return df

# Local maxima/minima detection for Fibonacci scoring
def detect_local_max_min(df, price_col='Close', window=5):
    prices = df[price_col].values
    max_idx, _ = find_peaks(prices, distance=window)
    min_idx, _ = find_peaks(-prices, distance=window)
    df['LocalMax'] = False
    df['LocalMin'] = False
    df.loc[df.index[max_idx], 'LocalMax'] = True
    df.loc[df.index[min_idx], 'LocalMin'] = True
    return df, max_idx, min_idx

def calculate_fib_levels(high, low):
    diff = high - low
    levels = {
        'Fib_0': low,
        'Fib_23.6': high - 0.236 * diff,
        'Fib_38.2': high - 0.382 * diff,
        'Fib_50': high - 0.5 * diff,
        'Fib_61.8': high - 0.618 * diff,
        'Fib_78.6': high - 0.786 * diff,
        'Fib_100': high
    }
    return levels

def score_fibonacci(df, price_col='Close', window=5, threshold=0.01):
    df, max_idx, min_idx = detect_local_max_min(df, price_col, window)
    swings = sorted(list(max_idx) + list(min_idx))
    df['Fib_Score'] = 0.0
    for i in range(len(swings) - 1):
        start_idx = swings[i]
        end_idx = swings[i+1]
        swing_high = df[price_col].iloc[start_idx:end_idx+1].max()
        swing_low = df[price_col].iloc[start_idx:end_idx+1].min()
        fib_levels = calculate_fib_levels(swing_high, swing_low)
        for j in range(start_idx, end_idx+1):
            price = df[price_col].iloc[j]
            for level_name, level_val in fib_levels.items():
                if abs(price - level_val) / level_val <= threshold:
                    if level_name in ['Fib_38.2', 'Fib_50', 'Fib_61.8', 'Fib_78.6', 'Fib_0']:
                        df.at[df.index[j], 'Fib_Score'] += 1
                    elif level_name in ['Fib_23.6', 'Fib_100']:
                        df.at[df.index[j], 'Fib_Score'] -= 1
    return df

# EMA calculation & scoring
def calculate_ema(df, price_col='Close'):
    df['EMA20'] = df[price_col].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df[price_col].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df[price_col].ewm(span=200, adjust=False).mean()
    return df

def score_ema_strategy(df):
    df['EMA_Score'] = 0.0
    for i in range(1, len(df)):
        if (df['EMA50'].iloc[i-1] < df['EMA200'].iloc[i-1]) and (df['EMA50'].iloc[i] > df['EMA200'].iloc[i]):
            df.at[df.index[i], 'EMA_Score'] += 2  # Golden Cross
        if (df['EMA50'].iloc[i-1] > df['EMA200'].iloc[i-1]) and (df['EMA50'].iloc[i] < df['EMA200'].iloc[i]):
            df.at[df.index[i], 'EMA_Score'] -= 2  # Death Cross
        if (df['EMA20'].iloc[i-1] < df['EMA50'].iloc[i-1]) and (df['EMA20'].iloc[i] > df['EMA50'].iloc[i]):
            df.at[df.index[i], 'EMA_Score'] += 1  # 20 cross up 50
        if (df['EMA20'].iloc[i-1] > df['EMA50'].iloc[i-1]) and (df['EMA20'].iloc[i] < df['EMA50'].iloc[i]):
            df.at[df.index[i], 'EMA_Score'] -= 1  # 20 cross down 50
        price = df['Close'].iloc[i]
        if abs(price - df['EMA20'].iloc[i]) / df['EMA20'].iloc[i] < 0.01:
            df.at[df.index[i], 'EMA_Score'] += 1
        elif abs(price - df['EMA50'].iloc[i]) / df['EMA50'].iloc[i] < 0.01:
            df.at[df.index[i], 'EMA_Score'] += 1
        if price < df['EMA20'].iloc[i] and price > df['EMA50'].iloc[i]:
            df.at[df.index[i], 'EMA_Score'] -= 1
        if (df['EMA20'].iloc[i] - df['EMA20'].iloc[i-1]) > 0:
            df.at[df.index[i], 'EMA_Score'] += 0.5
        else:
            df.at[df.index[i], 'EMA_Score'] -= 0.5
    return df

# Main running loop for tickers
def main():
    tickers = [
    "QQQ", "SPY", "IWM", "AAPL", "NVDA", "MSFT", "GOOG", "AMZN", "META", "BRK-B",
    "LLY", "TSM", "AVGO", "TSLA", "JPM", "WMT", "UNH", "V", "XOM", "NVO", "MA", "PG", "JNJ",
    "COST", "ORCL", "HD", "ASML", "ABBV", "BAC", "KO", "MRK", "NFLX", "CVX", "AZN", "CRM", "SAP",
    "AMD", "TM", "ADBE", "PEP", "SHEL", "NVS", "TMUS", "TMO", "LIN", "ACN", "MCD", "CSCO", "ABT",
    "DHR", "QCOM", "WFC", "TXN", "PDD", "GE", "IBM", "BABA", "AXP", "AMGN", "VZ", "INTU", "ISRG",
    "BX", "CAT", "AMAT", "MS", "DIS", "NEE", "TTE", "GS", "RTX", "SPGI", "UBER", "ARM", "LOW", "T",
    "PGR", "LMT", "REGN", "BLK", "BKNG", "ELV", "NKE", "PLD", "C", "SCHW", "MU", "PANW", "MDT", "CB",
    "LRCX", "ADP", "KLAC", "MMC", "UPS", "BA", "SBUX", "DE", "HCA", "CI", "SHOP", "FI", "BMY", "GILD",
    "ICE", "MO", "RACE", "CL", "ZTS", "DELL", "EQIX", "NOC", "ABNB", "TGT", "PYPL", "MMM", "PLTR",
    "USB", "SPOT", "CRWD", "SLB", "ADSK", "GM", "COIN", "OXY", "GEV", "CHTR", "MSCI", "F", "SE", "EW",
    "RCL", "XYZ", "SNOW", "JD", "SMCI", "EL", "MRNA", "MSTR", "CCL", "ILMN", "CELH", "MARA", "VST",
    "OKLO", "SMR", "APO", "WDAY", "APP", "NET", "MBLY", "AFRM", "UPST", "TMDX", "QUBT", "IONQ", "RKLB",
    "SOFI", "NU", "MELI", "TXRH", "BROS", "PRMB", "PM", "TDOC", "ZM", "PINS", "ROKU", "CRSP", "Z", "FSLY",
    "RDDT", "GRAB", "GLW", "NNE", "ZS", "TWLO","FSLR", "NBIS", "PENN","DKNG"
    ]

    
    results = []
    for tk in tickers:
        try:
            stock = yf.Ticker(tk)
            df = stock.history(period="60d", interval="1d")
            if df.empty:
                continue

            if 'Volume' in df:
                df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
                df['Rel_Volume'] = df['Volume'] / df['Volume_MA20']

            # RSI & divergence
            rsi = calculate_rsi(df)
            bullish_div, bearish_div = detect_rsi_divergence(df, rsi)
            rsi_score = 0
            latest_rsi = rsi.iloc[-1]
            if latest_rsi < 30:
                rsi_score += 1
            elif latest_rsi > 70:
                rsi_score -= 1
            if len(rsi) > 1:
                if rsi.iloc[-2] < 50 and latest_rsi >= 50:
                    rsi_score += 1
                elif rsi.iloc[-2] > 50 and latest_rsi <= 50:
                    rsi_score -= 1
            if bullish_div:
                rsi_score += 1
            if bearish_div:
                rsi_score -= 1

            # MACD & score
            df = calculate_macd(df)
            df = score_macd(df)
            macd_score = df['MACD_Score'].iloc[-1]

            # EMA & score
            df = calculate_ema(df)
            df = score_ema_strategy(df)
            ema_score = df['EMA_Score'].iloc[-1]

            # Fibonacci & score
            df = score_fibonacci(df)
            fib_score = df['Fib_Score'].iloc[-1]

            # Bollinger Bands & score
            df = calculate_bollinger_bands(df)
            df = score_bollinger_bands(df)
            bb_score = df['BB_Score'].iloc[-1]

            # Volume scoring based on MACD score & relative volume
            volume_score = 0
            if 'Volume' in df:
                rel_vol = df['Rel_Volume'].iloc[-1]
                if abs(macd_score) >= 1:
                    if rel_vol >= 1.5:
                        volume_score += np.sign(macd_score) * 1
                    elif rel_vol < 0.8:
                        volume_score += 0.5 * macd_score
                if df['Volume'].iloc[-1] == df['Volume'].rolling(window=20).max().iloc[-1]:
                    if macd_score > 0:
                        volume_score += 1
                    else:
                        volume_score -= 1
                if (df['Close'].iloc[-1] > df['Close'].iloc[-2] and df['Volume'].iloc[-1] < df['Volume'].iloc[-2]):
                    volume_score -= 1

            total_score = rsi_score + macd_score + volume_score + bb_score + fib_score + ema_score
            latest_price = df['Close'].iloc[-1]
            latest_change = df['Close'].iloc[-1] - df['Close'].iloc[-2] if len(df) > 1 else 0

            results.append({
                'Ticker': tk,
                'Price': latest_price,
                'Day Change': latest_change,
                'Total_Score': total_score,
                'RSI': latest_rsi,
                'RSI_Score': rsi_score,
                'MACD_Score': macd_score,
                'Volume_Score': volume_score,
                'BB_Score': bb_score,
                'Fib_Score': fib_score,
                'EMA_Score': ema_score
            })

        except Exception as e:
            print(f"Error processing {tk}: {e}")

    result_df = pd.DataFrame(results)
    # 儲存到 analysis 資料夾
    import os
    os.makedirs("analysis", exist_ok=True)
    file_name = f"analysis/analysis-{datetime.today().strftime('%Y-%m-%d')}.xlsx"
    result_df.to_excel(file_name, index=False)
    print(f"Analysis saved to {file_name}")

if __name__ == "__main__":
    main()
