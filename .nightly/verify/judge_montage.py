# -*- coding: utf-8 -*-
"""指揮官が⑤で画像を見て判定するための切り出しを並べる（読むだけ）。
確認の CSV（番号,頁,枠,入力値,正しくは…）の行ごとに、その枠を切り出して高さ H にそろえ、番号を付けて横に並べる。
使い方: .venv\\Scripts\\python.exe .nightly\\verify\\judge_montage.py <号> <確認の CSV> <書き先フォルダ> [1 枚に並べる数=6] [H=520]"""
import os, sys, csv
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image, ImageDraw
BASE = r"C:\Users\user\ndlocr-lite-custom"
num, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
per = int(sys.argv[4]) if len(sys.argv) > 4 else 6
H = int(sys.argv[5]) if len(sys.argv) > 5 else 520
os.makedirs(out, exist_ok=True)
frames = {}
for r in csv.DictReader(open(os.path.join(BASE, "work", "proofread", f"{num}号_校正の入力.csv"), encoding="utf-8-sig", newline="")):
    frames[(int(r["頁"]), str(r["枠"]))] = tuple(int(r[k]) for k in ("x1", "y1", "x2", "y2"))
rows = list(csv.DictReader(open(src, encoding="utf-8-sig", newline="")))
pieces, imgs = [], {}
for r in rows:
    pg, fr = int(r["頁"]), str(r["枠"])
    if pg not in imgs:
        imgs[pg] = Image.open(os.path.join(BASE, "work", "cache_images", f"{num}号", f"国際寫眞新聞_{num}号_p{pg:04d}.png")).convert("RGB")
    x1, y1, x2, y2 = frames[(pg, fr)]
    c = imgs[pg].crop((max(0, x1 - 8), max(0, y1 - 8), x2 + 8, y2 + 8))
    f = H / c.size[1]
    if c.size[0] * f > 1400: f = 1400 / c.size[0]
    c = c.resize((max(1, int(c.size[0] * f)), max(1, int(c.size[1] * f))), Image.LANCZOS)
    pieces.append((f"#{r['番号']}", c))
for i in range(0, len(pieces), per):
    g = pieces[i:i + per]
    W = sum(c.size[0] + 30 for _, c in g) + 10
    canvas = Image.new("RGB", (W, H + 40), "white"); d = ImageDraw.Draw(canvas); x = 10
    for lab, c in g:
        d.text((x, 5), lab, fill="red"); canvas.paste(c, (x, 35)); x += c.size[0] + 30
    canvas.save(os.path.join(out, f"judge_{i // per + 1}.png"))
print("images:", (len(pieces) + per - 1) // per, "／件数", len(pieces))
