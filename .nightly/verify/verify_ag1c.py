# -*- coding: utf-8 -*-
"""残る 4 件（#6 サウザンプトン・#7 (上)のグヰーン・#13 見出しのヱ・#23 パリ郊外）を、全体OCR の行の文字で探して拡大する。"""
import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image, ImageDraw
BASE = r"C:\Users\user\ndlocr-lite-custom"
S = os.path.dirname(os.path.abspath(__file__))
raw = json.load(open(os.path.join(BASE, "work", "output", "01_raw_ocr", "国際寫眞新聞_141号.json"), encoding="utf-8"))["contents"]
def box(b):
    xs, ys = [], []
    for pt in b["boundingBox"]:
        if isinstance(pt, str): x, y = map(float, pt.split())
        else: x, y = map(float, pt[:2])
        xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)
# (ラベル, 頁, 行の文字に含まれる語, 行の中の位置の割合 [始め, 終わり])
targets = [("#6a", 7, "サウザ", (0.75, 1.0)), ("#6b", 7, "ンから", (0.0, 0.3)), ("#6c", 7, "トンから", (0.0, 0.3)),
           ("#7", 7, "寫眞(上)", (0.0, 0.35)), ("#13", 9, "ツコ大統領の榮冠", (0.0, 0.35)),
           ("#23a", 11, "郊外", (0.0, 1.0)), ("#23b", 11, "搭乘", (0.0, 1.0))]
pieces = []
for lab, pg, key, (fa, fz) in targets:
    img = Image.open(os.path.join(BASE, "work", "cache_images", "141号", f"国際寫眞新聞_141号_p{pg:04d}.png")).convert("RGB")
    hits = [b for b in raw[pg - 1] if "boundingBox" in b and key in str(b.get("text", ""))]
    print(lab, pg, key, "行:", [str(b.get("text"))[:40] for b in hits])
    for b in hits[:1]:
        x1, y1, x2, y2 = box(b)
        if (y2 - y1) >= (x2 - x1):
            c = img.crop((int(x1) - 14, int(y1 + fa * (y2 - y1)) - 10, int(x2) + 14, int(y1 + fz * (y2 - y1)) + 10))
        else:
            c = img.crop((int(x1 + fa * (x2 - x1)) - 10, int(y1) - 14, int(x1 + fz * (x2 - x1)) + 10, int(y2) + 14)).rotate(-90, expand=True)
        pieces.append((lab, c))
H = 760
scaled = [(lab, c.resize((max(1, int(c.size[0] * H / c.size[1])), H))) for lab, c in pieces]
W = sum(c.size[0] + 34 for _, c in scaled) + 10
canvas = Image.new("RGB", (W, H + 40), "white"); d = ImageDraw.Draw(canvas); x = 10
for lab, c in scaled:
    d.text((x, 5), lab, fill="red"); canvas.paste(c, (x, 35)); x += c.size[0] + 34
canvas.save(os.path.join(S, "ag1c.png"))
