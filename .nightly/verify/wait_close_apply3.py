# -*- coding: utf-8 -*-
"""ビューア（8555）が閉じるのを待ってから、3 回目の当たりを apply_fixes.py --write で置き換える（承認者 案A）。1 分に 1 行。上限 2 時間。"""
import socket, subprocess, sys, time, datetime
sys.stdout.reconfigure(encoding="utf-8")
def is_open():
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", 8555)) == 0
end, last = time.time() + 7200, 0
while is_open():
    if time.time() - last >= 60:
        print(f"{datetime.datetime.now():%H:%M} ビューアが開いている。閉じるのを待つ", flush=True); last = time.time()
    if time.time() > end:
        print("END TIMEOUT（書いていない）", flush=True); sys.exit(1)
    time.sleep(2)
print(f"{datetime.datetime.now():%H:%M:%S} 8555 が閉じた", flush=True)
time.sleep(3)
r = subprocess.run([r"C:\Users\user\ndlocr-lite-custom\.venv\Scripts\python.exe", r".nightly\verify\apply_fixes.py", "141",
                    r"work\proofread\141号_3回目_指揮官の確認.csv", "--write"],
                   cwd=r"C:\Users\user\ndlocr-lite-custom", capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout, flush=True)
if r.stderr.strip(): print("stderr:", r.stderr[-1500:], flush=True)
print(f"END exit={r.returncode}", flush=True)
