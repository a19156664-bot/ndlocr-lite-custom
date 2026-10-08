# -*- coding: utf-8 -*-
"""枠を縦で読むの規則で列に切り、各列を読んで、目当ての語に近い列だけを大きく切り出す（読むだけ）。
引数なし。対象は下の TARGETS。"""
import os, sys, json, difflib
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"C:\Users\user\ndlocr-lite-custom"
sys.path.insert(0, BASE)
import numpy as np
from PIL import Image, ImageDraw
from custom_gui import vertical_ocr as vo, mark_detector
from custom_gui.region_ocr import crop_region
S = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(BASE, "work", ".ndlocr_cache", "国際寫眞新聞_141号_p{:04d}.work.json")
IMG = os.path.join(BASE, "work", "cache_images", "141号", "国際寫眞新聞_141号_p{:04d}.png")
TARGETS = [
    ("#4", 40, "2", ["半日を過して", "過してホテル"]),
    ("#5", 40, "5", ["近衞歩兵第一", "歩公第一"]),
    ("#8", 40, "5", ["勇壯な分列", "分列行進", "訓辭の後"]),
    ("#21", 43, "3", ["府市の肅正係り", "肅正係りでは"]),
    ("#22", 43, "3", ["模範選擧は東京", "範選擧は"]),
    ("#23", 43, "3", ["樂隊を附し", "毎に樂隊"]),
    ("#24", 43, "3", ["選擧肅正の大旗"]),
    ("#25", 43, "3", ["婦人聯合會でも", "肅正婦人"]),
    ("#26", 43, "6", ["係りでは最後", "肅正係りで"]),
    ("#27", 44, "3", ["ミス・メリー", "クリスマスと云ふ", "と云ふ"]),
    ("#29", 45, "3", ["間諜」に出演", "扱つた「間"]),
]
rec = vo.get_recognizer()
cache = {}
def columns(pg, rid):
    if (pg, rid) in cache: return cache[(pg, rid)]
    st = json.load(open(C.format(pg), encoding="utf-8"))
    bbox = tuple([r for r in st["rects"] if r["rect_id"] == rid][0]["bbox"])
    crop = crop_region(mark_detector.load_image(IMG.format(pg)), bbox)
    mask = vo.remove_photo_tiles(vo.ink_mask(crop)); y1, y2 = vo.text_band(mask)
    band, img = mask[y1:y2], crop[y1:y2]
    cols = list(reversed(vo.split_columns(band)))
    out = []
    for a, b in cols:
        ys = np.where(band[:, a:b].sum(axis=1) > 0)[0]
        if len(ys) == 0: continue
        c = img[max(0, ys[0] - 3):ys[-1] + 4, max(0, a - 3):b + 3]
        if c.shape[0] <= c.shape[1]: continue
        out.append((rec.read(c), c))
    cache[(pg, rid)] = out
    return out
def sim(q, t):
    sm = difflib.SequenceMatcher(None, q, t, autojunk=False)
    return sum(x.size for x in sm.get_matching_blocks()) / max(1, len(q))
pieces = []
for lab, pg, rid, keys in TARGETS:
    cols = columns(pg, rid)
    scored = sorted(range(len(cols)), key=lambda i: -max(max(sim(k, cols[i][0]), sim(k, cols[i][0] + (cols[i + 1][0] if i + 1 < len(cols) else ""))) for k in keys))
    best = sorted(scored[:1] + [i + 1 for i in scored[:1] if i + 1 < len(cols)])
    print(lab, pg, rid, "列", len(cols), "選んだ列", best, [cols[i][0][:30] for i in best])
    for i in best:
        pieces.append((f"{lab}-{i}", Image.fromarray(np.ascontiguousarray(cols[i][1][:, :, ::-1]))))
H = 760
for part in range(0, len(pieces), 12):
    grp = pieces[part:part + 12]
    sc = [(l, p.resize((max(1, int(p.size[0] * H / p.size[1])), H))) for l, p in grp]
    W = sum(p.size[0] + 40 for _, p in sc) + 10
    cv = Image.new("RGB", (W, H + 40), "white"); d = ImageDraw.Draw(cv); x = 10
    for l, p in sc:
        d.text((x, 5), l, fill="red"); cv.paste(p, (x, 35)); x += p.size[0] + 40
    cv.save(os.path.join(S, f"cols_find_{part // 12 + 1}.png")); print(cv.size)
