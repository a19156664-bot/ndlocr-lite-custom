# -*- coding: utf-8 -*-
"""画面確認用（複数頁）: 作業用フォルダのコードで、142号 p1〜p12 の写しを並べたビューアを立てる（10-10・Task 66 頁へ飛ぶ のため）。

本物の work には書かない（画像と保存は %TEMP%\\ndlocr_screencheck_pages に写して使う。元の保存状態は読むだけ）。
写しの頁番号 n は 142号の p n と同じ。port 8572・ブラウザは開かない。承認者は http://127.0.0.1:8572 を開く。
頁を切り替えるたびに画像を出し直すのは launch_viewer.py の BrowserImageViewer と同じ形。

    .venv\\Scripts\\python.exe .nightly\\verify\\serve_copy_pages.py C:\\Users\\user\\ndlocr-work3
"""
import os, sys, json, shutil, tempfile
sys.stdout.reconfigure(encoding="utf-8")
CODE = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\user\ndlocr-work3"
sys.path.insert(0, CODE)
N = 12
SRC = r"C:\Users\user\ndlocr-lite-custom\work"
HERE = os.path.join(tempfile.gettempdir(), "ndlocr_screencheck_pages")
os.makedirs(os.path.join(HERE, ".ndlocr_cache"), exist_ok=True)
paths = []
for i in range(1, N + 1):
    png = os.path.join(HERE, f"page_{i:02d}.png")
    if not os.path.exists(png):
        shutil.copyfile(os.path.join(SRC, "cache_images", "142号", f"国際寫眞新聞_142号_p{i:04d}.png"), png)
    st_src = os.path.join(SRC, ".ndlocr_cache", f"国際寫眞新聞_142号_p{i:04d}.work.json")
    st_dst = os.path.join(HERE, ".ndlocr_cache", f"page_{i:02d}.work.json")
    if os.path.exists(st_src) and not os.path.exists(st_dst):
        shutil.copyfile(st_src, st_dst)   # 元は読むだけ。写しに書く
    paths.append(png)

import flet as ft
from PIL import Image
from custom_gui.app import SelectableImageViewer
from custom_gui.image_sequence import ImageSequence
from custom_gui.web_image import show_web_image
from custom_gui.page_states import build_page_state


class CopyViewer(SelectableImageViewer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sequence = ImageSequence(paths)
        for p in paths:
            container, edits, mark = self._load_persisted_state(p)
            self.image_states[p] = build_page_state([], container, edits, mark, False)

    def _switch_image(self, path):
        with Image.open(path) as img:
            self.img_w, self.img_h = img.size
        super()._switch_image(path)
        show_web_image(self.image_control, path, HERE)
        self.update_layout(self.frame_w, self.frame_h)
        self._update_selections_ui()
        if self.page:
            self.page.update()


def main(page: ft.Page):
    try:
        page.padding = 0
        w, h = Image.open(paths[0]).size
        v = CopyViewer(image_src=paths[0], img_w=w, img_h=h, win_w=1400, win_h=900, expand=True)
        show_web_image(v.image_control, paths[0], HERE)
        page.add(v)
        v.update_layout(page.width or 1400, page.height or 900)
        page.update()
        v._switch_image(paths[0])
        print("main ok", flush=True)
    except Exception:
        import traceback; traceback.print_exc(); sys.stdout.flush()


print("CODE", CODE, "／写しの置き場", HERE, "／頁", N, flush=True)
ft.app(target=main, view=None, port=8572, assets_dir=HERE)
