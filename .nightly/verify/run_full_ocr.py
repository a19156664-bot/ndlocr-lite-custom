# -*- coding: utf-8 -*-
"""全体OCR（work\\output\\01_raw_ocr\\国際寫眞新聞_<号>号.json）を号ごとに順に作る（10-09 夜・166〜170号）。
142〜145号の json に記録された render_dpi 300 に合わせる。json が既にある号は飛ばす。1 号ずつ開始と終了の時刻を出す。

    .venv\\Scripts\\python.exe .nightly\\verify\\run_full_ocr.py 166 167 168 169 170
"""
import os, sys, subprocess, datetime
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"C:\Users\user\ndlocr-lite-custom"
OUT = os.path.join(BASE, "work", "output", "01_raw_ocr")
PY = os.path.join(BASE, ".venv", "Scripts", "python.exe")
now = lambda: datetime.datetime.now().strftime("%H:%M:%S")
for n in sys.argv[1:]:
    stem = f"国際寫眞新聞_{n}号"
    if os.path.exists(os.path.join(OUT, stem + ".json")):
        print(now(), n, "json あり → 飛ばす", flush=True); continue
    print(now(), n, "全体OCR 開始", flush=True)
    r = subprocess.run([PY, os.path.join(BASE, "src", "ocr.py"),
                        "--sourcepdf", os.path.join(BASE, "work", stem + ".pdf"),
                        "--output", OUT, "--pdf-render-dpi", "300",
                        "--pdf-output", os.path.join(OUT, stem + "_text.pdf")],
                       cwd=BASE, capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = os.path.exists(os.path.join(OUT, stem + ".json"))
    print(now(), n, "全体OCR 終了 exit", r.returncode, "json", "あり" if ok else "なし", flush=True)
    if not ok:
        print((r.stdout + r.stderr)[-1500:], flush=True)
