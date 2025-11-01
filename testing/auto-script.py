#!/usr/bin/env python3
# auto-option.py
# 這個 runner 會依序執行 step1..step4，並把當次產生的 .xlsx/.csv 檔集中到 outputs/<timestamp>/

import subprocess
import sys
import os
import shutil
import time
from datetime import datetime
from glob import glob

ROOT = os.path.abspath(os.path.dirname(__file__))  # repo root
os.chdir(ROOT)

# output folder (timestamped)
TS = datetime.now().strftime("%Y-%m-%d_%H%M%S")
OUT_BASE = os.path.join(ROOT, "outputs")
OUT_DIR = os.path.join(OUT_BASE, TS)
os.makedirs(OUT_DIR, exist_ok=True)

# files that existed before run (to detect newly created/modified files)
pre_existing = set(glob(os.path.join(ROOT, "*.*")))

# simple logger to file + stdout
log_path = os.path.join(OUT_DIR, "auto-option.log")
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# list the scripts to run in order (use relative paths if scripts live in subfolders)
# In this repo your scripts are under the `data1/` folder, so call them with that prefix.
SCRIPTS = [
    os.path.join(ROOT, "Mostactive.py"),
    os.path.join(ROOT, "optionsOI.py"),
    os.path.join(ROOT, "step1.py"),
    os.path.join(ROOT, "step2.py"),
]

def run_script(script):
    # Run each script and capture stdout/stderr to a per-script log file in testing/logs
    script_name = os.path.splitext(os.path.basename(script))[0]
    per_log_dir = os.path.join(ROOT, "logs")
    os.makedirs(per_log_dir, exist_ok=True)
    per_log_path = os.path.join(per_log_dir, f"{script_name}.log")

    log(f"RUN START: {script} (log: {per_log_path})")
    start = time.time()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    # Run and stream output to per-script log file
    with open(per_log_path, "wb") as pf:
        proc = subprocess.run([sys.executable, script], cwd=ROOT, env=env, stdout=pf, stderr=subprocess.STDOUT)

    # Append a short tail of the per-script log into the main auto log for quick glance
    try:
        with open(per_log_path, "rb") as pf:
            content = pf.read().decode("utf-8", errors="replace")
            tail = content[-8192:]
            if tail:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write("\n" + tail + "\n")
    except Exception:
        pass

    if proc.returncode != 0:
        log(f"ERROR: {script} exited with code {proc.returncode} (see {per_log_path})")
        raise SystemExit(proc.returncode)

    elapsed = time.time() - start
    log(f"RUN OK: {script} ({elapsed:.1f}s)")

try:
    log("Auto-option run started.")
    # run each script in order
    for s in SCRIPTS:
        if not os.path.exists(os.path.join(ROOT, s)):
            log(f"WARNING: script {s} not found - skipping")
            continue
        run_script(s)

    # collect outputs: any new or modified .xlsx/.csv in ROOT will be moved into OUT_DIR
    # (also include files created in subfolders if you prefer)
    moved = []
    now = time.time()
    for pattern in ("*.xlsx", "*.xls", "*.csv", "*.json"):
        for path in glob(os.path.join(ROOT, pattern)):
            if path in pre_existing:
                # if existed before but modified recently, move it too
                mtime = os.path.getmtime(path)
                if mtime >= (time.time() - 24*3600):  # modified within 24h (tunable)
                    dest = os.path.join(OUT_DIR, os.path.basename(path))
                    shutil.move(path, dest)
                    moved.append(dest)
            else:
                # newly created
                dest = os.path.join(OUT_DIR, os.path.basename(path))
                shutil.move(path, dest)
                moved.append(dest)

    log(f"Moved {len(moved)} files to {OUT_DIR}: {moved}")
    log("Auto-option run finished successfully.")
except Exception as e:
    log(f"Fatal error: {e}")
    raise