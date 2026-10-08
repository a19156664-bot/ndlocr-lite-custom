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
for lab, pg, keys in [("12", 34, ["明朗", "正明", "肅正", "粛正"]), ("14", 36, ["九官", "官鳥", "童話"])]:
    img = Image.open(os.path.join(BASE, "work", "cache_images", "141号", f"国際寫眞新聞_141号_p{pg:04d}.png")).convert("RGB")
    hits = [b for b in raw[pg - 1] if "boundingBox" in b and any(k in str(b.get("text", "")) for k in keys)]
    print(lab, pg, [str(b.get("text"))[:40] for b in hits])
    for b in hits[:2]:
        x1, y1, x2, y2 = box(b)
        c = img.crop((int(x1) - 14, int(y1) - 14, int(x2) + 14, int(y2) + 14))
        if c.size[0] > c.size[1]: c = c.rotate(-90, expand=True)
        pieces.append((lab, c))
H = 800
sc = [(l, c.resize((max(1, int(c.size[0] * H / c.size[1])), H))) for l, c in pieces]
W = sum(c.size[0] + 30 for _, c in sc) + 10
cv = Image.new("RGB", (W, H + 40), "white"); d = ImageDraw.Draw(cv); x = 10
for l, c in sc:
    d.text((x, 5), "#" + l, fill="red"); cv.paste(c, (x, 35)); x += c.size[0] + 30
cv.save(os.path.join(S, "ag3c.png")); print(cv.size)