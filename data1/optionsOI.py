import requests
import pandas as pd
from bs4 import BeautifulSoup
import os
from datetime import datetime

all_rows = []
base_url = "https://finance.yahoo.com/markets/options/highest-open-interest/?start={}&count=100"

for page in range(0, 75):
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
folder_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "option OI")
os.makedirs(folder_path, exist_ok=True)

# 產生檔名格式
today_str = datetime.today().strftime("%Y-%m-%d")
file_name = f"HighestOI-{today_str}.xlsx"
file_path = os.path.join(folder_path, file_name)

# 儲存 Excel 檔案
df = pd.DataFrame(all_rows, columns=headers_row)
df.to_excel(file_path, index=False)

# 進行過濾與排序
# 排除 C 欄（index 2）為 "HYG" 的資料
df_filtered = df[df.iloc[:, 2] != "HYG"].copy()
# 將 L 欄（index 11, Open Interest）轉為數字（去除逗號），更健壯地處理非數字與空值
df_filtered = df_filtered.assign(**{
    df.columns[11]: pd.to_numeric(
        df_filtered[df.columns[11]].astype(str).str.replace(',', '', regex=False),
        errors='coerce'
    ).fillna(0).astype(int)
})
# 依 Open Interest 由大到小排序
df_sorted = df_filtered.sort_values(by=df.columns[11], ascending=False)

# 儲存排序後檔案
sorted_file_name = f"Sorted-{today_str}.xlsx"
sorted_file_path = os.path.join(folder_path, sorted_file_name)
df_sorted.to_excel(sorted_file_path, index=False)
print(f"Done: Filtered out HYG and sorted by highest Open Interest. Saved to {sorted_file_path}")


