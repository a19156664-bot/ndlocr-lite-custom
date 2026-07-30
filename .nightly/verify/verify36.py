# -*- coding: utf-8 -*-
"""Task 36 commander verification - drives the real widgets."""
import os, sys, tempfile
sys.path.insert(0, r"C:\Users\user\ndlocr-work")
from unittest.mock import MagicMock
import flet as ft
from PIL import Image

import custom_gui.app as app
from custom_gui.app import SelectableImageViewer, OcrState
from custom_gui.image_sequence import ImageSequence

app.run_ocr_and_parse = MagicMock(return_value=[])
ft.core.control.Control.update = MagicMock()

FAIL = 0
def ck(cond, label, extra=""):
    global FAIL
    print(("  [OK ] " if cond else "  [FAIL] ") + label + ("  " + str(extra) if extra else ""))
    if not cond: FAIL += 1

class DummyPage:
    def __init__(self): self.overlay = []; self.opened = []
    def add(self, *c): pass
    def update(self): pass
    def open(self, d): self.opened.append(d); self.overlay.append(d)
    def close(self, d):
        if d in self.overlay: self.overlay.remove(d)
    def run_thread(self, fn, *a): fn(*a)

def mkimg(d, n):
    p = os.path.join(d, n)
    Image.new("RGB", (200, 200), "white").save(p)
    return p

root = tempfile.mkdtemp(prefix="t36_")
d = os.path.join(root, "issue"); os.makedirs(d)
img1 = mkimg(d, "page1.jpg"); img2 = mkimg(d, "page2.jpg")

v = SelectableImageViewer(img1, 200, 200, 800, 600)
v.page = DummyPage()
v.sequence = ImageSequence([img1, img2])
v._switch_image(img1)

def ocr(v, img):
    v.ocr_state = OcrState.DONE
    v.image_states[img]["ocr_state"] = OcrState.DONE
    r = [{"bbox": (10, 10, 90, 40), "text": "本文テキスト", "confidence": .9,
          "is_vertical": False, "source_image": img}]
    v.ocr_results = r
    v.image_states[img]["ocr_results"] = r

print("=== 1. ボタンの存在 ===")
labels = [c.text for c in v.controls_row.controls if isinstance(c, ft.TextButton)]
ck("広告" in labels, "広告ボタン", labels)
ck("表紙" in labels, "表紙ボタン")

print("=== 2. 押した瞬間にファイルへ追記、ダイアログは出ない ===")
v.btn_mark_ad.on_click(None)
txt1 = os.path.join(d, "page1.txt")
ck(os.path.exists(txt1), "page1.txt ができた")
body = open(txt1, encoding="utf-8").read()
ck(body == "page1.jpg\t【広告】\n", "内容が1行だけ", repr(body))
ck(body.count("\t") == 1, "TABは1つ")
ck(v._save_dialog is None, "ダイアログは開かない")
print("    status:", v.latest_region_info)

print("=== 3. 連打しても二重追記しない ===")
v.btn_mark_ad.on_click(None)
ck(open(txt1, encoding="utf-8").read() == body, "ファイルは不変")
ck("既に" in v.latest_region_info, "既に記録済みと表示", v.latest_region_info)

print("=== 4. 表紙を押すと2行目が増え、印が入れ替わる ===")
v.btn_mark_cover.on_click(None)
lines = open(txt1, encoding="utf-8").read().splitlines()
ck(len(lines) == 2 and lines[1] == "page1.jpg\t【表紙】", "2行目=表紙", lines)
ck(v.mark == "【表紙】", "mark が入れ替わった", v.mark)
v.btn_mark_ad.on_click(None)

print("=== 5. ページを移動して戻っても印が残る ===")
v._switch_image(img2)
ck(v.mark is None, "page2 は印なし", v.mark)
v._switch_image(img1)
ck(v.mark == "【広告】", "page1 に戻すと印が復活", v.mark)

print("=== 6. 印のあるページを保存しても【広告】行が消えない ===")
ocr(v, img1)
v.selection_container.add((5, 5, 95, 95), "Region 1")
v._start_export("current")
if v._save_dialog is not None and v._save_dialog.title.value == "上書き確認":
    print("    -> 上書き確認が出た（広告ボタンが既にファイルを作ったため）")
    v._save_dialog.actions[1].on_click(None)
after = open(txt1, encoding="utf-8").read()
ck("page1.jpg\t【広告】" in after, "【広告】行が残っている", repr(after))
ck("本文テキスト" in after, "OCR本文も入っている")
if v._save_dialog: v._save_dialog.actions[0].on_click(None)

print("=== 7. 枠もOCRも無い印だけのページが全ページ保存に載る ===")
v._switch_image(img2)
v.btn_mark_ad.on_click(None)
v._switch_image(img1)
v._start_export("all")
if v._save_dialog is not None and v._save_dialog.title.value == "上書き確認":
    v._save_dialog.actions[1].on_click(None)
allp = os.path.join(d, "issue_all.txt")
ck(os.path.exists(allp), "issue_all.txt ができた")
txt = open(allp, encoding="utf-8").read()
print("    ---- issue_all.txt ----")
for l in txt.splitlines(): print("      ", repr(l))
ck("page2.jpg\t【広告】" in txt, "枠もOCRも無いページが載っている")
ck("page1.jpg\t【広告】" in txt, "page1 の印も載っている")
ck("skipped" not in v.latest_region_info, "skipped 扱いされない", v.latest_region_info)
if v._save_dialog: v._save_dialog.actions[0].on_click(None)

print("=== 8. PDFページは元PDFの隣に記録される ===")
src = os.path.join(root, "src"); os.makedirs(src)
open(os.path.join(src, "book.pdf"), "wb").write(b"%PDF-1.4")
tmpd = os.path.join(root, "ndlocr_pdf_fake"); os.makedirs(tmpd)
pimg = mkimg(tmpd, "p0003.png")
v2 = SelectableImageViewer(pimg, 200, 200, 800, 600)
v2.page = DummyPage()
v2._switch_image(pimg)
v2.pdf_page_map[pimg] = (os.path.join(src, "book.pdf"), 2)
v2.btn_mark_ad.on_click(None)
ck(os.path.exists(os.path.join(src, "p0003.txt")), "元PDFの隣に記録")
ck(not os.path.exists(os.path.join(tmpd, "p0003.txt")), "一時フォルダには作らない")

print("=== 9. 末尾に改行が無いファイルへの追記 ===")
f9 = os.path.join(d, "nonl.txt")
open(f9, "w", encoding="utf-8").write("既存行\t本文")   # 末尾改行なし
from custom_gui.page_marks import append_mark_line, mark_line
append_mark_line(f9, mark_line("x.jpg", "【広告】"))
got = open(f9, encoding="utf-8").read()
ck(got == "既存行\t本文\nx.jpg\t【広告】\n", "行が繋がらない", repr(got))

print("=== 10. mark キーの無い state を渡したとき ===")
v3 = SelectableImageViewer(img1, 200, 200, 800, 600)
v3.page = DummyPage()
from custom_gui.selection import SelectionContainer
v3.image_states["ghost.png"] = {"selections": SelectionContainer(), "ocr_state": OcrState.IDLE,
                                "ocr_results": [], "ocr_error": None, "edits": {}}
try:
    v3._switch_image("ghost.png")
    ck(True, "KeyError にならない")
except KeyError as e:
    ck(False, "KeyError が発生", e)

print()
print("=== FAILURES: %d ===" % FAIL)
