# -*- coding: utf-8 -*-
"""Antigravity の校正（指摘のみ）に渡す「納品に入る文字の一覧」を作る（10-08・承認者 案A）。
Excel を作る手順（make141_all.py）と同じ組み立てで、頁・枠・位置・文字を 1 行ずつ。
Region 1 と印（mark）の行は除く（Region 1 は納品に入らない。印は【広告】等で校正の対象外）。
書く先: work\\proofread\\<号>_校正の入力.csv（UTF-8 BOM 付き）。引数: 号（既定 141）"""
import os, sys, json, csv, datetime
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"C:\Users\user\ndlocr-lite-custom"
sys.path.insert(0, BASE)
import pypdfium2
import custom_gui.work_state as work_state
from custom_gui.selection import SelectionContainer, SelectionRect
from custom_gui.exporter import build_export_rows_multi

NUM = sys.argv[1] if len(sys.argv) > 1 else "141"
ISSUE = f"国際寫眞新聞_{NUM}号"
PDF = os.path.join(BASE, "work", f"{ISSUE}.pdf")
RAW = os.path.join(BASE, "work", "output", "01_raw_ocr", f"{ISSUE}.json")
OUTDIR = os.path.join(BASE, "work", "proofread")
OUT = os.path.join(OUTDIR, f"{NUM}号_校正の入力.csv")

def normalize(page_lines, name):
    res = []
    for b in page_lines:
        if "boundingBox" not in b or "text" not in b:
            continue
        xs, ys = [], []
        for pt in b["boundingBox"]:
            if isinstance(pt, str):
                x, y = map(float, pt.split()); xs.append(x); ys.append(y)
            elif isinstance(pt, (list, tuple)):
                xs.append(float(pt[0])); ys.append(float(pt[1]))
        if not xs:
            continue
        x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
        if x1 >= x2: x2 = x1 + 1
        if y1 >= y2: y2 = y1 + 1
        v = b.get("isVertical", False)
        res.append({"text": str(b.get("text", "")), "bbox": (x1, y1, x2, y2),
                    "confidence": float(b.get("confidence", 0.0)),
                    "is_vertical": v.lower() == "true" if isinstance(v, str) else bool(v),
                    "source_image": name})
    return res

doc = pypdfium2.PdfDocument(PDF); n = len(doc); doc.close()
contents = json.load(open(RAW, encoding="utf-8")).get("contents", [])
out_rows, edited, unedited = [], 0, 0
for i in range(n):
    name = f"{ISSUE}_p{i+1:04d}.png"
    parsed = normalize(contents[i], name) if i < len(contents) else []
    st = work_state.load_work_state(PDF, page_index=i)
    c = SelectionContainer(); edits = {}
    if st:
        c.restore([SelectionRect(rect_id=r["rect_id"], bbox=tuple(r["bbox"]), label=r["label"]) for r in st["rects"]])
        edits = st["edits"]
    rects = c.get_all()
    if not rects:
        continue
    for r in build_export_rows_multi([{"image_name": name, "rects": rects, "ocr_results": parsed, "edited_texts": edits}]):
        if str(r["region_id"]) == "1" or not str(r["text"]).strip():
            continue
        is_edit = str(r["region_id"]) in edits
        edited += is_edit; unedited += (not is_edit)
        out_rows.append([i + 1, r["region_id"], round(r["x1"]), round(r["y1"]), round(r["x2"]), round(r["y2"]),
                         "人が直した" if is_edit else "全体OCRのまま", r["text"]])
os.makedirs(OUTDIR, exist_ok=True)
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["頁", "枠", "x1", "y1", "x2", "y2", "出どころ", "文字"])
    w.writerows(out_rows)
print(f"{datetime.datetime.now():%m-%d %H:%M} {OUT}")
print(f"rows={len(out_rows)} pages={len({r[0] for r in out_rows})}/{n} 人が直した={edited} 全体OCRのまま={unedited}")
