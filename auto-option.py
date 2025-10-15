import subprocess
import os
import sys

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

# 自動執行 step1.py 與 step2.py
# 先執行 step1.py（建立 sheet）
print("Running step1.py...")
result1 = subprocess.run([sys.executable, "step1.py"], cwd="/workspaces/my-web")
if result1.returncode != 0:
    print("step1.py 執行失敗！")
    sys.exit(result1.returncode)

# 再執行 step2.py（處理 sheet）
print("Running step2.py...")
result2 = subprocess.run([sys.executable, "step2.py"], cwd="/workspaces/my-web")
if result2.returncode != 0:
    print("step2.py 執行失敗！")
    sys.exit(result2.returncode)

print("All tasks completed.")
