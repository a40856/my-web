import subprocess
import os

# 取得 data1 資料夾路徑
base_dir = os.path.dirname(os.path.abspath(__file__))
data1_dir = os.path.join(base_dir, "data1")

# 執行 Mostactive.py
mostactive_path = os.path.join(data1_dir, "Mostactive.py")
print("Running Mostactive.py...")
subprocess.run(["python3", mostactive_path], check=True)

# 執行 optionsOI.py
optionsOI_path = os.path.join(data1_dir, "optionsOI.py")
print("Running optionsOI.py...")
subprocess.run(["python3", optionsOI_path], check=True)

print("All tasks completed.")
