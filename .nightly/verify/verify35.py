# -*- coding: utf-8 -*-
"""Task 35 commander verification: drive the real widgets, no mocks of the
controls under test. Read-only with respect to the repository."""
import os, sys, tempfile, shutil
sys.path.insert(0, r"C:\Users\user\ndlocr-t35")
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
    if not cond:
        FAIL += 1

class DummyPage:
    def __init__(self):
        self.controls = []; self.overlay = []; self.opened = []
    def add(self, *c): self.controls.extend(c)
    def update(self): pass
    def open(self, d): self.opened.append(d); self.overlay.append(d)
    def close(self, d):
        if d in self.overlay: self.overlay.remove(d)
    def run_thread(self, fn, *a): fn(*a)

def make(dirpath, name="page_0008.png", w=200, h=200):
    p = os.path.join(dirpath, name)
    Image.new("RGB", (w, h), "white").save(p)
    return p

def new_viewer(img):
    v = SelectableImageViewer(img, 200, 200, 800, 600)
    v.page = DummyPage()
    v._switch_image(img)
    v.ocr_state = OcrState.DONE
    v.ocr_results = [
        {"text": "一行目", "bbox": (10, 10, 90, 30), "confidence": .9, "is_vertical": False, "source_image": img},
        {"text": "二行目", "bbox": (10, 40, 90, 60), "confidence": .9, "is_vertical": False, "source_image": img},
        {"text": "三行目", "bbox": (10, 70, 90, 90), "confidence": .9, "is_vertical": False, "source_image": img},
    ]
    return v

def walk(c, out=None):
    out = [] if out is None else out
    out.append(c)
    for attr in ("controls", "actions"):
        for k in (getattr(c, attr, None) or []):
            walk(k, out)
    for attr in ("content", "title"):
        k = getattr(c, attr, None)
        if isinstance(k, ft.Control):
            walk(k, out)
    return out

root = tempfile.mkdtemp(prefix="t35_")

print("=== 1. ツールバー: アイコン2つ / PopupMenu 撤去 ===")
d1 = os.path.join(root, "issue028"); os.makedirs(d1)
img = make(d1)
v = new_viewer(img)
tb = v.controls_row.controls
icons = [c.icon for c in tb if isinstance(c, ft.IconButton)]
ck(ft.Icons.SAVE in icons, "SAVE アイコンがある")
ck(ft.Icons.SAVE_ALT in icons, "SAVE_ALT アイコンがある")
ck(not any(isinstance(c, ft.PopupMenuButton) for c in tb), "PopupMenuButton は無い")
ck(v.save_page_button.tooltip.startswith("このページ"), "tooltip(ページ)", v.save_page_button.tooltip)
ck(v.save_all_button.tooltip.startswith("全ページ"), "tooltip(全ページ)", v.save_all_button.tooltip)

print("=== 2. 保存: ダイアログを開かず画像と同じフォルダへ ===")
v.file_picker.save_file = lambda **kw: (_ for _ in ()).throw(AssertionError("save_file が呼ばれた"))
v.selection_container.add((5, 5, 95, 95), "Region 1")
v._start_export("current")
csv_p = os.path.join(d1, "page_0008.csv"); txt_p = os.path.join(d1, "page_0008.txt")
ck(os.path.exists(csv_p), "CSV が画像と同じフォルダにできた", csv_p)
ck(os.path.exists(txt_p), "TXT が画像と同じフォルダにできた")
body = open(txt_p, encoding="utf-8").read()
ck(body.startswith("page_0008.png\t"), "TXT は 画像名+TAB 形式", repr(body[:40]))
ck(open(csv_p, "rb").read()[:3] == b"\xef\xbb\xbf", "CSV は BOM 付き UTF-8")

print("=== 3. 完了ダイアログは OK ボタン1つだけ ===")
dlg = v._save_dialog
ck(dlg is not None, "ダイアログが保持されている")
ck(dlg.title.value == "保存しました", "タイトル", dlg.title.value)
ck(len(dlg.actions) == 1, "ボタンは1つ", len(dlg.actions))
ck(dlg.actions[0].text == "OK", "ボタンは OK")
ck(csv_p in dlg.content.value and txt_p in dlg.content.value, "保存先フルパスを表示")
ck(v.page.opened and v.page.opened[-1] is dlg, "page.open で開かれた")
dlg.actions[0].on_click(None)
ck(v._save_dialog is None, "OK で閉じる")

print("=== 4. 2回目は上書き確認。キャンセルで一切書かない ===")
shutil.copy2(csv_p, csv_p + ".keep")
with open(csv_p, "w", encoding="utf-8") as f:
    f.write("SENTINEL")
v._start_export("current")
ck(open(csv_p, encoding="utf-8").read() == "SENTINEL", "まだ書き換えられていない")
dlg = v._save_dialog
ck(dlg is not None and dlg.title.value == "上書き確認", "上書き確認ダイアログ")
ck(len(dlg.actions) == 2, "ボタンは2つ", len(dlg.actions))
labels = [a.text for a in dlg.actions]
ck(labels == ["キャンセル", "上書き保存"], "ボタン名", labels)
dlg.actions[0].on_click(None)
ck(open(csv_p, encoding="utf-8").read() == "SENTINEL", "キャンセルで書き換わらない")
ck(v._save_dialog is None, "キャンセルで閉じる")
ck("cancel" in v.latest_region_info.lower(), "ステータスに cancel", v.latest_region_info)

print("=== 5. 上書き保存を押すと実際に書き換わる ===")
v._start_export("current")
v._save_dialog.actions[1].on_click(None)
ck(open(csv_p, encoding="utf-8-sig").read() != "SENTINEL", "上書きされた")
ck(v._save_dialog is not None and v._save_dialog.title.value == "保存しました", "完了ダイアログに遷移")

print("=== 6. 全ページ保存は <フォルダ名>_all ===")
v._save_dialog.actions[0].on_click(None)
img2 = make(d1, "page_0009.png")
from custom_gui.image_sequence import ImageSequence
v.sequence = ImageSequence([img, img2])
v._start_export("all")
if v._save_dialog is not None and v._save_dialog.title.value == "上書き確認":
    v._save_dialog.actions[1].on_click(None)
ck(os.path.exists(os.path.join(d1, "issue028_all.csv")), "issue028_all.csv")
ck(os.path.exists(os.path.join(d1, "issue028_all.txt")), "issue028_all.txt")

print("=== 7. PDFページは元PDFの隣に保存される ===")
src = os.path.join(root, "src"); os.makedirs(src)
open(os.path.join(src, "book.pdf"), "wb").write(b"%PDF-1.4")
tmpd = os.path.join(root, "ndlocr_pdf_fake"); os.makedirs(tmpd)
pimg = make(tmpd, "page_0003.png")
v2 = new_viewer(pimg)
v2.pdf_page_map[pimg] = (os.path.join(src, "book.pdf"), 2)
v2.selection_container.add((5, 5, 95, 95), "Region 1")
v2._start_export("current")
ck(os.path.exists(os.path.join(src, "page_0003.csv")), "元PDFの隣に CSV")
ck(not os.path.exists(os.path.join(tmpd, "page_0003.csv")), "一時フォルダには作らない")

print("=== 8. 右枠の [改行 N] ===")
v3 = new_viewer(make(os.path.join(root, "p3") if os.makedirs(os.path.join(root, "p3")) is None else "", "p.png"))
v3.selection_container.add((0, 0, 100, 100), "Region 1")
v3._update_selections_ui()
heads = [c.value for c in walk(v3.selections_list) if isinstance(c, ft.Text) and c.value and "Region" in c.value]
ck(any("[改行 2]" in h for h in heads), "3行のOCR → [改行 2]", heads)
rid = v3.selection_container.get_all()[0].rect_id
v3.commit_edit(rid, "一行だけ")
heads = [c.value for c in walk(v3.selections_list) if isinstance(c, ft.Text) and c.value and "Region" in c.value]
ck(any("[改行 0]" in h for h in heads), "修正して1行 → [改行 0]", heads)
ck(any("(edited)" in h for h in heads), "(edited) は残っている", heads)
v3.commit_edit(rid, "あ\r\nい\r\nう\r\n")
heads = [c.value for c in walk(v3.selections_list) if isinstance(c, ft.Text) and c.value and "Region" in c.value]
ck(any("[改行 2]" in h for h in heads), "CRLF3行+末尾改行 → [改行 2]", heads)

print("=== 9. フォルダ/PDF を開く経路は生きているか ===")
ck(isinstance(v.file_picker, ft.FilePicker), "file_picker は残っている")
ck(v.file_picker.on_result is not None, "on_result は繋がっている")

print()
print("=== FAILURES: %d ===" % FAIL)
