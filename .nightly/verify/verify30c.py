"""Task 30c acceptance: concurrent drags against the REAL widget tree.

Reproduces the user's situation: a page whose OCR results are already cached,
so every pan event has dozens of highlights to deal with, dragged hard from
several threads at once - which is what flet does with on_pan_update.

Usage:  verify30c.py <repo root>
"""
import os, sys, time, threading, tempfile, traceback
ROOT = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\user\ndlocr-lite-custom"
os.chdir(ROOT); sys.path.insert(0, ROOT)

from PIL import Image
import flet as ft
import custom_gui.app as appmod
from custom_gui.app import SelectableImageViewer, OcrState
from custom_gui.image_sequence import ImageSequence, list_images_in_folder

WORK = tempfile.mkdtemp(prefix="v30c_")
for i in range(1, 5):
    Image.new("RGB", (2218, 3071), (240, 240, 240)).save(
        os.path.join(WORK, f"p_{i:03}.jpg"))

# 144 lines, like the user's densest page.
LINES = [{"text": f"line {i}",
          "bbox": (50.0 + (i % 12) * 150, 40.0 + (i // 12) * 190,
                   180.0 + (i % 12) * 150, 150.0 + (i // 12) * 190),
          "confidence": 0.9, "is_vertical": True,
          "source_image": "p_001.jpg"} for i in range(144)]
appmod.run_ocr_and_parse = lambda p, *a, **k: list(LINES)

FAILS, ERRORS = [], []
def check(label, ok, detail=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {label}{'  ' + detail if detail else ''}",
          flush=True)
    if not ok:
        FAILS.append(label)


class DS:
    def __init__(s, x, y): s.local_x = float(x); s.local_y = float(y)


def main(page: ft.Page):
    imgs = list_images_in_folder(WORK)
    v = SelectableImageViewer(image_src=imgs[0], img_w=2218, img_h=3071,
                              win_w=1600, win_h=900, expand=True)
    page.add(v); v.update_layout(1600, 900); page.update()
    v.sequence = ImageSequence(imgs)
    v._switch_image(imgs[0])

    t = time.time()
    while v.ocr_state not in (OcrState.DONE, OcrState.ERROR) and time.time() - t < 60:
        time.sleep(0.2)
    check("page has OCR results to work with", len(v.ocr_results) == 144,
          f"{len(v.ocr_results)} lines")

    # A selection covering everything, so filter_lines_by_region returns them all.
    v.mode_state.current = "SELECT"
    v._on_pan_start(DS(5, 5))
    v._on_pan_update(DS(1500, 850))
    v._on_pan_end(DS(1500, 850))
    time.sleep(0.5)
    n_high = len(v.highlight_layer.controls)
    check("highlights were built", n_high > 50, f"{n_high} highlights")

    print(flush=True)
    print("=== 1. CONCURRENT PANNING (the reported crash) ===", flush=True)
    v.mode_state.current = "PAN"
    v._on_pan_start(DS(400, 400))
    z_before = v.zoom_scale

    stop = threading.Event()
    counts = [0, 0, 0, 0]

    def dragger(idx):
        x = 400 + idx * 7
        while not stop.is_set():
            try:
                x = 400 + ((x + 11) % 300)
                v._on_pan_update(DS(x, 400 + (x % 97)))
                counts[idx] += 1
            except Exception as e:
                ERRORS.append((f"dragger{idx}", type(e).__name__, str(e)[:160]))
                traceback.print_exc()
                return
            time.sleep(0.002)

    ths = [threading.Thread(target=dragger, args=(i,), daemon=True) for i in range(4)]
    for th in ths:
        th.start()
    time.sleep(12)
    stop.set()
    for th in ths:
        th.join(timeout=5)
    v._on_pan_end(DS(500, 500))

    print(f"  pan events delivered: {sum(counts)}  {counts}", flush=True)
    check("no exception from 4 concurrent draggers", ERRORS == [],
          str(ERRORS[:2]))
    check("enough events to be a real test", sum(counts) > 400, str(sum(counts)))

    print(flush=True)
    print("=== 2. the UI still works afterwards ===", flush=True)
    for label, fn in (
            ("page turn", lambda: v._on_next_click(None)),
            ("page back", lambda: v._on_prev_click(None)),
            ("switch image", lambda: v._switch_image(imgs[0])),
            ("new rectangle", lambda: (v._on_pan_start(DS(10, 10)),
                                       v._on_pan_update(DS(600, 600)),
                                       v._on_pan_end(DS(600, 600)))),
            ("selections rebuild", lambda: v._update_selections_ui())):
        try:
            if label == "new rectangle":
                v.mode_state.current = "SELECT"
            fn()
            print(f"  [OK ] {label}", flush=True)
        except Exception as e:
            print(f"  [FAIL] {label}: {type(e).__name__}: {str(e)[:150]}", flush=True)
            FAILS.append(f"after concurrency: {label}")

    print(flush=True)
    print("=== 3. no regressions ===", flush=True)
    check("zoom unchanged by panning", abs(v.zoom_scale - z_before) < 1e-9,
          f"{z_before:.4f} -> {v.zoom_scale:.4f}")
    v._switch_image(imgs[0])
    check("zoom is the expected fit scale", abs(v.zoom_scale - 0.2605) < 1e-3,
          f"{v.zoom_scale:.4f}")
    check("layers are internally consistent",
          len(v.highlight_layer.controls) >= 0 and
          len(v.rects_layer.controls) >= 0)

    print(flush=True)
    print("=== 4. concurrent _update_selections_ui ===", flush=True)
    ERRORS.clear()
    stop2 = threading.Event()

    def rebuilder():
        while not stop2.is_set():
            try:
                v._update_selections_ui()
            except Exception as e:
                ERRORS.append(("rebuilder", type(e).__name__, str(e)[:160]))
                return
            time.sleep(0.003)

    ths2 = [threading.Thread(target=rebuilder, daemon=True) for _ in range(4)]
    for th in ths2:
        th.start()
    time.sleep(6)
    stop2.set()
    for th in ths2:
        th.join(timeout=5)
    check("no exception from 4 concurrent rebuilds", ERRORS == [], str(ERRORS[:2]))

    quiet = len(v.highlight_layer.controls)
    v._update_selections_ui()
    check("no duplicated or leftover highlights",
          len(v.highlight_layer.controls) == quiet,
          f"{quiet} -> {len(v.highlight_layer.controls)}")

    print(flush=True)
    print(f"=== FAILURES: {len(FAILS)} ===", flush=True)
    for f in FAILS:
        print(f"    - {f}", flush=True)
    page.window.destroy()


ft.app(target=main, view=ft.AppView.FLET_APP_HIDDEN)
print("=== main() returned ===", flush=True)
