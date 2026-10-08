# -*- coding: utf-8 -*-
"""⑤ で指揮官が判定するための拡大（読むだけ）。確認の CSV の行ごとに、枠の中の全体 OCR の行から
「入力値」「正しくは」に近い行を上位 2 つ選び、一致した字の前後 6 字を拡大して並べる（verify_ag1b.py と同じ考え）。
縦の行は縦のまま、横の行は横のまま。1 枚に 6 件ずつ。
使い方: .venv\\Scripts\\python.exe .nightly\\verify\\judge_crops.py <号> <確認の CSV> <書き先フォルダ> [番号 …]"""
import os, sys, csv, json, difflib
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image, ImageDraw
BASE = r"C:\Users\user\ndlocr-lite-custom"
num, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
ONLY = set(sys.argv[4:])
os.makedirs(out, exist_ok=True)
raw = json.load(open(os.path.join(BASE, "work", "output", "01_raw_ocr", f"国際寫眞新聞_{num}号.json"), encoding="utf-8"))["contents"]
frames = {}
for r in csv.DictReader(open(os.path.join(BASE, "work", "proofread", f"{num}号_校正の入力.csv"), encoding="utf-8-sig", newline="")):
    frames[(int(r["頁"]), str(r["枠"]))] = tuple(int(r[k]) for k in ("x1", "y1", "x2", "y2"))

def box(b):
    xs, ys = [], []
    for pt in b["boundingBox"]:
        x, y = (map(float, pt.split()) if isinstance(pt, str) else map(float, pt[:2]))
        xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)

def match(q, t):
    sm = difflib.SequenceMatcher(None, q, t, autojunk=False)
    bl = [b for b in sm.get_matching_blocks() if b.size]
    if not bl or not q: return 0, 0, 0
    return sum(b.size for b in bl) / len(q), bl[0].b, bl[-1].b + bl[-1].size

rows = [r for r in csv.DictReader(open(src, encoding="utf-8-sig", newline="")) if not ONLY or r["番号"] in ONLY]
imgs, pieces = {}, []
for r in rows:
    pg, fr = int(r["頁"]), str(r["枠"])
    fx1, fy1, fx2, fy2 = frames[(pg, fr)]
    q1, q2 = r["入力値"], r["正しくは（Antigravity）"]
    cands = []
    for b in raw[pg - 1]:
        if "boundingBox" not in b or not str(b.get("text", "")): continue
        x1, y1, x2, y2 = box(b)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        if not (fx1 - 30 <= cx <= fx2 + 30 and fy1 - 30 <= cy <= fy2 + 30): continue
        t = str(b["text"])
        best = max(match(q1, t), match(q2, t))
        cands.append((best, (x1, y1, x2, y2), t))
    cands.sort(key=lambda c: -c[0][0])
    if pg not in imgs:
        imgs[pg] = Image.open(os.path.join(BASE, "work", "cache_images", f"{num}号", f"国際寫眞新聞_{num}号_p{pg:04d}.png")).convert("RGB")
    for k, ((sc, s, e), (x1, y1, x2, y2), t) in enumerate(cands[:2]):
        L = max(1, len(t)); vertical = (y2 - y1) >= (x2 - x1)
        a, z = max(0, s - 6) / L, min(L, e + 6) / L
        if vertical:
            c = imgs[pg].crop((int(x1) - 12, int(y1 + a * (y2 - y1)) - 10, int(x2) + 12, int(y1 + z * (y2 - y1)) + 10))
            f = min(110 / max(1, c.size[0]), 900 / max(1, c.size[1]), 4.0)
        else:
            c = imgs[pg].crop((int(x1 + a * (x2 - x1)) - 10, int(y1) - 12, int(x1 + z * (x2 - x1)) + 10, int(y2) + 12))
            f = min(110 / max(1, c.size[1]), 900 / max(1, c.size[0]), 4.0)
        c = c.resize((max(1, int(c.size[0] * f)), max(1, int(c.size[1] * f))), Image.LANCZOS)
        pieces.append((f"#{r['番号']}{'ab'[k]}", c))
for i in range(0, len(pieces), 12):
    g = pieces[i:i + 12]
    H = max(c.size[1] for _, c in g); W = sum(c.size[0] + 26 for _, c in g) + 10
    canvas = Image.new("RGB", (W, H + 34), "white"); d = ImageDraw.Draw(canvas); x = 10
    for lab, c in g:
        d.text((x, 4), lab, fill="red"); canvas.paste(c, (x, 30)); x += c.size[0] + 26
    canvas.save(os.path.join(out, f"crops_{i // 12 + 1}.png"))
print("images:", (len(pieces) + 11) // 12, "／切り出し", len(pieces), "／件数", len(rows))
