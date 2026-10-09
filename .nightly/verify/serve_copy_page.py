# -*- coding: utf-8 -*-
"""画面確認用: 作業用フォルダのコードで、142号 p6 の写しの画像 1 枚だけを開くビューアを立てる。

本物の work には書かない（画像と保存は %TEMP%\\ndlocr_screencheck に写して使う。元の保存状態は読むだけ）。
port 8572・ブラウザは開かない。承認者は http://127.0.0.1:8572 を開く。

    .venv\\Scripts\\python.exe .nightly\\verify\\serve_copy_page.py C:\\Users\\user\\ndlocr-work3

10-09 Task 64（↑↓ボタン）の画面確認のために作った（karte_web STATUS §121）。
"""
import os, sys, json, shutil, tempfile
sys.stdout.reconfigure(encoding="utf-8")
CODE = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\user\ndlocr-work3"
sys.path.insert(0, CODE)
HERE = os.path.join(tempfile.gettempdir(), "ndlocr_screencheck")
os.makedirs(HERE, exist_ok=True)
SRC_PNG = r"C:\Users\user\ndlocr-lite-custom\work\cache_images\142号\国際寫眞新聞_142号_p0006.png"
SRC_STATE = r"C:\Users\user\ndlocr-lite-custom\work\.ndlocr_cache\国際寫眞新聞_142号_p0006.work.json"
IMG = os.path.join(HERE, "page.png")
if not os.path.exists(IMG):
    shutil.copyfile(SRC_PNG, IMG)
st = json.load(open(SRC_STATE, encoding="utf-8"))   # 読むだけ

import flet as ft
from PIL import Image
from custom_gui.app import SelectableImageViewer
from custom_gui.selection import SelectionRect
from custom_gui.web_image import show_web_image


def main(page: ft.Page):
    try:
        _main(page)
        print("main ok", flush=True)
    except Exception:
        import traceback; traceback.print_exc(); sys.stdout.flush()


def _main(page: ft.Page):
    page.padding = 0
    w, h = Image.open(IMG).size
    v = SelectableImageViewer(image_src=IMG, img_w=w, img_h=h, win_w=1400, win_h=900, expand=True)
    v.selection_container.restore([SelectionRect(r["rect_id"], tuple(r["bbox"]), r["label"]) for r in st["rects"]])
    v.edits.clear(); v.edits.update(st["edits"])
    show_web_image(v.image_control, IMG, HERE)
    page.add(v)
    v.update_layout(page.width or 1400, page.height or 900)
    v._update_selections_ui()
    page.update()


print("CODE", CODE, "／写しの置き場", HERE, flush=True)
ft.app(target=main, view=None, port=8572, assets_dir=HERE)
