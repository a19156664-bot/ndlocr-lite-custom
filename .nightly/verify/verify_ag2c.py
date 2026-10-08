import os, sys, json
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image, ImageDraw
BASE = r"C:\Users\user\ndlocr-lite-custom"
S = r"C:\Users\user\AppData\Local\Temp\claude\c--Users-user-moto-booklm\c408740a-f2b3-49a8-b9f9-b392b9fd899a\scratchpad"
raw = json.load(open(os.path.join(BASE, "work", "output", "01_raw_ocr", "国際寫眞新聞_141号.json"), encoding="utf-8"))["contents"]
def box(b):
    xs, ys = [], []
    for pt in b["boundingBox"]:
        if isinstance(pt, str): x, y = map(float, pt.split())
        else: x, y = map(float, pt[:2])
        xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)
pieces = []
for lab, pg, key, mode in [("#7", 16, "べく出來上つたの", "next_top"), ("#16", 20, "結局バ", "end")]:
    img = Image.open(os.path.join(BASE, "work", "cache_images", "141号", f"国際寫眞新聞_141号_p{pg:04d}.png")).convert("RGB")
    b = [b for b in raw[pg - 1] if "boundingBox" in b and key in str(b.get("text", ""))][0]
    x1, y1, x2, y2 = box(b); w, h = x2 - x1, y2 - y1
    if mode == "next_top":
        c = img.crop((int(x1 - 1.4 * w), int(y1) - 10, int(x2) + 4, int(y1 + 0.3 * h)))
    else:
        c = img.crop((int(x1) - 14, int(y1 + 0.6 * h), int(x2) + 14, int(y2) + 40))
    pieces.append((lab, c.resize((c.size[0] * 2, c.size[1] * 2))))
W = sum(c.size[0] + 30 for _, c in pieces) + 10; H = max(c.size[1] for _, c in pieces) + 40
canvas = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(canvas); x = 10
for lab, c in pieces:
    d.text((x, 5), lab, fill="red"); canvas.paste(c, (x, 35)); x += c.size[0] + 30
canvas.save(os.path.join(S, "ag2c.png")); print(canvas.size)