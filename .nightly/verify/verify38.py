# -*- coding: utf-8 -*-
"""Task 38 commander verification - drives the real widgets."""
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
    def __init__(self): self.overlay = []; self.keyboard = None
    def add(self, *c): pass
    def update(self): pass
    def open(self, d): self.overlay.append(d)
    def close(self, d):
        if d in self.overlay: self.overlay.remove(d)
    def run_thread(self, fn, *a): fn(*a)

class Key:
    def __init__(self, key, ctrl=False, shift=False, alt=False, meta=False):
        self.key = key; self.ctrl = ctrl; self.shift = shift
        self.alt = alt; self.meta = meta

root = tempfile.mkdtemp(prefix="t38_")
d = os.path.join(root, "issue"); os.makedirs(d)
def mk(n):
    p = os.path.join(d, n); Image.new("RGB", (200, 200), "white").save(p); return p
img1, img2 = mk("p001.png"), mk("p002.png")

def build():
    v = SelectableImageViewer(img1, 200, 200, 800, 600)
    v.page = DummyPage()
    v.sequence = ImageSequence([img1, img2])
    v._switch_image(img1)
    v.btn_next.disabled = not v.sequence.has_next()
    return v

def ready(v, img):
    v.ocr_state = OcrState.DONE
    v.image_states[img]["ocr_state"] = OcrState.DONE
    r = [{"bbox": (10, 10, 90, 40), "text": "本文", "confidence": .9,
          "is_vertical": False, "source_image": img}]
    v.ocr_results = r; v.image_states[img]["ocr_results"] = r
    v.selection_container.add((5, 5, 95, 95), "Region 1")

# main() の on_keyboard と同じものを作る
def make_handler(v):
    def on_keyboard(e):
        if v.editing_region_id is not None or v.inline_editing_region_id is not None:
            if e.key == "Escape":
                if v.inline_editing_region_id is not None:
                    v._cancel_inline_edit()
            return
        if e.key == "S" and e.ctrl:
            v._start_export("current")
        elif e.key == "N" and e.ctrl:
            if v.btn_next and not v.btn_next.disabled:
                v._on_next_click(None)
        elif e.key == "F2":
            if v.active_region_id:
                v.editing_region_id = v.active_region_id
                v._update_selections_ui()
    return on_keyboard

print("=== 1. 次ページありのダイアログ ===")
v = build(); ready(v, img1)
v._start_export("current")
dlg = v._save_dialog
ck(dlg is not None, "ダイアログが開いた")
ck(len(dlg.actions) == 2, "ボタンは2つ", [a.text for a in dlg.actions])
ck(dlg.actions[1].text == "次へ", "2つ目は 次へ")
ck(dlg.actions[1].autofocus is True, "次へ に autofocus", dlg.actions[1].autofocus)
ck(dlg.actions[0].text == "ここに残る", "1つ目は ここに残る")
ck(dlg.actions[0].autofocus in (None, False), "ここに残る に autofocus なし")
ck("次のページへ進みますか？" in dlg.content.value, "確認文がある")

print("=== 2. 次へ でページが進む ===")
before = v.image_src
dlg.actions[1].on_click(None)
ck(v._save_dialog is None, "ダイアログが閉じた")
ck(v.image_src == img2, "2ページ目に進んだ", os.path.basename(v.image_src))
ck(before != v.image_src, "移動している")

print("=== 3. ここに残る では進まない ===")
v2 = build(); ready(v2, img1)
v2._start_export("current")
if v2._save_dialog.title.value == "上書き確認":
    v2._save_dialog.actions[1].on_click(None)
v2._save_dialog.actions[0].on_click(None)
ck(v2._save_dialog is None, "閉じた")
ck(v2.image_src == img1, "1ページ目のまま", os.path.basename(v2.image_src))

print("=== 4. 最終ページは OK 1つだけ ===")
v3 = build()
v3._switch_image(img2)
v3.btn_next.disabled = True
ready(v3, img2)
v3._start_export("current")
dlg = v3._save_dialog
if dlg.title.value == "上書き確認":
    dlg.actions[1].on_click(None); dlg = v3._save_dialog
ck(len(dlg.actions) == 1, "ボタンは1つ", [a.text for a in dlg.actions])
ck(dlg.actions[0].text == "OK", "OK である")
ck(dlg.actions[0].autofocus is True, "autofocus あり")
ck("次のページへ進みますか？" not in dlg.content.value, "確認文は出さない")
dlg.actions[0].on_click(None)

print("=== 5. 全ページ保存も OK 1つだけ（次ページがあっても） ===")
v4 = build(); ready(v4, img1)
ck(not v4.btn_next.disabled, "次ページは存在する")
v4._start_export("all")
dlg = v4._save_dialog
if dlg is not None and dlg.title.value == "上書き確認":
    dlg.actions[1].on_click(None); dlg = v4._save_dialog
ck(len(dlg.actions) == 1, "ボタンは1つ", [a.text for a in dlg.actions])
ck(dlg.actions[0].text == "OK", "OK である")
dlg.actions[0].on_click(None)

print("=== 6. 上書き確認には autofocus を付けない ===")
v5 = build(); ready(v5, img1)
v5._start_export("current")   # 既にファイルがある
dlg = v5._save_dialog
ck(dlg.title.value == "上書き確認", "上書き確認が出た", dlg.title.value)
ck(all(a.autofocus in (None, False) for a in dlg.actions),
   "どのボタンにも autofocus なし", [(a.text, a.autofocus) for a in dlg.actions])
dlg.actions[0].on_click(None)

print("=== 7. Ctrl+S で保存される ===")
root2 = tempfile.mkdtemp(prefix="t38b_")
d2 = os.path.join(root2, "iss"); os.makedirs(d2)
p = os.path.join(d2, "x001.png"); Image.new("RGB", (200, 200), "white").save(p)
p2 = os.path.join(d2, "x002.png"); Image.new("RGB", (200, 200), "white").save(p2)
v6 = SelectableImageViewer(p, 200, 200, 800, 600)
v6.page = DummyPage(); v6.sequence = ImageSequence([p, p2]); v6._switch_image(p)
v6.btn_next.disabled = False
ready(v6, p)
h = make_handler(v6)
h(Key("S", ctrl=True))
ck(os.path.exists(os.path.join(d2, "x001.csv")), "CSV ができた")
ck(os.path.exists(os.path.join(d2, "x001.txt")), "TXT ができた")
ck(v6._save_dialog is not None, "完了ダイアログが出た")
v6._save_dialog.actions[0].on_click(None)

print("=== 8. 編集中の Ctrl+S は無効 ===")
os.remove(os.path.join(d2, "x001.csv")); os.remove(os.path.join(d2, "x001.txt"))
v6._save_dialog = None
v6.editing_region_id = v6.selection_container.get_all()[0].rect_id
h(Key("S", ctrl=True))
ck(not os.path.exists(os.path.join(d2, "x001.csv")), "保存されない（右枠編集中）")
ck(v6._save_dialog is None, "ダイアログも出ない")
v6.editing_region_id = None
v6.inline_editing_region_id = v6.selection_container.get_all()[0].rect_id
h(Key("S", ctrl=True))
ck(not os.path.exists(os.path.join(d2, "x001.csv")), "保存されない（インライン編集中）")
v6.inline_editing_region_id = None

print("=== 9. S 単独・Ctrl+N・F2 が壊れていない ===")
h(Key("S"))
ck(not os.path.exists(os.path.join(d2, "x001.csv")), "S 単独では保存しない")
cur = v6.image_src
h(Key("N", ctrl=True))
ck(v6.image_src != cur, "Ctrl+N は従来どおり進む", os.path.basename(v6.image_src))

print()
print("=== FAILURES: %d ===" % FAIL)
