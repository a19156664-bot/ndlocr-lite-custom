# -*- coding: utf-8 -*-
"""Diagnosis: why does the per-page save refuse while the all-pages save works?
Reproduces a SECOND session on a folder that already has persisted work state."""
import os, sys, tempfile
sys.path.insert(0, r"C:\Users\user\ndlocr-lite-custom")
from unittest.mock import MagicMock
import flet as ft
from PIL import Image

import custom_gui.app as app
from custom_gui.app import SelectableImageViewer, OcrState
from custom_gui.image_sequence import ImageSequence

OCR_ROWS = [{"bbox": (10, 10, 90, 40), "text": "本文", "confidence": .9,
             "is_vertical": False}]
app.run_ocr_and_parse = MagicMock(return_value=list(OCR_ROWS))
ft.core.control.Control.update = MagicMock()

class DummyPage:
    def __init__(self): self.overlay = []
    def add(self, *c): pass
    def update(self): pass
    def open(self, d): self.overlay.append(d)
    def close(self, d):
        if d in self.overlay: self.overlay.remove(d)
    def run_thread(self, fn, *a): fn(*a)

root = tempfile.mkdtemp(prefix="diag40_")
d = os.path.join(root, "issue"); os.makedirs(d)
paths = []
for n in ("p001.png", "p002.png"):
    p = os.path.join(d, n)
    Image.new("RGB", (200, 200), "white").save(p)
    paths.append(p)

def build(img):
    v = SelectableImageViewer(img, 200, 200, 800, 600)
    v.page = DummyPage()
    v.sequence = ImageSequence(paths)
    return v

def report(v, tag):
    print(f"  --- {tag}")
    print(f"      ocr_state(self)      = {v.ocr_state}")
    print(f"      ocr_state(state)     = {v.image_states[v.image_src]['ocr_state']}")
    print(f"      rects                = {len(v.selection_container.get_all())}")
    print(f"      ocr_results          = {len(v.ocr_results)}")
    print(f"      mark                 = {v.mark}")
    print(f"      latest_region_info   = {getattr(v, 'latest_region_info', None)!r}")
    dlg = getattr(v, "_save_dialog", None)
    print(f"      dialog               = {None if dlg is None else dlg.title.value}")

print("=== SESSION 1: 矩形を引いて OCR を回し、保存する ===")
v = build(paths[0])
v.start_ocr(v.page)
r = v.selection_container.add((5, 5, 95, 95), "Region 1")
v._persist_work_state()
report(v, "session1 保存前")
v._start_export("current")
report(v, "session1 _start_export('current') 後")
csv1 = os.path.join(d, "p001.csv")
print(f"      p001.csv exists      = {os.path.exists(csv1)}")
if v._save_dialog:
    for a in v._save_dialog.actions:
        print(f"        action: {a.text!r} autofocus={a.autofocus}")
    v._save_dialog.actions[0].on_click(None)

print()
print("=== SESSION 2: アプリを閉じて開き直した状態（永続化から復元） ===")
v2 = build(paths[0])
report(v2, "session2 起動直後（start_ocr 前）")
v2._start_export("current")
report(v2, "session2 _start_export('current') 後")
print(f"      p001.csv exists      = {os.path.exists(csv1)}")
if v2._save_dialog:
    for a in v2._save_dialog.actions:
        print(f"        action: {a.text!r} autofocus={a.autofocus}")

print()
print("=== SESSION 2b: start_ocr を回してから保存 ===")
v2._save_dialog = None
v2.start_ocr(v2.page)
report(v2, "start_ocr 後")
v2._start_export("current")
report(v2, "_start_export('current') 後")
if v2._save_dialog:
    for a in v2._save_dialog.actions:
        print(f"        action: {a.text!r} autofocus={a.autofocus}")

print()
print("=== 全ページ保存を同じ状態で ===")
v2._save_dialog = None
v2._start_export("all")
report(v2, "_start_export('all') 後")
allcsv = os.path.join(d, "issue_all.csv")
print(f"      issue_all.csv exists = {os.path.exists(allcsv)}")
