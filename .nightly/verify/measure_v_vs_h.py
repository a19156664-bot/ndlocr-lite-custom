# -*- coding: utf-8 -*-
"""夜間の一括処理で、枠を「縦で読む」と「この枠だけOCR」のどちらで読むと、人が直した最終の文字に近いかを測る（10-08）。
正解: 141号の保存（work.json）の edits（人の検品と校正の後の文字）。読むだけ。書くのは標準出力と scratchpad の CSV だけ。
選び方: 直した文字が 30 字以上ある枠を、頁ごとに最大 1 つ、頁の順に最大 N 個（引数・既定 24）。
近さ: 正解の字（空白・改行・｜を除く）のうち、同じ順で一致した字の割合（difflib）。1 分に 1 行は出る。"""
import os, sys, json, glob, time, csv, difflib, datetime
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"C:\Users\user\ndlocr-lite-custom"
os.chdir(BASE); sys.path.insert(0, BASE)
from custom_gui import vertical_ocr
from custom_gui.region_ocr import region_ocr_text
N = int(sys.argv[1]) if len(sys.argv) > 1 else 24
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, "work", "proofread", "141号_縦と横の比べ.csv")
IMG = os.path.join(BASE, "work", "cache_images", "141号", "国際寫眞新聞_141号_p{:04d}.png")
def norm(s): return "".join(ch for ch in s if not ch.isspace() and ch not in "|｜")
def score(truth, out):
    a, b = norm(truth), norm(out)
    if not a: return 0.0
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(x.size for x in sm.get_matching_blocks()) / len(a)
picks = []
for f in sorted(glob.glob(os.path.join(BASE, "work", ".ndlocr_cache", "国際寫眞新聞_141号_p*.work.json"))):
    pg = int(os.path.basename(f)[-14:-10])
    st = json.load(open(f, encoding="utf-8"))
    for r in st["rects"]:
        t = st["edits"].get(r["rect_id"], "")
        if r["rect_id"] != "1" and len(norm(t)) >= 30:
            picks.append((pg, r["rect_id"], tuple(r["bbox"]), t)); break
picks = picks[:N]
print(f"{datetime.datetime.now():%H:%M} 枠 {len(picks)} 個", flush=True)
rec = vertical_ocr.get_recognizer()
rows = []
for i, (pg, rid, bbox, truth) in enumerate(picks, 1):
    t0 = time.time(); v = vertical_ocr.vertical_ocr_text(IMG.format(pg), bbox, recognizer=rec); tv = time.time() - t0
    t0 = time.time()
    try:
        h = region_ocr_text(IMG.format(pg), bbox)
    except Exception as e:
        h = ""
    th = time.time() - t0
    sv, sh = score(truth, v), score(truth, h)
    w, hgt = bbox[2] - bbox[0], bbox[3] - bbox[1]
    rows.append([pg, rid, round(w), round(hgt), len(norm(truth)), round(sv, 3), round(sh, 3), round(tv, 1), round(th, 1)])
    print(f"{datetime.datetime.now():%H:%M} [{i}/{len(picks)}] p{pg} R{rid} 枠{round(w)}x{round(hgt)} 正解{len(norm(truth))}字 縦{sv:.2f} 横{sh:.2f} ({tv:.0f}s/{th:.0f}s)", flush=True)
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    wr = csv.writer(f); wr.writerow(["頁", "枠", "幅", "高さ", "正解字数", "縦で読む", "この枠だけOCR", "縦の秒", "横の秒"]); wr.writerows(rows)
n = len(rows)
if n:
    mv = sum(r[5] for r in rows) / n; mh = sum(r[6] for r in rows) / n
    best = sum(max(r[5], r[6]) for r in rows) / n
    print(f"END 枠 {n}: 平均 縦 {mv:.3f} / 横 {mh:.3f} / 良い方を選べたら {best:.3f}。縦が勝ち {sum(r[5] > r[6] for r in rows)}・横が勝ち {sum(r[6] > r[5] for r in rows)}", flush=True)
print("書いた:", OUT, flush=True)
