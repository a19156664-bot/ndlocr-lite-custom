# -*- coding: utf-8 -*-
"""Task 37 commander verification - drives the real widgets."""
import os, sys, tempfile
sys.path.insert(0, r"C:\Users\user\ndlocr-work")
from unittest.mock import MagicMock
import flet as ft
from PIL import Image

import custom_gui.app as app
from custom_gui.app import SelectableImageViewer, OcrState

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
    def open(self, d): pass
    def close(self, d): pass
    def run_thread(self, fn, *a): fn(*a)

class Ev:
    def __init__(self, x, y, dx=0.0, dy=0.0):
        self.local_x = x; self.local_y = y
        self.delta_x = dx; self.delta_y = dy
        self.control = None

root = tempfile.mkdtemp(prefix="t37_")
img = os.path.join(root, "p.png")
Image.new("RGB", (400, 400), "white").save(img)

v = SelectableImageViewer(img, 400, 400, 800, 600)
v.page = DummyPage()
v._switch_image(img)
gd = v.gesture_detector

print("=== 1. 配線 ===")
ck(gd.on_secondary_tap is not None, "on_secondary_tap が繋がっている")
ck(gd.on_secondary_tap_down is None, "on_secondary_tap_down は未使用")
ck(gd.on_secondary_tap_up is None, "on_secondary_tap_up は未使用")

print("=== 2. 起動直後のカーソル ===")
ck(v.mode_state.current == "SELECT", "初期は SELECT")
ck(gd.mouse_cursor == ft.MouseCursor.PRECISE, "カーソルは PRECISE", gd.mouse_cursor)

print("=== 3. 右クリックでトグル ===")
gd.on_secondary_tap(None)
ck(v.mode_state.current == "PAN", "PAN になった")
ck(v.mode_toggle.selected == {"PAN"}, "ツールバー表示も追従", v.mode_toggle.selected)
ck(gd.mouse_cursor == ft.MouseCursor.GRAB, "カーソルは GRAB", gd.mouse_cursor)
gd.on_secondary_tap(None)
ck(v.mode_state.current == "SELECT", "もう一度で SELECT に戻る")
ck(v.mode_toggle.selected == {"SELECT"}, "ツールバー表示も戻る")
ck(gd.mouse_cursor == ft.MouseCursor.PRECISE, "カーソルは PRECISE に戻る")

print("=== 4. PAN でドラッグ中は GRABBING、離すと GRAB ===")
gd.on_secondary_tap(None)   # PAN へ
ox, oy = v.offset_x, v.offset_y
gd.on_pan_start(Ev(100, 100))
ck(gd.mouse_cursor == ft.MouseCursor.GRABBING, "ドラッグ中は GRABBING", gd.mouse_cursor)
gd.on_pan_update(Ev(140, 130, 40, 30))
ck(gd.mouse_cursor == ft.MouseCursor.GRABBING, "移動中も GRABBING")
moved = (v.offset_x, v.offset_y) != (ox, oy)
ck(moved, "画像が実際に動いた", f"({ox},{oy}) -> ({v.offset_x},{v.offset_y})")
gd.on_pan_end(Ev(140, 130))
ck(gd.mouse_cursor == ft.MouseCursor.GRAB, "離すと GRAB に戻る", gd.mouse_cursor)

print("=== 5. SELECT で矩形を引いてもカーソルは PRECISE のまま ===")
gd.on_secondary_tap(None)   # SELECT へ
n0 = len(v.selection_container.get_all())
gd.on_pan_start(Ev(60, 60))
ck(gd.mouse_cursor == ft.MouseCursor.PRECISE, "描き始めも PRECISE", gd.mouse_cursor)
gd.on_pan_update(Ev(200, 200, 140, 140))
ck(gd.mouse_cursor == ft.MouseCursor.PRECISE, "描いている間も PRECISE")
gd.on_pan_end(Ev(200, 200))
ck(gd.mouse_cursor == ft.MouseCursor.PRECISE, "描き終わりも PRECISE")
n1 = len(v.selection_container.get_all())
ck(n1 == n0 + 1, "矩形が1つ増えた", f"{n0} -> {n1}")

print("=== 6. 右クリックが状態を壊さない ===")
rid = v.selection_container.get_all()[0].rect_id
v.edits[rid] = "編集済みテキスト"
zoom = v.zoom_scale
ofs = (v.offset_x, v.offset_y)
gd.on_secondary_tap(None)
ck(len(v.selection_container.get_all()) == n1, "矩形は消えない")
ck(v.edits.get(rid) == "編集済みテキスト", "編集内容は消えない")
ck(v.zoom_scale == zoom, "ズーム不変", v.zoom_scale)
ck((v.offset_x, v.offset_y) == ofs, "画像も動かない")
gd.on_secondary_tap(None)

print("=== 7. ツールバーのボタンでもカーソルが変わる ===")
class FakeCtl:
    def __init__(self, sel): self.selected = sel
class FakeEv:
    def __init__(self, sel): self.control = FakeCtl(sel)
v._on_mode_change(FakeEv({"PAN"}))
ck(v.mode_state.current == "PAN", "PAN になった")
ck(gd.mouse_cursor == ft.MouseCursor.GRAB, "カーソルも GRAB", gd.mouse_cursor)
v._on_mode_change(FakeEv({"SELECT"}))
ck(gd.mouse_cursor == ft.MouseCursor.PRECISE, "SELECT で PRECISE に戻る")

print("=== 8. ページを移動してもカーソルが壊れない ===")
img2 = os.path.join(root, "q.png")
Image.new("RGB", (400, 400), "white").save(img2)
gd.on_secondary_tap(None)          # PAN
v._switch_image(img2)
ck(v.mode_state.current == "PAN", "モードは維持される", v.mode_state.current)
ck(gd.mouse_cursor == ft.MouseCursor.GRAB, "カーソルも GRAB のまま", gd.mouse_cursor)

print()
print("=== FAILURES: %d ===" % FAIL)
