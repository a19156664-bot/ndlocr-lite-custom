# -*- coding: utf-8 -*-
"""31 件の確かめ（2 回目の切り出し）。各指摘について、枠の中で「正しくは」「入力値」に当てはまる行を上位 2 つ選び、
行の中で一致した字の辺り（前後 4 字）だけを大きく切り出す。6 件ずつ並べる。読むだけ・書くのは scratchpad。"""
import os, sys, csv, glob, json, difflib
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image, ImageDraw
BASE = r"C:\Users\user\ndlocr-lite-custom"
S = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, "work", "proofread")
raw = json.load(open(os.path.join(BASE, "work", "output", "01_raw_ocr", "国際寫眞新聞_141号.json"), encoding="utf-8"))["contents"]
frames = {}
for r in csv.DictReader(open(os.path.join(D, "141号_校正の入力.csv"), encoding="utf-8-sig", newline="")):
    frames[(int(r["頁"]), str(r["枠"]))] = tuple(int(r[k]) for k in ("x1", "y1", "x2", "y2"))
items = []
for p in sorted(glob.glob(os.path.join(D, "141号_p*_校正案.csv"))):
    if int(os.path.basename(p)[6:10]) >= 14 and int(os.path.basename(p)[6:10]) <= 24:
        items += list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))
ONLY = [int(a) for a in sys.argv[1:]] or list(range(1, len(items) + 1))

def box(b):
    xs, ys = [], []
    for pt in b["boundingBox"]:
        if isinstance(pt, str): x, y = map(float, pt.split())
        else: x, y = map(float, pt[:2])
        xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)

def match(q, t):
    sm = difflib.SequenceMatcher(None, q, t, autojunk=False)
    bl = [b for b in sm.get_matching_blocks() if b.size]
    if not bl: return 0, 0, 0
    return sum(b.size for b in bl) / len(q), bl[0].b, bl[-1].b + bl[-1].size

pieces = []
for n, it in enumerate(items, 1):
    if n not in ONLY: continue
    pg = int(it["頁"]); fr = str(it["枠"]).replace("region", "").strip()
    fx1, fy1, fx2, fy2 = frames[(pg, fr)]
    cands = []
    for b in raw[pg - 1]:
        if "boundingBox" not in b: continue
        x1, y1, x2, y2 = box(b)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        if not (fx1 - 30 <= cx <= fx2 + 30 and fy1 - 30 <= cy <= fy2 + 30): continue
        t = str(b.get("text", ""))
        if not t: continue
        best = max(match(it["正しくは"], t), match(it["入力値"], t))
        cands.append((best[0], best[1], best[2], (x1, y1, x2, y2), t))
    cands.sort(key=lambda c: -c[0])
    img = Image.open(os.path.join(BASE, "work", "cache_images", "141号", f"国際寫眞新聞_141号_p{pg:04d}.png")).convert("RGB")
    for k, (sc, s, e, (x1, y1, x2, y2), t) in enumerate(cands[:2]):
        L = max(1, len(t)); vertical = (y2 - y1) >= (x2 - x1)
        a, z = max(0, s - 4) / L, min(L, e + 4) / L
        if vertical:
            c = img.crop((int(x1) - 14, int(y1 + a * (y2 - y1)) - 10, int(x2) + 14, int(y1 + z * (y2 - y1)) + 10))
        else:
            c = img.crop((int(x1 + a * (x2 - x1)) - 10, int(y1) - 14, int(x1 + z * (x2 - x1)) + 10, int(y2) + 14))
            c = c.rotate(-90, expand=True)
        pieces.append((f"#{n}{'ab'[k]}", c, round(sc, 2)))
    print(n, pg, fr, it["入力値"], "→", it["正しくは"], [(round(c[0], 2), c[4][:20]) for c in cands[:2]])

H = 760
for i in range(0, len(pieces), 10):
    group = pieces[i:i + 10]
    scaled = [(lab, c.resize((max(1, int(c.size[0] * H / c.size[1])), H)), sc) for lab, c, sc in group]
    W = sum(c.size[0] + 34 for _, c, _ in scaled) + 10
    canvas = Image.new("RGB", (W, H + 40), "white"); d = ImageDraw.Draw(canvas); x = 10
    for lab, c, sc in scaled:
        d.text((x, 5), lab, fill="red"); canvas.paste(c, (x, 35)); x += c.size[0] + 34
    canvas.save(os.path.join(S, f"ag2b_{i // 10 + 1}.png"))
print("images:", (len(pieces) + 9) // 10)
