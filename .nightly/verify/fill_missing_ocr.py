# -*- coding: utf-8 -*-
"""一括処理で文字の入らなかった枠（edits に無い枠・Region 1 を除く）にだけ「この枠だけOCR」をかけ直して書き足す（10-10 未明）。

169号で 3 本の一括処理が同じ頁の画像を同時に作り、書きかけの PNG を読んで 12 枠が空のまま保存された。
  - 書く前に、その号の保存を work\\backup\\<時刻>_<号>号_空の枠の読み直し前\\ に写す
  - 既にある edits には触れない。書いた後に読み戻し、ほかの枠が 1 字も変わっていないことを確かめる
  - ビューアが同じ号を開いていたら止める（viewer_guard）

    .venv\\Scripts\\python.exe .nightly\\verify\\fill_missing_ocr.py <号> [--write]
"""
import os, sys, shutil, datetime, time
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"C:\Users\user\ndlocr-lite-custom"
sys.path.insert(0, BASE); sys.path.insert(0, os.path.join(BASE, ".nightly", "verify"))
from custom_gui import work_state, region_ocr
from custom_gui.selection import SelectionRect
from viewer_guard import viewer_issues

num = sys.argv[1]; write = "--write" in sys.argv
pdf = os.path.join(BASE, "work", f"国際寫眞新聞_{num}号.pdf")
png_dir = os.path.join(BASE, "work", "cache_images", f"{num}号")
if write and (num in viewer_issues() or "?" in viewer_issues()):
    print("ビューアがこの号を開いている（または号が分からない）。止めた"); sys.exit(1)
plan = {}
for name in sorted(os.listdir(work_state.work_dir_for(pdf))):
    if not (name.startswith(f"国際寫眞新聞_{num}号_p") and name.endswith(".work.json")):
        continue
    pg = int(name.split("_p")[1][:4])
    st = work_state.load_work_state(pdf, page_index=pg - 1)
    for r in st["rects"][1:]:
        if r["rect_id"] in st["edits"]:
            continue
        png = os.path.join(png_dir, f"国際寫眞新聞_{num}号_p{pg:04d}.png")
        t0 = time.time()
        text = region_ocr.region_ocr_text(png, tuple(r["bbox"]))
        print(f"p{pg} 枠{r['rect_id']}: {time.time()-t0:.0f} 秒 {len(text)} 字 {text[:30]!r}", flush=True)
        if text:
            plan.setdefault(pg, {})[r["rect_id"]] = text
print("書く枠:", sum(len(v) for v in plan.values()))
if not write or not plan:
    print("（書いていない）"); sys.exit(0)
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bdir = os.path.join(BASE, "work", "backup", f"{stamp}_{num}号_空の枠の読み直し前"); os.makedirs(bdir)
src = work_state.work_dir_for(pdf)
for name in os.listdir(src):
    if name.startswith(f"国際寫眞新聞_{num}号_p") and name.endswith(".work.json"):
        shutil.copy2(os.path.join(src, name), bdir)
print("控え:", bdir)
for pg, add in sorted(plan.items()):
    st = work_state.load_work_state(pdf, page_index=pg - 1)
    before = dict(st["edits"]); edits = dict(before); edits.update(add)
    rects = [SelectionRect(rect_id=r["rect_id"], bbox=tuple(r["bbox"]), label=r["label"]) for r in st["rects"]]
    work_state.save_work_state(pdf, rects, edits, st["mark"], page_index=pg - 1)
    back = work_state.load_work_state(pdf, page_index=pg - 1)
    ok = back["edits"] == edits and all(back["edits"][k] == v for k, v in before.items())
    print(f"書いた p{pg}: 読み戻し一致={ok}")
