# -*- coding: utf-8 -*-
"""Task 39b commander verification - the DoD items verify39.py does not cover."""
import os, sys, json, tempfile
sys.path.insert(0, r"C:\Users\user\ndlocr-work")
from unittest.mock import MagicMock
import flet as ft
from PIL import Image

import custom_gui.app as app
from custom_gui.app import SelectableImageViewer, OcrState
from custom_gui.image_sequence import ImageSequence
from custom_gui import work_state

app.run_ocr_and_parse = MagicMock(return_value=[])
ft.core.control.Control.update = MagicMock()

FAIL = 0
def ck(cond, label, extra=""):
    global FAIL
    print(("  [OK ] " if cond else "  [FAIL] ") + label + ("  " + str(extra) if extra else ""))
    if not cond: FAIL += 1

class DummyPage:
    def __init__(self): self.overlay = []
    def add(self, *c): pass
    def update(self): pass
    def open(self, d): self.overlay.append(d)
    def close(self, d):
        if d in self.overlay: self.overlay.remove(d)
    def run_thread(self, fn, *a): fn(*a)

def fresh(prefix="t39b_"):
    root = tempfile.mkdtemp(prefix=prefix)
    d = os.path.join(root, "issue"); os.makedirs(d)
    ps = []
    for n in ("p001.png", "p002.png"):
        p = os.path.join(d, n)
        Image.new("RGB", (200, 200), "white").save(p)
        ps.append(p)
    return d, ps

def build(img, paths):
    v = SelectableImageViewer(img, 200, 200, 800, 600)
    v.page = DummyPage()
    v.sequence = ImageSequence(paths)
    v.ocr_state = OcrState.DONE
    v.image_states[img]["ocr_state"] = OcrState.DONE
    return v

print("=== 1. 削除の永続化 (DoD[2]) ===")
d, ps = fresh()
v = build(ps[0], ps)
v.selection_container.add((5, 5, 95, 95), "Region 1")
v._persist_work_state()
data = work_state.load_work_state(ps[0])
ck(data is not None and len(data["rects"]) == 1, "追加後は矩形1つ")
rid = v.selection_container.get_all()[0].rect_id
v.selection_container.delete_by_id(rid)
v._persist_work_state()
data = work_state.load_work_state(ps[0])
ck(data is not None and len(data["rects"]) == 0, "削除がファイルに反映された",
   None if data is None else len(data["rects"]))
v2 = build(ps[0], ps)
ck(len(v2.selection_container.get_all()) == 0, "新ビューアでも矩形なし",
   len(v2.selection_container.get_all()))

print("=== 2. 編集の取り消しがファイルに反映される (DoD[2]) ===")
d, ps = fresh()
v = build(ps[0], ps)
r = v.selection_container.add((5, 5, 95, 95), "Region 1")
v.commit_edit(r.rect_id, "なおした")
ck(work_state.load_work_state(ps[0])["edits"].get(r.rect_id) == "なおした",
   "編集がファイルにある")
del v.edits[r.rect_id]
v._persist_work_state()
ck(r.rect_id not in work_state.load_work_state(ps[0])["edits"],
   "取り消しがファイルに反映された",
   work_state.load_work_state(ps[0])["edits"])

print("=== 3. 復元後に新規矩形を引いても既存が壊れない (DoD[4]) ===")
d, ps = fresh()
v = build(ps[0], ps)
a = v.selection_container.add((5, 5, 45, 45), "Region 1")
b = v.selection_container.add((50, 50, 95, 95), "Region 2")
v.commit_edit(a.rect_id, "AAA")
v.commit_edit(b.rect_id, "BBB")
v3 = build(ps[0], ps)
ck(len(v3.selection_container.get_all()) == 2, "2つ復元された")
new = v3.selection_container.add((100, 100, 150, 150))
ck(new.rect_id not in (a.rect_id, b.rect_id), "新IDが既存と衝突しない", new.rect_id)
v3.commit_edit(new.rect_id, "CCC")
ck(v3.edits[a.rect_id] == "AAA", "復元した矩形1の文字が無傷", v3.edits.get(a.rect_id))
ck(v3.edits[b.rect_id] == "BBB", "復元した矩形2の文字が無傷", v3.edits.get(b.rect_id))

print("=== 4. 画像が差し替わったら復元しない (DoD[5]) ===")
d, ps = fresh()
v = build(ps[0], ps)
v.selection_container.add((5, 5, 95, 95), "Region 1")
v._persist_work_state()
Image.new("RGB", (400, 400), "black").save(ps[0])   # size changes
v4 = build(ps[0], ps)
ck(len(v4.selection_container.get_all()) == 0, "矩形は復元されない",
   len(v4.selection_container.get_all()))

print("=== 5. 壊れた .work.json を無視する (DoD[6]) ===")
d, ps = fresh()
v = build(ps[0], ps)
v.selection_container.add((5, 5, 95, 95), "Region 1")
v._persist_work_state()
with open(work_state.work_path_for(ps[0]), "wb") as f:
    f.write(b"\x00\xff\xfe not json")
try:
    v5 = build(ps[0], ps)
    ck(len(v5.selection_container.get_all()) == 0, "矩形なしで正常に起動した")
except Exception as e:
    ck(False, "例外が出た", repr(e))

print("=== 6. PDFページは PDF の隣に保存される (DoD[7]) ===")
d, ps = fresh()
pdf_path = os.path.join(d, "book.pdf")
open(pdf_path, "wb").write(b"%PDF-1.4 dummy")
v = build(ps[0], ps)
v.pdf_page_map[ps[0]] = (pdf_path, 3)
v.selection_container.add((5, 5, 95, 95), "Region 1")
v._persist_work_state()
want = work_state.work_path_for(pdf_path, 3)
notwant = work_state.work_path_for(ps[0])
ck(os.path.exists(want), "PDF基準のパスに書かれた", os.path.basename(want))
ck(want.endswith("book_p0004.work.json"), "ページ番号が1始まり4桁", os.path.basename(want))

print("=== 7. NameError は握り潰されない (DoD[9]) ===")
d, ps = fresh()
v = build(ps[0], ps)
orig = work_state.save_work_state
work_state.save_work_state = MagicMock(side_effect=NameError("boom"))
try:
    v._persist_work_state()
    ck(False, "NameError が伝播した")
except NameError:
    ck(True, "NameError が伝播した")
work_state.save_work_state = MagicMock(side_effect=OSError("disk full"))
try:
    v._persist_work_state()
    ck(True, "OSError は握り潰される")
except OSError:
    ck(False, "OSError は握り潰される")
work_state.save_work_state = orig

print("=== 8. 復元がファイルを書き戻さない (DoD[E]) ===")
d, ps = fresh()
v = build(ps[0], ps)
v.selection_container.add((5, 5, 95, 95), "Region 1")
v._persist_work_state()
wp = work_state.work_path_for(ps[0])
before = os.stat(wp).st_mtime_ns
raw_before = open(wp, "rb").read()
v6 = build(ps[0], ps)
v6._switch_image(ps[1])
v6._switch_image(ps[0])
raw_after = open(wp, "rb").read()
ck(raw_before == raw_after, "ページを往復しても中身が変わらない")

print()
print("=== FAILURES: %d ===" % FAIL)
