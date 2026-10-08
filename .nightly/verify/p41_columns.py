# -*- coding: utf-8 -*-
"""p41 の西郷さんの記事（元の Region 8 の位置）を、縦で読むと同じ規則で列に切り、右の列から 2 枚に並べる（読むだけ）。"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"C:\Users\user\ndlocr-lite-custom"
sys.path.insert(0, BASE)
import numpy as np
from PIL import Image, ImageDraw
from custom_gui import vertical_ocr as vo, mark_detector
from custom_gui.region_ocr import crop_region
S = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(BASE, "work", "cache_images", "141号", "国際寫眞新聞_141号_p0041.png")
crop = crop_region(mark_detector.load_image(IMG), (27.90048910265347, 2568.0711309385506, 1140.1999879951052, 3062.8398043589386))
mask = vo.remove_photo_tiles(vo.ink_mask(crop)); y1, y2 = vo.text_band(mask)
band, img = mask[y1:y2], crop[y1:y2]
cols = list(reversed(vo.split_columns(band)))
print("列:", len(cols))
pieces = []
for k, (a, b) in enumerate(cols, 1):
    c = img[:, max(0, a - 3):b + 3][:, :, ::-1]
    pieces.append((k, Image.fromarray(np.ascontiguousarray(c))))
H = 760
for part, group in enumerate((pieces[:16], pieces[16:]), 1):
    sc = [(k, p.resize((max(1, int(p.size[0] * H / p.size[1])), H))) for k, p in group]
    W = sum(p.size[0] + 22 for _, p in sc) + 10
    cv = Image.new("RGB", (W, H + 40), "white"); d = ImageDraw.Draw(cv); x = 10
    for k, p in sc:
        d.text((x, 5), str(k), fill="red"); cv.paste(p, (x, 35)); x += p.size[0] + 22
    cv.save(os.path.join(S, f"p41_cols_{part}.png")); print(cv.size)
