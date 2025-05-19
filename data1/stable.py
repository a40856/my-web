import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
from pandas_ta import candles # For direct candlestick function calls

# --- Helper Function to Get Ticker ---
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

# --- Simplified POC, VAH, VAL Calculation ---
def calculate_volume_profile_levels(df_period, num_bins=50, va_percentage=70):
    """Calculates POC, VAH, VAL for the given DataFrame period."""
    if df_period.empty or len(df_period) < 2:
        return np.nan, np.nan, np.nan, {}

    min_price = df_period['Low'].min()
    max_price = df_period['High'].max()

    if pd.isna(min_price) or pd.isna(max_price) or max_price <= min_price:
        return np.nan, np.nan, np.nan, {}

    price_bins = np.linspace(min_price, max_price, num_bins + 1)
    bin_mids = (price_bins[:-1] + price_bins[1:]) / 2
    volume_profile_series = pd.Series(index=bin_mids, data=0.0)

    for _, row in df_period.iterrows():
        vol = row['Volume']
        low = row['Low']
        high = row['High']
        bins_touched_indices = np.where((bin_mids >= low) & (bin_mids <= high))[0]
        if len(bins_touched_indices) > 0:
            volume_per_touched_bin = vol / len(bins_touched_indices)
            for idx in bins_touched_indices:
                if 0 <= idx < len(volume_profile_series): # Boundary check
                    volume_profile_series.iloc[idx] += volume_per_touched_bin
    
    if volume_profile_series.sum() > 0:
        poc_price = volume_profile_series.idxmax()
        
        sorted_profile = volume_profile_series.sort_values(ascending=False)
        cumulative_volume_percent = (sorted_profile.cumsum() / sorted_profile.sum()) * 100
        
        value_area_prices = sorted_profile[cumulative_volume_percent <= va_percentage].index
        vah = value_area_prices.max() if not value_area_prices.empty else np.nan
        val = value_area_prices.min() if not value_area_prices.empty else np.nan
        
        return poc_price, vah, val, {"profile": volume_profile_series} # Return profile too if needed later
    return np.nan, np.nan, np.nan, {}


# --- Function to Add Indicators and Analysis ---
def analyze_ticker_daily(ticker_symbol, yf_ticker_obj):
    print(f"\n--- Technical Analysis for {ticker_symbol} (Daily Chart) ---")
    
    try:
        data = yf_ticker_obj.history(period="2y", interval="1d")
        if data.empty:
            print(f"No Daily data found for {ticker_symbol}.")
            return None

        data.index = pd.to_datetime(data.index)
        if data.index.tz is not None: data.index = data.index.tz_localize(None)

        print(f"Calculating base indicators for Daily chart...")
        data.ta.sma(length=20, append=True, col_names=("SMA_20",))
        data.ta.sma(length=50, append=True, col_names=("SMA_50",))
        data.ta.sma(length=100, append=True, col_names=("SMA_100",))
        data.ta.sma(length=200, append=True, col_names=("SMA_200",))
        data.ta.ema(length=9, append=True, col_names=("EMA_9",))
        data.ta.ema(length=12, append=True, col_names=("EMA_12",))
        data.ta.ema(length=21, append=True, col_names=("EMA_21",))
        data.ta.ema(length=26, append=True, col_names=("EMA_26",))
        data.ta.rsi(length=14, append=True, col_names=("RSI_14",))
        data.ta.macd(append=True) # MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
        data.ta.sma(close='Volume', length=20, append=True, col_names=("VOLSMA_20",))
        data.ta.atr(length=14, append=True, col_names=("ATR_14",))
        data.ta.bbands(length=20, std=2, append=True) # BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
        data.ta.vwap(append=True) # Default name is often 'VWAP_D' or just 'VWAP'
        
        vwap_col_name = None
        for col in data.columns:
            if "VWAP" in col.upper() and col.endswith("_D"): vwap_col_name = col; break
            if "VWAP" in col.upper() and vwap_col_name is None: vwap_col_name = col # Fallback
        if vwap_col_name: print(f"VWAP column identified as: {vwap_col_name}")
        else: print("Warning: VWAP column not automatically found, ensure it's handled if present.")



        # --- Optional: Ichimoku & Stochastic (Calculation part) ---
        # data.ta.ichimoku(append=True)
        # data.ta.stoch(append=True)
        # ichimoku_cols = [col for col in data.columns if col.startswith(("ISA_", "ISB_", "ITS_", "IKS_", "ICS_"))]
        # stoch_k_col, stoch_d_col = (next((c for c in data.columns if "STOCHK" in c.upper()), None), 
        #                            next((c for c in data.columns if "STOCHD" in c.upper()), None))


        print("Calculating S/R levels and Volume Profile...")
        n_swing = 20 
        data['min_swing'] = data['Low'].rolling(window=n_swing, center=True).min()
        data['max_swing'] = data['High'].rolling(window=n_swing, center=True).max()
        order_val = 5 
        local_lows_idx = argrelextrema(data['Low'].values, np.less_equal, order=order_val)[0]
        local_highs_idx = argrelextrema(data['High'].values, np.greater_equal, order=order_val)[0]
        data['local_low'] = np.nan; data['local_high'] = np.nan
        if len(local_lows_idx) > 0: data.loc[data.index[local_lows_idx], 'local_low'] = data['Low'].iloc[local_lows_idx]
        if len(local_highs_idx) > 0: data.loc[data.index[local_highs_idx], 'local_high'] = data['High'].iloc[local_highs_idx]

        vp_lookback = 60
        poc, vah, val, _ = calculate_volume_profile_levels(data.tail(vp_lookback))
        
        lookback_fib = 90 
        last_n_data = data.tail(lookback_fib)
        highest_high_val = last_n_data['High'].max(); highest_high_idx = last_n_data['High'].idxmax()
        lowest_low_val = last_n_data['Low'].min(); lowest_low_idx = last_n_data['Low'].idxmin()
        fib_levels = {}; significant_move_identified = False; fib_trend_direction = "Neutral"
        price_range = abs(highest_high_val - lowest_low_val) 

        if highest_high_idx != lowest_low_idx and price_range > 1e-9: # Check for non-zero price range
            significant_move_identified = True
            retracement_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
            extension_levels_std = [1.272, 1.618, 2.0, 2.618] 
            fib_levels['Move_Start_Price'] = np.nan; fib_levels['Move_End_Price'] = np.nan

            if highest_high_idx > lowest_low_idx: 
                fib_trend_direction = "Up"
                fib_levels['Move_Start_Price'] = lowest_low_val; fib_levels['Move_End_Price'] = highest_high_val
                for level in retracement_levels: fib_levels[f'Retr_{level*100:.1f}%_Up'] = highest_high_val - (price_range * level)
                for level in extension_levels_std: fib_levels[f'Ext_{level*100:.1f}%_Up'] = highest_high_val + (price_range * (level-1)) 
            else: 
                fib_trend_direction = "Down"
                fib_levels['Move_Start_Price'] = highest_high_val; fib_levels['Move_End_Price'] = lowest_low_val
                for level in retracement_levels: fib_levels[f'Retr_{level*100:.1f}%_Down'] = lowest_low_val + (price_range * level)
                for level in extension_levels_std: fib_levels[f'Ext_{level*100:.1f}%_Down'] = lowest_low_val - (price_range * (level-1))
            
            fib_levels['Move_Trend'] = fib_trend_direction
            fib_levels['Move_Start_Date'] = (lowest_low_idx if fib_trend_direction == "Up" else highest_high_idx).strftime('%Y-%m-%d')
            fib_levels['Move_End_Date'] = (highest_high_idx if fib_trend_direction == "Up" else lowest_low_idx).strftime('%Y-%m-%d')

        # --- Interpretation & Suggestion Logic ---
        latest = data.iloc[-1]; prev = data.iloc[-2] if len(data) > 1 else data.iloc[-1] # Handle short history
        current_price = latest.get('Close', np.nan)
        if pd.isna(current_price): 
            print("Error: Could not determine current price."); return data

        print("\n--- Daily Chart Interpretation ---")
        # Trend
        trend = "Neutral"
        sma50 = latest.get('SMA_50', np.nan); sma200 = latest.get('SMA_200', np.nan)
        ema9 = latest.get('EMA_9', np.nan); ema21 = latest.get('EMA_21', np.nan)
        if not pd.isna(current_price) and not pd.isna(sma50) and not pd.isna(sma200) and not pd.isna(ema9) and not pd.isna(ema21):
            if current_price > sma50 and sma50 > sma200 and ema9 > ema21: trend = "Strong Up"
            elif current_price > sma50 and ema9 > ema21: trend = "Up"
            elif current_price < sma50 and sma50 < sma200 and ema9 < ema21: trend = "Strong Down"
            elif current_price < sma50 and ema9 < ema21: trend = "Down"
        print(f"Overall Trend: {trend} (Price: {current_price:.2f})")

        # RSI
        rsi_val = latest.get('RSI_14', np.nan)
        rsi_state = "Neutral"
        if not pd.isna(rsi_val):
            if rsi_val > 70: rsi_state = "Overbought"
            elif rsi_val < 30: rsi_state = "Oversold"
            print(f"RSI(14): {rsi_val:.2f} ({rsi_state})")

        # MACD
        macd_line = latest.get('MACD_12_26_9', np.nan); macd_signal = latest.get('MACDs_12_26_9', np.nan); macd_hist = latest.get('MACDh_12_26_9', np.nan)
        prev_macd_line = prev.get('MACD_12_26_9', np.nan); prev_macd_signal = prev.get('MACDs_12_26_9', np.nan); prev_macd_hist = prev.get('MACDh_12_26_9', np.nan)
        macd_text = "Neutral"
        if not pd.isna(macd_line) and not pd.isna(macd_signal) and not pd.isna(prev_macd_line) and not pd.isna(prev_macd_signal):
            if macd_line > macd_signal and prev_macd_line <= prev_macd_signal: macd_text = "Bullish Crossover"
            elif macd_line < macd_signal and prev_macd_line >= prev_macd_signal: macd_text = "Bearish Crossover"
        if not pd.isna(macd_hist) and not pd.isna(prev_macd_hist) and macd_text == "Neutral": # Prioritize crossover
            if macd_hist > 0 and prev_macd_hist <= 0: macd_text = "Hist Bullish Flip"
            elif macd_hist < 0 and prev_macd_hist >= 0: macd_text = "Hist Bearish Flip"
        if not any(pd.isna(v) for v in [macd_line, macd_signal, macd_hist]):
             print(f"MACD: Line={macd_line:.2f}, Signal={macd_signal:.2f}, Hist={macd_hist:.2f} ({macd_text})")
        
        # Candlesticks
        print("\nLatest Candlestick Pattern(s):")
        latest_candle_patterns_found = []
        for col in data.columns:
            if col.startswith("CDL_") and latest.get(col, 0) != 0:
                pattern_name = col.replace("CDL_", "")
                signal_val = latest.get(col)
                signal_type = "Bullish" if signal_val > 0 else "Bearish"
                if "DOJI" in pattern_name: signal_type = "Neutral/Reversal"
                latest_candle_patterns_found.append(f"{pattern_name} ({signal_type})")
        if latest_candle_patterns_found:
            for p in latest_candle_patterns_found: print(f"  - {p}")
        else: print("  - No specific common pattern detected on the latest candle.")

        # --- Optional: Ichimoku & Stochastic Interpretation (Basic) ---
        # ... (interpretation printouts as shown in previous response, if indicators were calculated) ...

        # Key Levels
        print("\nKey Levels (Approximate):")
        for ma in ['SMA_20', 'SMA_50', 'SMA_100', 'SMA_200']: print(f"  {ma}: {latest.get(ma, np.nan):.2f}")
        print(f"  Upper BB: {latest.get('BBU_20_2.0', np.nan):.2f}, Lower BB: {latest.get('BBL_20_2.0', np.nan):.2f}")
        if vwap_col_name and not pd.isna(latest.get(vwap_col_name)): print(f"  {vwap_col_name}: {latest.get(vwap_col_name):.2f}")
        if not pd.isna(poc): print(f"  Recent POC ({vp_lookback}d): {poc:.2f}")
        if not pd.isna(vah): print(f"  Recent VAH ({vp_lookback}d): {vah:.2f}")
        if not pd.isna(val): print(f"  Recent VAL ({vp_lookback}d): {val:.2f}")
        last_local_low_val = data['local_low'].dropna().tail(1)
        last_local_high_val = data['local_high'].dropna().tail(1)
        if not last_local_low_val.empty: print(f"  Last Local Low: {last_local_low_val.iloc[0]:.2f} on {last_local_low_val.index[0].strftime('%Y-%m-%d')}")
        if not last_local_high_val.empty: print(f"  Last Local High: {last_local_high_val.iloc[0]:.2f} on {last_local_high_val.index[0].strftime('%Y-%m-%d')}")

        if significant_move_identified:
            print(f"\nFibonacci Levels for move from {fib_levels.get('Move_Start_Price',np.nan):.2f} ({fib_levels.get('Move_Start_Date','N/A')}) to {fib_levels.get('Move_End_Price',np.nan):.2f} ({fib_levels.get('Move_End_Date','N/A')}) ({fib_levels.get('Move_Trend','N/A')} trend):")
            for level_name, fib_val in fib_levels.items():
                if 'Retr' in level_name or 'Ext' in level_name: print(f"  {level_name}: {fib_val:.2f}")
        
        # --- Trade Suggestion Logic ---
        print("\n--- Potential Trade Ideas (Requires Careful Consideration) ---")
        atr_val = latest.get('ATR_14', current_price * 0.015) # Fallback ATR
        if pd.isna(atr_val) or atr_val == 0: atr_val = current_price * 0.015 # Further fallback

        def get_sr_levels(latest_series, data_df, fib_data, is_support, vwap_val_in, poc_in, vah_in, val_in):
            levels = []
            for ma_c in ['SMA_20', 'SMA_50', 'SMA_100', 'SMA_200', 'EMA_9', 'EMA_21']: levels.append(latest_series.get(ma_c))
            levels.append(latest_series.get('BBL_20_2.0') if is_support else latest_series.get('BBU_20_2.0'))
            
            last_local_s = data_df['local_low'].dropna().tail(1)
            last_local_r = data_df['local_high'].dropna().tail(1)
            if is_support and not last_local_s.empty: levels.append(last_local_s.iloc[0])
            if not is_support and not last_local_r.empty: levels.append(last_local_r.iloc[0])

            if fib_data:
                for name, f_val in fib_data.items():
                    if 'Retr' in name or 'Ext' in name: levels.append(f_val)
            
            if not pd.isna(vwap_val_in): levels.append(vwap_val_in)
            if not pd.isna(poc_in): levels.append(poc_in)
            if is_support and not pd.isna(val_in): levels.append(val_in)
            if not is_support and not pd.isna(vah_in): levels.append(vah_in)
            
            return sorted(list(set(filter(lambda x: x is not None and not pd.isna(x), levels))))

        latest_vwap_val = latest.get(vwap_col_name, np.nan) if vwap_col_name else np.nan
        all_supports = get_sr_levels(latest, data, fib_levels if significant_move_identified else None, True, latest_vwap_val, poc, vah, val)
        all_resistances = get_sr_levels(latest, data, fib_levels if significant_move_identified else None, False, latest_vwap_val, poc, vah, val)

        bullish_score = 0; bearish_score = 0
        bullish_reasons = []; bearish_reasons = []

        # Bullish Scoring
        if trend in ["Up", "Strong Up"]: bullish_score += 1; bullish_reasons.append(f"Trend: {trend}")
        if not pd.isna(rsi_val) and 30 < rsi_val < 70: bullish_score +=1; bullish_reasons.append(f"RSI: {rsi_val:.1f} (Healthy)")
        elif not pd.isna(rsi_val) and rsi_val <= 30 : bullish_score +=1; bullish_reasons.append(f"RSI: {rsi_val:.1f} (Oversold - Reversal Potential)") # Added for oversold
        if macd_text == "Bullish Crossover" or macd_text == "Hist Bullish Flip" or (not pd.isna(macd_line) and not pd.isna(macd_signal) and macd_line > macd_signal):
            bullish_score +=1; bullish_reasons.append(f"MACD: {macd_text if macd_text != 'Neutral' else 'Bullish Bias'}")
        for p in latest_candle_patterns_found:
            if "Bullish" in p or "Hammer" in p or "Engulfing" in p and latest.get('Close',0) > prev.get('Close',0) : bullish_score +=1; bullish_reasons.append(f"Candle: {p}"); break
        if not pd.isna(latest_vwap_val) and current_price > latest_vwap_val: bullish_score +=1; bullish_reasons.append("Price > VWAP")
        for s_lvl in all_supports:
            if current_price >= s_lvl and current_price <= s_lvl + (0.75 * atr_val): bullish_score +=1; bullish_reasons.append(f"Near Support {s_lvl:.2f}"); break
        
        # Bearish Scoring
        if trend in ["Down", "Strong Down"]: bearish_score += 1; bearish_reasons.append(f"Trend: {trend}")
        if not pd.isna(rsi_val) and 30 < rsi_val < 70: bearish_score +=1; bearish_reasons.append(f"RSI: {rsi_val:.1f} (Healthy)")
        elif not pd.isna(rsi_val) and rsi_val >= 70 : bearish_score +=1; bearish_reasons.append(f"RSI: {rsi_val:.1f} (Overbought - Reversal Potential)") # Added for overbought
        if macd_text == "Bearish Crossover" or macd_text == "Hist Bearish Flip" or (not pd.isna(macd_line) and not pd.isna(macd_signal) and macd_line < macd_signal):
            bearish_score +=1; bearish_reasons.append(f"MACD: {macd_text if macd_text != 'Neutral' else 'Bearish Bias'}")
        for p in latest_candle_patterns_found:
            if "Bearish" in p or "Shooting Star" in p or "Hanging Man" in p or "Engulfing" in p and latest.get('Close',0) < prev.get('Close',0): bearish_score +=1; bearish_reasons.append(f"Candle: {p}"); break
        if not pd.isna(latest_vwap_val) and current_price < latest_vwap_val: bearish_score +=1; bearish_reasons.append("Price < VWAP")
        for r_lvl in all_resistances:
            if current_price <= r_lvl and current_price >= r_lvl - (0.75 * atr_val): bearish_score +=1; bearish_reasons.append(f"Near Resistance {r_lvl:.2f}"); break
            
        # Trade Suggestion Output
        min_confluence_score = 3 # Adjustable
        if bullish_score >= min_confluence_score and bullish_score > bearish_score : # Ensure bullish score is dominant
            print(f"\n  Potential Long Scenario (Confluence Score: {bullish_score}):")
            for reason in bullish_reasons: print(f"    - {reason}")
            entry_long = current_price
            sl_long = entry_long - (1.5 * atr_val)
            risk_long = entry_long - sl_long
            if risk_long > 0:
                print(f"    Entry: ~{entry_long:.2f}, SL: {sl_long:.2f} (Risk: {risk_long:.2f})")
                tp_candidates_long = sorted([r for r in all_resistances if r > entry_long + (0.5 * atr_val)]) # Meaningful TP
                tp_count = 0
                for tp in tp_candidates_long:
                    if tp_count < 3:
                        reward_long = tp - entry_long
                        rr_long = reward_long / risk_long if risk_long > 0 else 0
                        if rr_long >= 1.0: # Minimum 1:1 R:R for a structural TP
                            print(f"    TP{tp_count+1} (Struct): {tp:.2f} (Reward: {reward_long:.2f}, R:R: {rr_long:.2f}:1)")
                            tp_count += 1
                # Add R:R based TPs if not enough structural ones or to supplement
                for rr_target in [1.5, 2.5, 3.5]:
                    if tp_count < 3:
                        tp_rr_based = entry_long + (rr_target * risk_long)
                        # Ensure this R:R TP is meaningfully different from last structural TP
                        if not any(abs(tp_rr_based - existing_tp) < (0.2 * atr_val) for existing_tp in [t for t_list in [tp_candidates_long[:tp_count]] for t in t_list]):
                             print(f"    TP{tp_count+1} (R:R {rr_target:.1f}): {tp_rr_based:.2f} (Reward: {(tp_rr_based-entry_long):.2f}, R:R: {rr_target:.1f}:1)")
                             tp_count +=1


        elif bearish_score >= min_confluence_score and bearish_score > bullish_score: # Ensure bearish score is dominant
            print(f"\n  Potential Short Scenario (Confluence Score: {bearish_score}):")
            for reason in bearish_reasons: print(f"    - {reason}")
            entry_short = current_price
            sl_short = entry_short + (1.5 * atr_val)
            risk_short = sl_short - entry_short
            if risk_short > 0:
                print(f"    Entry: ~{entry_short:.2f}, SL: {sl_short:.2f} (Risk: {risk_short:.2f})")
                tp_candidates_short = sorted([s for s in all_supports if s < entry_short - (0.5 * atr_val)], reverse=True)
                tp_count = 0
                for tp in tp_candidates_short:
                    if tp_count < 3:
                        reward_short = entry_short - tp
                        rr_short = reward_short / risk_short if risk_short > 0 else 0
                        if rr_short >= 1.0:
                            print(f"    TP{tp_count+1} (Struct): {tp:.2f} (Reward: {reward_short:.2f}, R:R: {rr_short:.2f}:1)")
                            tp_count += 1
                for rr_target in [1.5, 2.5, 3.5]:
                    if tp_count < 3:
                        tp_rr_based = entry_short - (rr_target * risk_short)
                        if not any(abs(tp_rr_based - existing_tp) < (0.2 * atr_val) for existing_tp in [t for t_list in [tp_candidates_short[:tp_count]] for t in t_list]):
                            if tp_rr_based > 0: # Ensure TP is not negative
                                print(f"    TP{tp_count+1} (R:R {rr_target:.1f}): {tp_rr_based:.2f} (Reward: {(entry_short-tp_rr_based):.2f}, R:R: {rr_target:.1f}:1)")
                                tp_count +=1
        
        else: # Neither bullish nor bearish score is dominant or high enough
            print("\n  No clear high-probability long or short scenario detected based on current rules.")
            print(f"    (Bullish Score: {bullish_score}, Bearish Score: {bearish_score}, Min Confluence: {min_confluence_score})")

        return data

    except Exception as e:
        print(f"An error occurred during daily analysis for {ticker_symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None

# --- Main Execution ---
if __name__ == "__main__":
    print("--- Technical Analysis Tool (Consolidated Daily Analysis) ---")
    selected_ticker, yf_ticker_object = get_ticker_symbol_for_analysis()
    if selected_ticker and yf_ticker_object:
        daily_analysis_data = analyze_ticker_daily(selected_ticker, yf_ticker_object)
        if daily_analysis_data is not None:
            print(f"\nDaily analysis for {selected_ticker} complete. Review interpretations above.")
        else:
            print(f"\nDaily analysis for {selected_ticker} could not be completed.")