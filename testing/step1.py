import csv
import requests
import time
import random
import sys
from pathlib import Path
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
    "RDDT", "GRAB", "GLW", "NNE", "ZS", "TWLO","FSLR", "NBIS", "PENN","DKNG", "LMND", "DDOG", "CRWV", "CRCL",
    "LEU", "ASPI", "APLD", "ALAB", "VRT", "RGTI", "HIMS", "AI", "GRAB", "S", "OSCR", "IBIT", "IREN", "ETHA",
    "CMG", "WDC", "ONDS","AVAV", "UMAC","FLNC", "SNDK", "RR", 

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
            "20 SMA": ema_20,
            "50 SMA": ema_50,
            "200 SMA": ema_200,
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

# Ensure outputs are written relative to this script's directory (testing/)
BASE_DIR = Path(__file__).resolve().parent
output_file = BASE_DIR / "stock_data.csv"
try:
    file = open(output_file, mode="w", newline="")
except Exception as e:
    print(f"Failed to open output file {output_file}: {e}")
    sys.exit(1)
with file as f:
    writer = csv.writer(f)
    writer = csv.writer(file)
    # Updated headers to match returned keys from fetch_data_from_finviz
    writer.writerow([
        "Ticker", "Name", "Price", "% Change", "20 SMA", "50 SMA", "200 SMA",
        "YTD %", "12M Return", "RSI", "ATR", "Market Cap", "52W High", "52W Low"
    ])

    for ticker in tickers:
        finviz_data = fetch_data_from_finviz(ticker)

        if finviz_data:
            writer.writerow([
                ticker,
                finviz_data.get("Name", "N/A"),
                finviz_data.get("Price", "N/A"),
                finviz_data.get("% Change", "N/A"),
                finviz_data.get("20 SMA", "N/A"),
                finviz_data.get("50 SMA", "N/A"),
                finviz_data.get("200 SMA", "N/A"),
                finviz_data.get("YTD %", "N/A"),
                finviz_data.get("12M Return", "N/A"),
                finviz_data.get("RSI", "N/A"),
                finviz_data.get("ATR", "N/A"),
                finviz_data.get("Market Cap", "N/A"),
                finviz_data.get("52W High", "N/A"),
                finviz_data.get("52W Low", "N/A"),
            ])  # Save each result
            print(f"Saved data for {ticker}")

    # sleep 1 second between ticker requests to avoid rate-limiting/glitches on the server
    time.sleep(1)

print(f"Data saved to {output_file}")
