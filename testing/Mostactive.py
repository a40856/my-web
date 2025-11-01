import requests
import pandas as pd
from bs4 import BeautifulSoup
import os
from datetime import datetime

all_rows = []
base_url = "https://finance.yahoo.com/markets/options/most-active/?start={}&count=100"

for page in range(0, 50):
    start = page * 100
    url = base_url.format(start)
    print(f"Fetching: {url}")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    if not table:
        print(f"Error: No table found on page {page+1}")
        continue
    # Get table headers
    if page == 0:
        headers_row = [th.text.strip() for th in table.find_all('th')]
    # Get data rows
    for tr in table.find_all('tr')[1:]:
        row = [td.text.strip() for td in tr.find_all('td')]
        if row:
            all_rows.append(row)


# 建立資料夾（若不存在）
folder_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "testing/active")
os.makedirs(folder_path, exist_ok=True)

# 產生檔名格式
today_str = datetime.today().strftime("%Y-%m-%d")
file_name = f"Mostactive-{today_str}.xlsx"
file_path = os.path.join(folder_path, file_name)

# 儲存 Excel 檔案
df = pd.DataFrame(all_rows, columns=headers_row)
df.to_excel(file_path, index=False)
