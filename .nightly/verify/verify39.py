# -*- coding: utf-8 -*-
"""Task 39 commander verification - does persistence actually happen?"""
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
    def __init__(self): self.overlay = []
    def add(self, *c): pass
    def update(self): pass
    def open(self, d): self.overlay.append(d)
    def close(self, d):
        if d in self.overlay: self.overlay.remove(d)
    def run_thread(self, fn, *a): fn(*a)

root = tempfile.mkdtemp(prefix="t39_")
d = os.path.join(root, "issue"); os.makedirs(d)
def mk(n):
    p = os.path.join(d, n); Image.new("RGB", (200, 200), "white").save(p); return p
img1, img2 = mk("p001.png"), mk("p002.png")

def build():
    v = SelectableImageViewer(img1, 200, 200, 800, 600)
    v.page = DummyPage()
    v.sequence = ImageSequence([img1, img2])
    v._switch_image(img1)
    return v

cache = os.path.join(d, ".ndlocr_cache")
work = os.path.join(cache, "p001.work.json")

print("=== 1. work_state はそもそも import されているか ===")
ck(hasattr(app, "work_state"), "custom_gui.app.work_state が存在する")

print("=== 2. 矩形を引いたら .work.json が書かれるか (DoD[1]) ===")
v = build()
v.ocr_state = OcrState.DONE
v.image_states[img1]["ocr_state"] = OcrState.DONE
v.selection_container.add((5, 5, 95, 95), "Region 1")
v._persist_work_state()
ck(os.path.exists(work), ".ndlocr_cache/p001.work.json が存在する", work)

print("=== 3. 編集を確定したら書かれるか (DoD[2]) ===")
rid = v.selection_container.get_all()[0].rect_id
v.commit_edit(rid, "なおした文字")
ck(os.path.exists(work), "編集確定後に .work.json が存在する")

print("=== 4. マーク押下で書かれるか (DoD[2]) ===")
v._on_mark_click("【広告】")
ck(os.path.exists(work), "マーク押下後に .work.json が存在する")

print("=== 5. 新しいビューアで復元されるか (DoD[3]) ===")
v2 = build()
rects = v2.selection_container.get_all()
ck(len(rects) == 1, "矩形が1つ復元された", len(rects))
ck(v2.edits.get("1") == "なおした文字", "編集文字が復元された", v2.edits)
ck(v2.mark == "【広告】", "マークが復元された", v2.mark)

print("=== 6. 削除の永続化 (DoD[2]) ===")
print("  (復元されないため検証不能)")

print()
print("=== FAILURES: %d ===" % FAIL)
