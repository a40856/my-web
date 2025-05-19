import numpy as np
from scipy.stats import norm
import pandas as pd
from datetime import date, datetime, timedelta
import yfinance as yf

# --- Black-Scholes-Merton Model (ensure this is complete from previous versions) ---
def black_scholes_merton(S, K, T, r, sigma, option_type='call', q=0.0):
    if T < 0: T = 0
    if T == 0:
        if option_type == 'call': return max(0, S - K)
        else: return max(0, K - S)
    if sigma <= 0 : # Treat as intrinsic if no volatility
        if option_type == 'call': return max(0, S - K)
        else: return max(0, K - S)

    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == 'call':
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    elif option_type == 'put':
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    else:
        raise ValueError("option_type must be 'call' or 'put'")
    return price

# --- Greeks (ensure these are complete from previous versions) ---
def delta(S, K, T, r, sigma, option_type='call', q=0.0):
    if T <= 0: return 1.0 if S > K and option_type=='call' else (-1.0 if K > S and option_type=='put' else 0.0)
    if sigma <= 0: return 1.0 if S > K and option_type=='call' else (-1.0 if K > S and option_type=='put' else 0.0)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    if option_type == 'call': return np.exp(-q * T) * norm.cdf(d1)
    else: return np.exp(-q * T) * (norm.cdf(d1) - 1)

def gamma(S, K, T, r, sigma, q=0.0):
    if T <= 0 or sigma <= 0: return 0.0
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))

def theta(S, K, T, r, sigma, option_type='call', q=0.0):
    if T <= 0 or sigma <= 0: return 0.0
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == 'call':
        term1 = - (S * np.exp(-q * T) * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
        term2 = - r * K * np.exp(-r * T) * norm.cdf(d2)
        term3 = q * S * np.exp(-q * T) * norm.cdf(d1)
    else: # put
        term1 = - (S * np.exp(-q * T) * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
        term2 = r * K * np.exp(-r * T) * norm.cdf(-d2)
        term3 = -q * S * np.exp(-q * T) * norm.cdf(-d1)
    return (term1 + term2 + term3) / 365.25

def vega(S, K, T, r, sigma, q=0.0):
    if T <= 0 or sigma <= 0: return 0.0
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T) / 100

# --- P/L Table Generator (no significant changes needed here for this request) ---
def generate_pl_table(
    option_type,
    action,
    strike_price,
    initial_premium_per_share, # This will be the user's entry price
    num_contracts,
    expiration_date_obj,
    current_stock_price_at_analysis,
    fetched_implied_volatility,
    risk_free_rate,
    dividend_yield=0.0,
    analysis_start_date=date.today(),
    num_dates_to_show=7,
    stock_price_range_percent=0.15,
    stock_price_steps=21
):
    multiplier = 100
    dates_for_table = []
    if analysis_start_date < expiration_date_obj:
        days_to_expiration_total = (expiration_date_obj - analysis_start_date).days
        if num_dates_to_show > days_to_expiration_total + 1:
            num_dates_to_show = days_to_expiration_total + 1
        dates_for_table.append(analysis_start_date)
        if num_dates_to_show > 1:
            days_between_points = max(1, days_to_expiration_total // (num_dates_to_show -1 if num_dates_to_show > 1 else 1) )
            current_analysis_date = analysis_start_date
            for _ in range(num_dates_to_show - 2):
                current_analysis_date += timedelta(days=days_between_points)
                if current_analysis_date < expiration_date_obj: dates_for_table.append(current_analysis_date)
                else: break
    if expiration_date_obj not in dates_for_table: dates_for_table.append(expiration_date_obj)
    dates_for_table = sorted(list(set(dates_for_table)))

    min_stock_price = current_stock_price_at_analysis * (1 - stock_price_range_percent)
    max_stock_price = current_stock_price_at_analysis * (1 + stock_price_range_percent)
    stock_prices_scenarios = np.linspace(min_stock_price, max_stock_price, stock_price_steps)

    column_names = [d.strftime('%b %d') if d != expiration_date_obj else 'Exp ' + d.strftime('%b %d') for d in dates_for_table]
    if len(column_names) != len(set(column_names)):
        for i, d_obj in enumerate(dates_for_table):
            if d_obj == expiration_date_obj: column_names[i] = 'Exp ' + d_obj.strftime('%b %d'); break
    
    df_pl = pd.DataFrame(index=[f"{price:.2f}" for price in stock_prices_scenarios], columns=column_names)

    for analysis_date_col_obj in dates_for_table:
        col_name_for_df = analysis_date_col_obj.strftime('%b %d')
        if analysis_date_col_obj == expiration_date_obj: col_name_for_df = 'Exp ' + analysis_date_col_obj.strftime('%b %d')
        
        T_to_actual_expiry = (expiration_date_obj - analysis_date_col_obj).days / 365.25
        
        for S_scenario in stock_prices_scenarios:
            option_value_at_point = black_scholes_merton(S_scenario, strike_price, T_to_actual_expiry, risk_free_rate, fetched_implied_volatility, option_type, dividend_yield)
            if action == 'buy': profit_loss = (option_value_at_point - initial_premium_per_share) * num_contracts * multiplier
            else: profit_loss = (initial_premium_per_share - option_value_at_point) * num_contracts * multiplier
            df_pl.loc[f"{S_scenario:.2f}", col_name_for_df] = round(profit_loss)

    percent_change_col = [f"{((S_scenario - current_stock_price_at_analysis) / current_stock_price_at_analysis) * 100:.2f}%" for S_scenario in stock_prices_scenarios]
    df_pl['+/- % (from current)'] = percent_change_col
    cols = ['+/- % (from current)'] + [col for col in df_pl.columns if col != '+/- % (from current)']
    df_pl = df_pl[cols]
    return df_pl

# --- User Input Functions (mostly same, slight adjustment in main for premium) ---
def get_ticker_symbol():
    while True:
        ticker_sym = input("Enter Ticker Symbol (e.g., AMD, SPY): ").upper()
        if ticker_sym:
            try:
                yf_ticker = yf.Ticker(ticker_sym)
                if yf_ticker.info and ('currentPrice' in yf_ticker.info or 'regularMarketPreviousClose' in yf_ticker.info or not yf_ticker.history(period="1d").empty):
                    return ticker_sym, yf_ticker
                else:
                    print(f"Could not retrieve sufficient data for {ticker_sym}. Please try again.")
            except Exception as e:
                print(f"Error fetching ticker {ticker_sym}: {e}. Please ensure it's correct and try again.")
        else:
            print("Ticker symbol cannot be empty.")

def get_option_type():
    while True:
        otype = input("Enter Option Type ('call' or 'put'): ").lower()
        if otype in ['call', 'put']: return otype
        print("Invalid option type.")

def get_action():
    while True:
        act = input("Enter Action ('buy' or 'sell'): ").lower()
        if act in ['buy', 'sell']: return act
        print("Invalid action.")

def get_expiration_date(yf_ticker_obj):
    expirations = yf_ticker_obj.options
    if not expirations: print("No option expiration dates found."); return None
    print("\nAvailable Expiration Dates:")
    for i, exp_date_str in enumerate(expirations): print(f"{i+1}. {exp_date_str}")
    while True:
        try:
            choice = int(input("Select Expiration Date (number): "))
            if 1 <= choice <= len(expirations): return expirations[choice-1]
            print("Invalid choice.")
        except ValueError: print("Invalid input.")

def get_strike_price_and_details(yf_ticker_obj, expiration_date_str, option_type_val):
    try: opt_chain = yf_ticker_obj.option_chain(expiration_date_str)
    except Exception as e: print(f"Could not fetch option chain for {expiration_date_str}: {e}"); return None, None, None, None, None
    
    chain_df = opt_chain.calls if option_type_val == 'call' else opt_chain.puts
    if chain_df.empty: print(f"No {option_type_val} options found for {expiration_date_str}."); return None, None, None, None, None

    print(f"\nAvailable {option_type_val.capitalize()} Strikes for {expiration_date_str} (showing a subset):")
    display_df = chain_df[['strike', 'lastPrice', 'impliedVolatility', 'bid', 'ask']].copy()
    display_df.reset_index(drop=True, inplace=True)
    
    max_display = 30
    if len(display_df) > max_display:
        print(display_df.head(max_display // 2).to_string()); print("..."); print(display_df.tail(max_display // 2).to_string())
    else: print(display_df.to_string())

    while True:
        try:
            choice_str = input(f"Select Strike (number from table or type strike value e.g. 150.0): ")
            selected_option_row = None
            if '.' in choice_str:
                strike_val = float(choice_str)
                selected_option_row_df = chain_df[chain_df['strike'] == strike_val]
                if not selected_option_row_df.empty: selected_option_row = selected_option_row_df.iloc[0]
                else: print(f"Strike {strike_val} not found."); continue
            else:
                choice_idx = int(choice_str) -1
                if 0 <= choice_idx < len(display_df):
                    target_strike = display_df.loc[choice_idx, 'strike']
                    selected_option_row_df = chain_df[chain_df['strike'] == target_strike]
                    if not selected_option_row_df.empty: selected_option_row = selected_option_row_df.iloc[0]
                else: print("Invalid choice number."); continue
            
            if selected_option_row is not None:
                strike = selected_option_row['strike']
                market_premium = selected_option_row['lastPrice'] # This is current market price
                iv = selected_option_row['impliedVolatility']
                bid = selected_option_row.get('bid', market_premium) # Fallback to lastPrice if bid not avail
                ask = selected_option_row.get('ask', market_premium) # Fallback to lastPrice if ask not avail
                if iv == 0.0: print("Warning: 'impliedVolatility' is 0.0. Results might be inaccurate.")
                print(f"Selected: Strike={strike}, Market Last Price={market_premium:.2f}, Bid={bid:.2f}, Ask={ask:.2f}, IV={iv:.4f}")
                return strike, market_premium, iv, bid, ask # Return bid and ask too
            else: print("Could not identify selected option."); continue
        except ValueError: print("Invalid input.")
        except KeyError as e: print(f"Missing data: {e}"); return None, None, None, None, None

def get_num_contracts():
    while True:
        try:
            contracts = int(input("Enter Number of Contracts: "))
            if contracts > 0: return contracts
            print("Number of contracts must be positive.")
        except ValueError: print("Invalid input.")

def get_user_entry_price(default_market_price):
    while True:
        try:
            user_price_str = input(f"Enter YOUR entry price per share for this option (or press Enter to use current market price ${default_market_price:.2f}): ")
            if not user_price_str: # User pressed Enter
                return default_market_price
            user_price = float(user_price_str)
            if user_price >= 0:
                return user_price
            print("Entry price cannot be negative.")
        except ValueError:
            print("Invalid price format. Please enter a number (e.g., 2.50).")


# --- Main Execution ---
if __name__ == "__main__":
    ticker_symbol, yf_ticker_obj = get_ticker_symbol()
    
    try:
        stock_info = yf_ticker_obj.info
        current_stock_price = stock_info.get('currentPrice', stock_info.get('regularMarketPrice', stock_info.get('regularMarketPreviousClose')))
        if current_stock_price is None:
            hist = yf_ticker_obj.history(period="1d")
            if not hist.empty: current_stock_price = hist['Close'].iloc[-1]
            else: print("Could not fetch current stock price."); exit()
        dividend_yield = stock_info.get('dividendYield', 0.0); dividend_yield = dividend_yield if dividend_yield is not None else 0.0
        print(f"\nCurrent {ticker_symbol} Price: ${current_stock_price:.2f}, Dividend Yield: {dividend_yield*100:.2f}%")
    except Exception as e: print(f"Error fetching stock info: {e}"); exit()

    option_type_val = get_option_type()
    action_val = get_action() # 'buy' or 'sell' (this is for opening the position)
    
    exp_date_str = get_expiration_date(yf_ticker_obj)
    if not exp_date_str: exit()
    try: expiration_date_object = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
    except ValueError: print(f"Error parsing expiration date: {exp_date_str}"); exit()

    # Fetches market data for the selected option
    strike_price_val, market_premium_val, iv_val, market_bid_val, market_ask_val = get_strike_price_and_details(yf_ticker_obj, exp_date_str, option_type_val)
    if strike_price_val is None: exit()

    num_contracts_val = get_num_contracts()

    # *** NEW: Get user's actual entry price ***
    actual_entry_premium_per_share = get_user_entry_price(market_premium_val)
    print(f"Using entry premium per share: ${actual_entry_premium_per_share:.2f} for P/L calculations.")

    risk_free_rate_val = 0.05 
    print(f"Using Risk-Free Rate: {risk_free_rate_val*100:.2f}% (assumed)")

    print("\nGenerating Projected P/L Table (based on your entry price)...")
    pl_table = generate_pl_table(
        option_type=option_type_val,
        action=action_val, # This is the action taken to OPEN the position
        strike_price=strike_price_val,
        initial_premium_per_share=actual_entry_premium_per_share, # USER'S ENTRY PRICE
        num_contracts=num_contracts_val,
        expiration_date_obj=expiration_date_object,
        current_stock_price_at_analysis=current_stock_price,
        fetched_implied_volatility=iv_val,
        risk_free_rate=risk_free_rate_val,
        dividend_yield=dividend_yield,
        analysis_start_date=date.today(),
        num_dates_to_show=8,
        stock_price_range_percent=0.20,
        stock_price_steps=21
    )

    print(f"\n--- Projected P/L Table for {num_contracts_val} {action_val.upper()} {ticker_symbol} {expiration_date_object.strftime('%d %b %Y')} {strike_price_val:.2f} {option_type_val.upper()} ---")
    print(f"--- Your Entry Price per share: ${actual_entry_premium_per_share:.2f} | Current Market IV: {iv_val*100:.2f}% ---")
    print(pl_table.to_string())
    
    # --- Calculate and Display CURRENT P/L based on actual entry and current market price ---
    print("\n--- Current Position Status ---")
    print(f"Your Entry Price per Share: ${actual_entry_premium_per_share:.2f}")
    
    # Determine current exit price (bid for selling an owned call/put, ask for buying back a shorted call/put)
    current_exit_premium_per_share = 0
    if action_val == 'buy': # If you BOUGHT to open, you SELL to close (use BID)
        current_exit_premium_per_share = market_bid_val
        print(f"Current Market Bid (to sell): ${market_bid_val:.2f}")
        current_pl_per_share = market_bid_val - actual_entry_premium_per_share
    else: # action_val == 'sell' (If you SOLD to open, you BUY to close (use ASK))
        current_exit_premium_per_share = market_ask_val
        print(f"Current Market Ask (to buy back): ${market_ask_val:.2f}")
        current_pl_per_share = actual_entry_premium_per_share - market_ask_val

    current_total_pl = current_pl_per_share * num_contracts_val * 100 # 100 shares per contract
    
    print(f"Current P/L per Share: ${current_pl_per_share:.2f}")
    print(f"Current Total P/L for {num_contracts_val} contract(s): ${current_total_pl:.2f}")
    if actual_entry_premium_per_share > 0: # Avoid division by zero if entry was free (e.g. part of spread not modeled here)
        current_pl_percentage = (current_pl_per_share / actual_entry_premium_per_share) * 100
        print(f"Current P/L Percentage (on premium paid/received): {current_pl_percentage:.2f}%")


    # --- Optional: Display Greeks at current conditions (no change needed here) ---
    print("\n--- Greeks at current market conditions (approximate, based on fetched IV) ---")
    T_to_expiry_now = (expiration_date_object - date.today()).days / 365.25
    if T_to_expiry_now < 0: T_to_expiry_now = 0
        
    calc_delta = delta(current_stock_price, strike_price_val, T_to_expiry_now, risk_free_rate_val, iv_val, option_type_val, dividend_yield)
    calc_gamma = gamma(current_stock_price, strike_price_val, T_to_expiry_now, risk_free_rate_val, iv_val, dividend_yield)
    calc_theta = theta(current_stock_price, strike_price_val, T_to_expiry_now, risk_free_rate_val, iv_val, option_type_val, dividend_yield)
    calc_vega = vega(current_stock_price, strike_price_val, T_to_expiry_now, risk_free_rate_val, iv_val, dividend_yield)
    
    print(f"  Delta: {calc_delta:.4f}")
    print(f"  Gamma: {calc_gamma:.4f}")
    print(f"  Theta (per day): ${calc_theta:.4f}")
    print(f"  Vega (per 1% IV change): ${calc_vega:.4f}")

    bsm_current_price = black_scholes_merton(current_stock_price, strike_price_val, T_to_expiry_now, risk_free_rate_val, iv_val, option_type_val, dividend_yield)
    print(f"  BSM Theoretical Price: ${bsm_current_price:.2f} (Market Last Price was ${market_premium_val:.2f})")