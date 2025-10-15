import csv
import requests
import time
import random
from bs4 import BeautifulSoup

# List of tickers
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
        
        # Extract Previous Close and Day Close
        previous_close = extract_value(10, 11)
        day_close = extract_value(11, 11)
        
        # Calculate Day Change
        try:
            day_change = round(float(day_close) - float(previous_close), 2)
        except ValueError:
            day_change = "N/A"
        
        percent_change = extract_value(12, 11)
        ema_20 = extract_value(12, 1)
        ema_50 = extract_value(12, 3)
        ema_200 = extract_value(12, 5)
        ytd_percent = extract_value(5, 11)
        return_12m = extract_value(4, 11)
        rsi = extract_value(8, 9)
        market_cap = extract_value(1, 1)
        atr = extract_value(7, 11)  # ATR added here

        
        return {
            "Name": name,
            "Price": price,
            "Day Change": day_change,
            "% Change": percent_change,
            "20 EMA": ema_20,
            "50 EMA": ema_50,
            "200 EMA": ema_200,
            "YTD %": ytd_percent,
            "12M Return": return_12m,
            "RSI": rsi,
            "Market Cap": market_cap,
            "ATR": atr  # Include ATR in return

        }
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

# Fetch data for all tickers and save to a CSV
output_file = "stock_data.csv"
with open(output_file, mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Ticker", "Name", "Price", "Day Change", "% Change", "20 EMA", "50 EMA", "200 EMA", "YTD %", "12M Return", "RSI", "ATR", "Market Cap"])  # Add headers

    for ticker in tickers:
        finviz_data = fetch_data_from_finviz(ticker)
        
        if finviz_data:
            writer.writerow([
                ticker, finviz_data["Name"], finviz_data["Price"], finviz_data["Day Change"], finviz_data["% Change"],
                finviz_data["20 EMA"], finviz_data["50 EMA"], finviz_data["200 EMA"], finviz_data["YTD %"], finviz_data["12M Return"], finviz_data["RSI"], finviz_data["ATR"],finviz_data["Market Cap"]
            ])  # Save each result
            print(f"Saved data for {ticker}")
        
        time.sleep(random.uniform(1, 2))  # Introduce a random delay between 2 to 6 seconds

print(f"Data saved to {output_file}")
