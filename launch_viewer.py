# -*- coding: utf-8 -*-
"""
全号対応 NDLOCR-Lite 確認・校正ビューア起動ランナー（自動枠生成・即時テキスト表示対応版）
Antigravity Universal Historical Document Viewer
"""

import os
import sys
import json
from pathlib import Path
from PIL import Image

BASE_DIR = r"C:\Users\user\ndlocr-lite-custom"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

import flet as ft
import pypdfium2
from custom_gui.app import SelectableImageViewer, OcrState
from custom_gui.image_sequence import ImageSequence
from custom_gui.pdf_loader import ensure_page_rendered
from custom_gui.web_image import show_web_image

# 引数またはデフォルトから号数を決定
target_num = "141"
if len(sys.argv) > 1:
    arg = sys.argv[1].strip().replace("号", "").replace("第", "")
    if arg in ["141", "142", "143", "144", "145"]:
        target_num = arg

ISSUE_NAME = f"国際寫眞新聞_{target_num}号"
PDF_PATH = os.path.join(BASE_DIR, "work", f"{ISSUE_NAME}.pdf")
RAW_JSON = os.path.join(BASE_DIR, "work", "output", "01_raw_ocr", f"{ISSUE_NAME}.json")
CACHE_DIR = os.path.join(BASE_DIR, "work", "cache_images", f"{target_num}号")
os.makedirs(CACHE_DIR, exist_ok=True)

if not os.path.exists(PDF_PATH):
    print(f"Error: {PDF_PATH} does not exist.")
    sys.exit(1)

print(f"Loading raw OCR data for {ISSUE_NAME}...", flush=True)
with open(RAW_JSON, 'r', encoding='utf-8') as f:
    ocr_raw = json.load(f)

pages_contents = ocr_raw.get("contents", [])
print(f"Loaded {len(pages_contents)} pages of OCR data.", flush=True)

doc = pypdfium2.PdfDocument(PDF_PATH)
page_count = len(doc)
doc.close()

png_paths = []
pdf_page_map = {}
for i in range(page_count):
    p_path = os.path.join(CACHE_DIR, f"{ISSUE_NAME}_p{i+1:04d}.png")
    png_paths.append(p_path)
    pdf_page_map[p_path] = (PDF_PATH, i)

# Pre-render page 1
print(f"Ensuring Page 1 is rendered at 300 DPI for {ISSUE_NAME}...", flush=True)
ensure_page_rendered(png_paths[0], PDF_PATH, 0)

def normalize_page_ocr(page_lines, source_name):
    results = []
    for block in page_lines:
        if "boundingBox" not in block or "text" not in block:
            continue
        raw_bbox = block["boundingBox"]
        xs, ys = [], []
        for pt in raw_bbox:
            if isinstance(pt, str):
                x, y = map(float, pt.split())
                xs.append(x)
                ys.append(y)
            elif isinstance(pt, (list, tuple)):
                xs.append(float(pt[0]))
                ys.append(float(pt[1]))
        if not xs or not ys:
            continue
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)
        if x1 >= x2: x2 = x1 + 1
        if y1 >= y2: y2 = y1 + 1
        
        is_vert_raw = block.get("isVertical", False)
        is_vert = is_vert_raw.lower() == "true" if isinstance(is_vert_raw, str) else bool(is_vert_raw)
        conf = float(block.get("confidence", 0.0))
        results.append({
            "text": str(block.get("text", "")),
            "bbox": (x1, y1, x2, y2),
            "confidence": conf,
            "is_vertical": is_vert,
            "source_image": source_name
        })
    return results

class BrowserImageViewer(SelectableImageViewer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pdf_page_map.update(pdf_page_map)
        self.sequence = ImageSequence(png_paths)
        
        # Pre-populate all OCR results
        for i, png_p in enumerate(png_paths):
            if i < len(pages_contents):
                page_lines = pages_contents[i]
                parsed = normalize_page_ocr(page_lines, os.path.basename(png_p))
                container, edits, mark = self._load_persisted_state(png_p)
                
                # 【自動枠生成】枠がまだない場合、全行を包み込む枠（Region 1）を自動作成して即座に右側にテキストを表示させる！
                if len(container.get_all()) == 0 and parsed:
                    all_xs = [l["bbox"][0] for l in parsed] + [l["bbox"][2] for l in parsed]
                    all_ys = [l["bbox"][1] for l in parsed] + [l["bbox"][3] for l in parsed]
                    if all_xs and all_ys:
                        min_x = max(0.0, min(all_xs) - 15.0)
                        max_x = max(all_xs) + 15.0
                        min_y = max(0.0, min(all_ys) - 15.0)
                        max_y = max(all_ys) + 15.0
                        container.add((min_x, min_y, max_x, max_y))
                
                self.image_states[png_p] = {
                    "selections": container,
                    "ocr_state": OcrState.DONE,
                    "ocr_results": parsed,
                    "ocr_error": None,
                    "edits": edits,
                    "mark": mark
                }

    def _switch_image(self, path: str):
        if path in self.pdf_page_map:
            pdf_p, p_idx = self.pdf_page_map[path]
            ensure_page_rendered(path, pdf_p, p_idx)

        try:
            with Image.open(path) as img:
                self.img_w, self.img_h = img.size
        except Exception:
            self.img_w, self.img_h = 2250, 3075

        super()._switch_image(path)
        
        show_web_image(self.image_control, path, CACHE_DIR)
            
        self.update_layout(self.frame_w, self.frame_h)
        self._update_selections_ui()
        if self.page:
            self.page.update()

def main(page: ft.Page):
    page.title = f"{ISSUE_NAME} — NDLOCR-Lite 確認・校正システム"
    page.window_width = 1400
    page.window_height = 900
    page.padding = 0
    
    p0 = png_paths[0]
    with Image.open(p0) as img:
        w, h = img.size
        
    viewer = BrowserImageViewer(
        image_src=p0,
        img_w=w,
        img_h=h,
        win_w=page.width if page.width else 1400,
        win_h=page.height if page.height else 900,
        expand=True
    )
    
    show_web_image(viewer.image_control, p0, CACHE_DIR)

    def on_resize(e):
        viewer.update_layout(page.width, page.height)
        page.update()

    def on_keyboard(e: ft.KeyboardEvent):
        if e.key == "N" and e.ctrl:
            if viewer.btn_next and not viewer.btn_next.disabled:
                viewer._on_next_click(None)
        elif e.key == "S" and e.ctrl:
            viewer._start_export("current")

    page.on_resized = on_resize
    page.on_keyboard_event = on_keyboard
    page.add(viewer)
    viewer.update_layout(page.width if page.width else 1400, page.height if page.height else 900)
    page.update()

    viewer._switch_image(p0)

if __name__ == "__main__":
    print("=" * 65, flush=True)
    print(f"  {ISSUE_NAME} （全 {len(png_paths)} ページ）確認ビューアを起動しています...", flush=True)
    print(f"  ブラウザ (Edge / Chrome) で自動的に開きます。", flush=True)
    print(f"  URL: http://127.0.0.1:8555")
    print("=" * 65, flush=True)
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8555, assets_dir=CACHE_DIR)
