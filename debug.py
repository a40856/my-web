import csv
import requests
import time
import random
from bs4 import BeautifulSoup

# List of tickers
ticker = "nvda"

# Function to fetch stock data from Finviz
def fetch_data_from_finviz(ticker):
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", class_="snapshot-table2")
        if not table:
            raise ValueError("Could not find the target table on Finviz")
        rows = table.find_all("tr")
        
        # Debug: 印出所有 row/col 資料
        print("--- Finviz Table Rows ---")
        for i, row in enumerate(rows):
            cols = row.find_all("td")
            print(f"Row {i}: {[col.text.strip() for col in cols]}")
        print("-------------------------")
        
        # Extract values from specific positions
        def extract_value(row, col):
            try:
                return rows[row].find_all("td")[col].text.strip().replace("*", "").replace("%", "")
            except:
                return "N/A"
        
        name_tag = soup.find("a", class_="tab-link block truncate")
        name = name_tag.text.strip() if name_tag else "N/A"
        price_tag = soup.find("strong", class_="quote-price_wrapper_price")
        price = price_tag.text.strip() if price_tag else "N/A"
        
        # Extract values from correct columns (cross-checked)
        previous_close = extract_value(11, 9)
        price = extract_value(12, 11)
        percent_change = extract_value(13, 11)  # Change (%)
        # SMA/EMA values (cross-checked)
        ema_20 = extract_value(10, 7)  # SMA20 value is in col 7
        ema_50 = extract_value(11, 7)  # SMA50 value is in col 7
        ema_200 = extract_value(12, 7) # SMA200 value is in col 7
        # RSI & ATR (cross-checked)
        rsi = extract_value(9, 9)      # RSI (14) value is in col 9
        atr = extract_value(8, 9)      # ATR (14) value is in col 9
        market_cap = extract_value(1, 1)
        ytd_percent = extract_value(4, 11)
        return_12m = extract_value(5, 11)
        # day_change 不再計算，直接用 percent_change
        # 52W High/Low
        high_52w = extract_value(5, 9)
        low_52w = extract_value(6, 9)
        
        return {
            "Name": name,
            "Price": price,
            "% Change": percent_change,
            "SMA20": ema_20,
            "SMA50": ema_50,
            "SMA200": ema_200,
            "YTD %": ytd_percent,
            "12M Return": return_12m,
            "RSI": rsi,
            "Market Cap": market_cap,
            "ATR": atr,
            "52W High": high_52w,
            "52W Low": low_52w
        }
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

if __name__ == "__main__":
    info = fetch_data_from_finviz(ticker)
    if info:
        print(f"[{ticker}] Extracted:")
        for k, v in info.items():
            print(f"  {k}: {v}")
    else:
        print(f"資料擷取失敗：{ticker}")
