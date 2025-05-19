import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
# from pandas_ta import candles # Already imported if using the previous corrected script

# --- Helper Function to Get Ticker (from previous version) ---
def get_ticker_symbol_for_analysis():
    while True:
        ticker_sym = input("Enter Ticker Symbol for Technical Analysis (e.g., AMD, SPY): ").upper()
        if ticker_sym:
            try:
                yf_ticker = yf.Ticker(ticker_sym)
                if not yf_ticker.history(period="5d").empty:
                    return ticker_sym, yf_ticker
                else:
                    print(f"Could not retrieve data for {ticker_sym}. Please try again.")
            except Exception as e:
                print(f"Error fetching ticker {ticker_sym}: {e}")
        else:
            print("Ticker symbol cannot be empty.")


# --- Simplified POC Calculation ---
def calculate_poc(df_period, num_bins=50):
    """Calculates a simplified Point of Control for the given DataFrame period."""
    if df_period.empty or len(df_period) < 2: # Need at least a few bars
        return np.nan, {}

    min_price = df_period['Low'].min()
    max_price = df_period['High'].max()

    if pd.isna(min_price) or pd.isna(max_price) or max_price <= min_price:
        return np.nan, {}

    price_bins = np.linspace(min_price, max_price, num_bins + 1)
    # Use midpoints of bins for labeling
    bin_mids = (price_bins[:-1] + (price_bins[1:])) / 2
    volume_profile_series = pd.Series(index=bin_mids, data=0.0)

    # This is a common way to approximate daily bar volume distribution for VP
    # Iterate through each bar and distribute its volume across the bins it touches
    for _, row in df_period.iterrows():
        vol = row['Volume']
        low = row['Low']
        high = row['High']
        
        # Find bins touched by this bar's range
        bins_touched_indices = np.where((bin_mids >= low) & (bin_mids <= high))[0]
        
        if len(bins_touched_indices) > 0:
            # Distribute volume equally among touched bins (simplification)
            volume_per_touched_bin = vol / len(bins_touched_indices)
            for idx in bins_touched_indices:
                volume_profile_series.iloc[idx] += volume_per_touched_bin
    
    if volume_profile_series.sum() > 0:
        poc_price = volume_profile_series.idxmax() # Price level (bin midpoint) with max volume
        
        # For VAH/VAL (Value Area High/Low) - typically 70% of volume
        sorted_profile = volume_profile_series.sort_values(ascending=False)
        cumulative_volume_percentage = (sorted_profile.cumsum() / sorted_profile.sum()) * 100
        
        value_area_prices = sorted_profile[cumulative_volume_percentage <= 70].index
        vah = value_area_prices.max() if not value_area_prices.empty else np.nan
        val = value_area_prices.min() if not value_area_prices.empty else np.nan
        
        return poc_price, {"vah": vah, "val": val, "profile": volume_profile_series}
    return np.nan, {}


# --- Function to Add Indicators and Analysis ---
def analyze_ticker_daily(ticker_symbol, yf_ticker_obj):
    print(f"\n--- Technical Analysis for {ticker_symbol} (Daily Chart) ---")
    
    try:
        data = yf_ticker_obj.history(period="1y", interval="1d")
        if data.empty:
            print(f"No Daily data found for {ticker_symbol}.")
            return None

        data.index = pd.to_datetime(data.index)
        if data.index.tz is not None: data.index = data.index.tz_localize(None)

        print(f"Calculating base indicators for Daily chart...")

        # --- Moving Averages, RSI, MACD, Volume, ATR, BBands ---
        data.ta.sma(length=20, append=True, col_names=("SMA_20",))
        data.ta.sma(length=50, append=True, col_names=("SMA_50",))
        data.ta.sma(length=100, append=True, col_names=("SMA_100",))
        data.ta.sma(length=200, append=True, col_names=("SMA_200",))
        data.ta.ema(length=9, append=True, col_names=("EMA_9",))
        data.ta.ema(length=12, append=True, col_names=("EMA_12",))
        data.ta.ema(length=21, append=True, col_names=("EMA_21",))
        data.ta.ema(length=26, append=True, col_names=("EMA_26",))
        data.ta.rsi(length=14, append=True, col_names=("RSI_14",))
        data.ta.macd(append=True)
        data.ta.sma(close='Volume', length=20, append=True, col_names=("VOLSMA_20",))
        data.ta.atr(length=14, append=True, col_names=("ATR_14",))
        data.ta.bbands(length=20, std=2, append=True)
        data.ta.vwap(append=True)
        vwap_col_name = None
        for col in data.columns:
            if "VWAP" in col.upper():
                vwap_col_name = col
                break
        if vwap_col_name:
            print(f"VWAP column identified as: {vwap_col_name}")
        else:
            print("Warning: VWAP column not found after ta.vwap().")

        print("Calculating S/R levels and Volume Profile...")

        # --- Volume Profile ---
        vp_lookback = 60
        recent_period_for_vp = data.tail(vp_lookback)
        poc, vp_details = calculate_poc(recent_period_for_vp, num_bins=50)
        
        # --- Fibonacci Retracement (近90天) ---
        lookback_fib = 90
        last_n_data = data.tail(lookback_fib)
        highest_high_val = last_n_data['High'].max()
        highest_high_idx = last_n_data['High'].idxmax()
        lowest_low_val = last_n_data['Low'].min()
        lowest_low_idx = last_n_data['Low'].idxmin()
        fib_levels = {}
        significant_move_identified = False
        trend_direction = "Neutral"

        price_range = abs(highest_high_val - lowest_low_val)
        if highest_high_idx != lowest_low_idx and price_range > 0:
            significant_move_identified = True
            if highest_high_idx > lowest_low_idx:
                trend_direction = "Up"
                fib_levels = {
                    "Retr_23.6%_Up": highest_high_val - 0.236 * price_range,
                    "Retr_38.2%_Up": highest_high_val - 0.382 * price_range,
                    "Retr_50.0%_Up": highest_high_val - 0.5 * price_range,
                    "Retr_61.8%_Up": highest_high_val - 0.618 * price_range,
                    "Retr_78.6%_Up": highest_high_val - 0.786 * price_range,
                    "Ext_127.2%_Up": highest_high_val + 0.272 * price_range,
                    "Ext_161.8%_Up": highest_high_val + 0.618 * price_range,
                    "Ext_200.0%_Up": highest_high_val + 1.0 * price_range,
                    "Ext_261.8%_Up": highest_high_val + 1.618 * price_range,
                }
            else:
                trend_direction = "Down"
                fib_levels = {
                    "Retr_23.6%_Dn": lowest_low_val + 0.236 * price_range,
                    "Retr_38.2%_Dn": lowest_low_val + 0.382 * price_range,
                    "Retr_50.0%_Dn": lowest_low_val + 0.5 * price_range,
                    "Retr_61.8%_Dn": lowest_low_val + 0.618 * price_range,
                    "Retr_78.6%_Dn": lowest_low_val + 0.786 * price_range,
                    "Ext_127.2%_Dn": lowest_low_val - 0.272 * price_range,
                    "Ext_161.8%_Dn": lowest_low_val - 0.618 * price_range,
                    "Ext_200.0%_Dn": lowest_low_val - 1.0 * price_range,
                    "Ext_261.8%_Dn": lowest_low_val - 1.618 * price_range,
                }

        latest = data.iloc[-1]; prev = data.iloc[-2]
        print("\n--- Daily Chart Interpretation ---")
        print(f"Overall Trend: {'Strong Up' if trend_direction == 'Up' else 'Strong Down' if trend_direction == 'Down' else 'Neutral'} (Price: {latest['Close']:.2f})")
        print(f"RSI(14): {latest['RSI_14']:.2f} ({'Overbought' if latest['RSI_14'] > 70 else 'Oversold' if latest['RSI_14'] < 30 else 'Neutral'})")
        macd_val = latest.get('MACD_12_26_9', 0)
        macdsig_val = latest.get('MACDs_12_26_9', 0)
        macdh_val = latest.get('MACDh_12_26_9', 0)
        macd_bias = "Bullish Bias" if macd_val > 0 and macdh_val > 0 else "Bearish Bias" if macd_val < 0 and macdh_val < 0 else "Neutral"
        print(f"MACD: Line={macd_val:.2f}, Signal={macdsig_val:.2f}, Hist={macdh_val:.2f} ({macd_bias})")

        print("\nKey Levels (Approximate):")
        for ma in ['SMA_20', 'SMA_50', 'SMA_100', 'SMA_200']:
            if not pd.isna(latest.get(ma, np.nan)):
                print(f"  {ma}: {latest[ma]:.2f}")
        if not pd.isna(latest.get('BBU_20_2.0', np.nan)):
            print(f"  Upper BB: {latest['BBU_20_2.0']:.2f}, Lower BB: {latest['BBL_20_2.0']:.2f}")
        if vwap_col_name and vwap_col_name in latest and not pd.isna(latest[vwap_col_name]):
            print(f"  {vwap_col_name}: {latest[vwap_col_name]:.2f}")
        if not pd.isna(poc):
            print(f"  Recent POC ({vp_lookback}d): {poc:.2f}")
        if vp_details and not pd.isna(vp_details.get('vah')):
            print(f"  Recent VAH ({vp_lookback}d): {vp_details['vah']:.2f}")
        if vp_details and not pd.isna(vp_details.get('val')):
            print(f"  Recent VAL ({vp_lookback}d): {vp_details['val']:.2f}")
        # Local swing points
        last_local_low = data['Low'].iloc[-10:].min()
        last_local_high = data['High'].iloc[-10:].max()
        last_local_low_idx = data['Low'].iloc[-10:].idxmin()
        last_local_high_idx = data['High'].iloc[-10:].idxmax()
        print(f"  Last Local Low: {last_local_low:.2f} on {last_local_low_idx.date()}")
        print(f"  Last Local High: {last_local_high:.2f} on {last_local_high_idx.date()}")
        # Fibonacci
        if significant_move_identified:
            print(f"\nFibonacci Levels for move from {lowest_low_val:.2f} ({lowest_low_idx.date()}) to {highest_high_val:.2f} ({highest_high_idx.date()}) ({trend_direction} trend):")
            for k, v in fib_levels.items():
                print(f"  {k}: {v:.2f}")

        # 90天內最大跌幅警示
        lookback_for_drop = 90
        recent_data = data.tail(lookback_for_drop)
        if not recent_data.empty:
            high_90d = recent_data['High'].max()
            low_90d = recent_data['Low'].min()
            if high_90d > 0 and (high_90d - low_90d) / high_90d >= 0.3:
                print("\n⚠️  警告：過去90天內股價最大跌幅超過30%，請特別注意風險！")

        # --- 多空分數與理由 ---
        bullish_score = 0
        bearish_score = 0
        bullish_reasons = []
        bearish_reasons = []

        # VWAP
        if vwap_col_name and latest.get(vwap_col_name, 0) < latest.get('Close', float('inf')):
            bullish_score += 1
            bullish_reasons.append("Price > VWAP")
        if vwap_col_name and latest.get(vwap_col_name, float('inf')) > latest.get('Close', 0):
            bearish_score += 1
            bearish_reasons.append("Price < VWAP")

        # RSI
        if latest.get('RSI_14', 50) > 60:
            bullish_score += 1
            bullish_reasons.append("RSI > 60")
        if latest.get('RSI_14', 50) < 40:
            bearish_score += 1
            bearish_reasons.append("RSI < 40")
        if latest.get('RSI_14', 50) > 70:
            bearish_score += 1
            bearish_reasons.append("RSI > 70（超買）")
        if latest.get('RSI_14', 50) < 30:
            bullish_score += 1
            bullish_reasons.append("RSI < 30（超賣）")

        # MACD
        if macd_val > 0 and macdh_val > 0:
            bullish_score += 1
            bullish_reasons.append("MACD > 0 且柱狀體 > 0")
        if macd_val < 0 and macdh_val < 0:
            bearish_score += 1
            bearish_reasons.append("MACD < 0 且柱狀體 < 0")

        # 均線排列
        if latest.get('Close', 0) > latest.get('SMA_20', 0) > latest.get('SMA_50', 0):
            bullish_score += 1
            bullish_reasons.append("多頭排列 (Close > SMA20 > SMA50)")
        if latest.get('Close', 0) < latest.get('SMA_20', 0) < latest.get('SMA_50', 0):
            bearish_score += 1
            bearish_reasons.append("空頭排列 (Close < SMA20 < SMA50)")

        # Bearish Divergence
        bearish_divergence = False
        if latest['High'] > prev['High'] and latest['RSI_14'] < prev['RSI_14']:
            bearish_divergence = True
            bearish_score += 1
            bearish_reasons.append("Bearish Divergence: 價格創新高但RSI未創新高")

        # Bullish Divergence
        bullish_divergence = False
        if latest['Low'] < prev['Low'] and latest['RSI_14'] > prev['RSI_14']:
            bullish_divergence = True
            bullish_score += 1
            bullish_reasons.append("Bullish Divergence: 價格創新低但RSI未創新低")

        # 乖離率
        ema20 = latest.get('EMA_21', np.nan)
        sma50 = latest.get('SMA_50', np.nan)
        close = latest.get('Close', np.nan)
        ema20_diff = (close - ema20) / ema20 * 100 if pd.notna(ema20) and ema20 != 0 else 0
        sma50_diff = (close - sma50) / sma50 * 100 if pd.notna(sma50) and sma50 != 0 else 0

        # 低點且高量，考慮反彈
        if close == data['Low'].min() and latest['Volume'] > data['Volume'].rolling(20).mean().iloc[-1] * 1.5:
            bullish_score += 1
            bullish_reasons.append("近期低點且爆量，可能反彈")
        # 高點且高量，考慮拉回
        if close == data['High'].max() and latest['Volume'] > data['Volume'].rolling(20).mean().iloc[-1] * 1.5:
            bearish_score += 1
            bearish_reasons.append("近期高點且爆量，可能拉回")

        # 乖離率門檻
        overbought_threshold = 8
        oversold_threshold = -8
        if ema20_diff > overbought_threshold or sma50_diff > overbought_threshold:
            bearish_score += 1
            bearish_reasons.append("股價遠高於均線，短線過熱不宜追多")
        if ema20_diff < oversold_threshold or sma50_diff < oversold_threshold:
            bullish_score += 1
            bullish_reasons.append("股價遠低於均線，短線過冷不宜追空")

        # 多均線乖離
        ma_cols = ['EMA_21', 'SMA_20', 'SMA_50', 'SMA_100', 'SMA_200', 'EMA_9']
        for ma_col in ma_cols:
            ma_val = latest.get(ma_col, np.nan)
            if pd.notna(ma_val) and ma_val != 0:
                diff = (close - ma_val) / ma_val * 100
                if diff > 10:
                    bearish_score += 1
                    bearish_reasons.append(f"股價高於{ma_col}超過10%（+{diff:.1f}%），短線過熱")
                if diff < -10:
                    bullish_score += 1
                    bullish_reasons.append(f"股價低於{ma_col}超過10%（{diff:.1f}%），短線過冷")

        # --- 支撐/壓力計算 ---
        def get_sr_levels_safe_enhanced(data_latest_series, full_data_df, fib_data_dict, is_support_levels, vwap_val, poc_val, vah_val, val_val):
            levels = []
            for ma_col_sr in ['SMA_20', 'SMA_50', 'SMA_100', 'SMA_200', 'EMA_9', 'EMA_21']:
                val = data_latest_series.get(ma_col_sr)
                if val is not None and not pd.isna(val): levels.append(val)
            # BBands
            if not pd.isna(data_latest_series.get('BBL_20_2.0', np.nan)):
                levels.append(data_latest_series['BBL_20_2.0'] if is_support_levels else data_latest_series['BBU_20_2.0'])
            # Fibonacci
            if fib_data_dict:
                for v in fib_data_dict.values():
                    levels.append(v)
            # VWAP
            if vwap_val is not None and not pd.isna(vwap_val): levels.append(vwap_val)
            # Volume Profile
            if is_support_levels:
                if poc_val is not None and not pd.isna(poc_val): levels.append(poc_val)
                if val_val is not None and not pd.isna(val_val): levels.append(val_val)
            else:
                if poc_val is not None and not pd.isna(poc_val): levels.append(poc_val)
                if vah_val is not None and not pd.isna(vah_val): levels.append(vah_val)
            # 過濾 None/NaN
            return sorted(list(set(lvl for lvl in levels if lvl is not None and not pd.isna(lvl))))

        def get_structural_tps_with_source(entry, supports, fib_levels, poc, vah, val, bb_lower, max_tp_count=3):
            """回傳 [(tp_value, 來源說明)]，依據結構重要性排序"""
            tps = []
            fib_map = {
                "Retr_23.6%_Dn": "Fib 23.6%", "Retr_38.2%_Dn": "Fib 38.2%", "Retr_50.0%_Dn": "Fib 50.0%", "Retr_61.8%_Dn": "Fib 61.8%",
                "Retr_23.6%_Up": "Fib 23.6%", "Retr_38.2%_Up": "Fib 38.2%", "Retr_50.0%_Up": "Fib 50.0%", "Retr_61.8%_Up": "Fib 61.8%",
                "Ext_127.2%_Dn": "Fib 127.2%", "Ext_161.8%_Dn": "Fib 161.8%", "Ext_127.2%_Up": "Fib 127.2%", "Ext_161.8%_Up": "Fib 161.8%",
                "Ext_200.0%_Dn": "Fib 200.0%", "Ext_200.0%_Up": "Fib 200.0%", "Ext_261.8%_Dn": "Fib 261.8%", "Ext_261.8%_Up": "Fib 261.8%",
            }
            if fib_levels:
                for k, v in fib_levels.items():
                    if v < entry and v > 0 and abs(v-entry)/entry < 0.3:
                        tps.append((v, fib_map.get(k, k)))
            # 2. POC, VAL
            if poc and poc < entry and poc > 0 and abs(poc-entry)/entry < 0.3:
                tps.append((poc, "POC"))
            if val and val < entry and val > 0 and abs(val-entry)/entry < 0.3:
                tps.append((val, "VAL"))
            # 3. BB下軌
            if bb_lower and bb_lower < entry and abs(bb_lower-entry)/entry < 0.3:
                tps.append((bb_lower, "BB下軌"))
            # 4. 重要均線（來源名稱帶入）
            # 先建立名稱對應值的 dict
            ma_dict = {}
            for name in ['EMA_21', 'SMA_20', 'SMA_50', 'SMA_100', 'SMA_200', 'EMA_9']:
                val = None
                try:
                    val = float(globals()["latest"].get(name, None))
                except Exception:
                    continue
                if val is not None:
                    ma_dict[val] = name
            for ma in supports:
                ma_name = ma_dict.get(ma, "均線")
                tps.append((ma, ma_name))
            # 去重並排序
            tps = list({(v, s) for v, s in tps if s})
            tps = sorted(tps, key=lambda x: -x[0])
            return tps[:max_tp_count]

        def get_structural_tps_long_with_source(entry, resistances, fib_levels, poc, vah, val, bb_upper, max_tp_count=3):
            tps = []
            fib_map = {
                "Ext_127.2%_Up": "Fib 127.2%", "Ext_161.8%_Up": "Fib 161.8%", "Ext_200.0%_Up": "Fib 200.0%", "Ext_261.8%_Up": "Fib 261.8%",
                "Retr_23.6%_Up": "Fib 23.6%", "Retr_38.2%_Up": "Fib 38.2%", "Retr_50.0%_Up": "Fib 50.0%", "Retr_61.8%_Up": "Fib 61.8%",
                "Ext_127.2%_Dn": "Fib 127.2%", "Ext_161.8%_Dn": "Fib 161.8%", "Ext_200.0%_Dn": "Fib 200.0%", "Ext_261.8%_Dn": "Fib 261.8%",
            }
            if fib_levels:
                for k, v in fib_levels.items():
                    if v > entry and abs(v-entry)/entry < 0.3:
                        tps.append((v, fib_map.get(k, k)))
            if poc and poc > entry and abs(poc-entry)/entry < 0.3:
                tps.append((poc, "POC"))
            if vah and vah > entry and abs(vah-entry)/entry < 0.3:
                tps.append((vah, "VAH"))
            if bb_upper and bb_upper > entry and abs(bb_upper-entry)/entry < 0.3:
                tps.append((bb_upper, "BB上軌"))
            ma_dict = {}
            for name in ['EMA_21', 'SMA_20', 'SMA_50', 'SMA_100', 'SMA_200', 'EMA_9']:
                val = None
                try:
                    val = float(globals()["latest"].get(name, None))
                except Exception:
                    continue
                if val is not None:
                    ma_dict[val] = name
            for ma in resistances:
                ma_name = ma_dict.get(ma, "均線")
                tps.append((ma, ma_name))
            tps = list({(v, s) for v, s in tps if s})
            tps = sorted(tps, key=lambda x: x[0])
            return tps[:max_tp_count]

        def filter_tp_candidates(entry, stop_loss, tp_candidates, is_short=True, min_gap=0.02, max_tp=3):
            """過濾TP: 不重複、距離不能太近、RR需大於1"""
            filtered = []
            used_values = set()
            last_tp = None
            for tp, src in tp_candidates:
                # 距離現價太近或重複來源跳過
                if last_tp is not None and abs(tp - last_tp) / entry < min_gap:
                    continue
                if tp in used_values:
                    continue
                rr = ((entry - tp) / (stop_loss - entry)) if is_short else ((tp - entry) / (entry - stop_loss))
                if rr < 1 or (is_short and tp >= entry) or (not is_short and tp <= entry):
                    continue
                filtered.append((tp, src, rr))
                used_values.add(tp)
                last_tp = tp
                if len(filtered) >= max_tp:
                    break
            return filtered

        latest_vwap = latest.get(vwap_col_name, np.nan) if vwap_col_name else np.nan
        all_supports = get_sr_levels_safe_enhanced(
            latest, data, fib_levels if significant_move_identified else None, True, 
            latest_vwap, poc, vp_details.get('vah'), vp_details.get('val')
        )
        all_resistances = get_sr_levels_safe_enhanced(
            latest, data, fib_levels if significant_move_identified else None, False,
            latest_vwap, poc, vp_details.get('vah'), vp_details.get('val')
        )

        print("\n--- Potential Trade Ideas (Requires Careful Consideration) ---")

        entry = latest['Close']
        print(f"Current Price: {entry:.2f}")

        # 過濾合理的支撐/壓力（大於0且與現價距離不超過50%）
        filtered_supports = [lvl for lvl in all_supports if lvl > 0 and lvl < entry and abs(lvl-entry)/entry < 0.5]
        filtered_resistances = [lvl for lvl in all_resistances if lvl > entry and abs(lvl-entry)/entry < 0.5]

        # 空單
        if bearish_score >= 3:
            stop_loss = max(filtered_resistances) if filtered_resistances else entry * 1.03
            bb_lower = latest.get('BBL_20_2.0', None)
            tp_candidates = get_structural_tps_with_source(entry, filtered_supports, fib_levels if significant_move_identified else None, poc, vp_details.get('vah'), vp_details.get('val'), bb_lower, max_tp_count=10)
            filtered_tp = filter_tp_candidates(entry, stop_loss, tp_candidates, is_short=True, min_gap=0.02, max_tp=3)
            print("\n  Potential Short Scenario (Confluence Score: %d):" % bearish_score)
            print(f"    Entry: ~{entry:.2f}, SL: {stop_loss:.2f} (Risk: {stop_loss-entry:.2f})")
            for i, (tp, src, rr) in enumerate(filtered_tp):
                print(f"    TP{i+1}: {tp:.2f} ({src}) (Reward: {entry-tp:.2f}, R:R: {rr:.2f}:1)")
            print(f"    空方理由: {', '.join(bearish_reasons)}")
            if not filtered_tp:
                print("    ⚠️ 無合理TP（RR>1），建議觀望。")

        # 多單同理
        if bullish_score >= 3:
            stop_loss = min(filtered_supports) if filtered_supports else entry * 0.97
            bb_upper = latest.get('BBU_20_2.0', None)
            tp_candidates = get_structural_tps_long_with_source(entry, filtered_resistances, fib_levels if significant_move_identified else None, poc, vp_details.get('vah'), vp_details.get('val'), bb_upper, max_tp_count=10)
            filtered_tp = filter_tp_candidates(entry, stop_loss, tp_candidates, is_short=False, min_gap=0.02, max_tp=3)
            print("\n  Potential Long Scenario (Confluence Score: %d):" % bullish_score)
            print(f"    Entry: ~{entry:.2f}, SL: {stop_loss:.2f} (Risk: {entry-stop_loss:.2f})")
            for i, (tp, src, rr) in enumerate(filtered_tp):
                print(f"    TP{i+1}: {tp:.2f} ({src}) (Reward: {tp-entry:.2f}, R:R: {rr:.2f}:1)")
            print(f"    多方理由: {', '.join(bullish_reasons)}")
            if not filtered_tp:
                print("    ⚠️ 無合理TP（RR>1），建議觀望。")

        # 極端超賣提示
        if latest['RSI_14'] < 20 or (latest['Close'] < latest.get('BBL_20_2.0', 0)):
            print("\n  ⚠️ 極端超賣：RSI < 20 或收盤價低於BB下軌，短線反彈機會大增，可考慮小部位短線多單。")

        if latest['Close'] < latest.get('BBL_20_2.0', 0) and latest['Close'] < latest.get('SMA_20', 0) * 0.95:
            print("\n  [Short-term Long Bias] 收盤價跌破BB下軌且遠離SMA20，短線反彈機會，可考慮小部位多單。")

        if bullish_score < 3 and bearish_score < 3:
            print("\n  No clear high-probability scenario based on current rules.")

        return data

    except Exception as e:
        print(f"An error occurred during daily analysis for {ticker_symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None

# --- Main Execution for Tool 2 ---
if __name__ == "__main__":
    print("--- Technical Analysis Tool (Phase 4 - VWAP & Basic Volume Profile) ---")
    selected_ticker, yf_ticker_object = get_ticker_symbol_for_analysis()
    if selected_ticker and yf_ticker_object:
        daily_analysis_data = analyze_ticker_daily(selected_ticker, yf_ticker_object)
        if daily_analysis_data is not None:
            print(f"\nDaily analysis for {selected_ticker} complete. Review interpretations above.")
        else:
            print(f"\nDaily analysis for {selected_ticker} could not be completed.")


