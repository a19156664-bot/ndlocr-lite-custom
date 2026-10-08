# -*- coding: utf-8 -*-
"""「この枠だけOCR で行の大半が横向きなら、縦で読み直す」決め方が効くかを測る（10-08）。
measure_v_vs_h.py と同じ 24 枠に、崩れの分かっている p41 旧 R8・p42 R2 を足し、region_ocr と同じ切り出しで
NDLOCR の行の向き（is_vertical）を数える。字数で重みを付けた横向きの割合を出す。読むだけ。"""
import os, sys, csv, json, glob, tempfile, shutil, datetime
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"C:\Users\user\ndlocr-lite-custom"
os.chdir(BASE); sys.path.insert(0, BASE)
import cv2
from custom_gui import mark_detector, ocr_bridge
from custom_gui.region_ocr import crop_region
IMG = os.path.join(BASE, "work", "cache_images", "141号", "国際寫眞新聞_141号_p{:04d}.png")
prev = list(csv.DictReader(open(os.path.join(BASE, "work", "proofread", "141号_縦と横の比べ.csv"), encoding="utf-8-sig", newline="")))
frames = []
for r in prev:
    st = json.load(open(os.path.join(BASE, "work", ".ndlocr_cache", f"国際寫眞新聞_141号_p{int(r['頁']):04d}.work.json"), encoding="utf-8"))
    b = [x for x in st["rects"] if x["rect_id"] == r["枠"]][0]["bbox"]
    frames.append((int(r["頁"]), r["枠"], tuple(b), float(r["縦で読む"]), float(r["この枠だけOCR"])))
frames.append((41, "旧8", (27.90048910265347, 2568.0711309385506, 1140.1999879951052, 3062.8398043589386), None, None))
frames.append((42, "旧2", (1783.0, 0.0, 2213.0, 937.0), None, None))
out = []
for i, (pg, rid, bbox, sv, sh) in enumerate(frames, 1):
    crop = crop_region(mark_detector.load_image(IMG.format(pg)), bbox)
    d = tempfile.mkdtemp(prefix="orient_")
    try:
        p = os.path.join(d, f"p{pg}.png"); cv2.imencode(".png", crop)[1].tofile(p)
        lines = ocr_bridge.run_ocr_and_parse(p)
    finally:
        shutil.rmtree(d)
    hv = sum(len(l["text"]) for l in lines if not l["is_vertical"]); vv = sum(len(l["text"]) for l in lines if l["is_vertical"])
    share = hv / max(1, hv + vv)
    out.append([pg, rid, len(lines), hv, vv, round(share, 3), sv, sh])
    print(f"{datetime.datetime.now():%H:%M} [{i}/{len(frames)}] p{pg} R{rid} 行{len(lines)} 横の字{hv} 縦の字{vv} 横の割合{share:.2f} 縦{sv} 横{sh}", flush=True)
with open(os.path.join(BASE, "work", "proofread", "141号_行の向き.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f); w.writerow(["頁", "枠", "行", "横の字", "縦の字", "横の割合", "縦で読む", "この枠だけOCR"]); w.writerows(out)
for th in (0.5, 0.6, 0.7):
    sel = [r for r in out if r[6] is not None]
    rule = sum((r[6] if r[5] > th else r[7]) for r in sel) / len(sel)
    print(f"END 決め方「横の割合 > {th} なら縦」: 24 枠の平均 {rule:.3f}（横だけ {sum(r[7] for r in sel)/len(sel):.3f}）。縦に回る枠 {sum(1 for r in sel if r[5] > th)}", flush=True)
print("p41・p42 の横の割合:", [(r[0], r[1], r[5]) for r in out if r[6] is None], flush=True)
