"""Task 30 acceptance: real widgets, real OCR, real batch button."""
import os, sys, time, shutil, tempfile
ROOT = r"C:\Users\user\ndlocr-t30"
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import flet as ft
import custom_gui.app as appmod
from custom_gui.app import SelectableImageViewer, OcrState
from custom_gui.image_sequence import ImageSequence, list_images_in_folder
from custom_gui.ocr_cache import is_cached, cache_dir_for

SRC = [
    "resource/digidepo_2531162_0024.jpg",
    "resource/tategaki2026-04-24-094138.png",
]
WORK = tempfile.mkdtemp(prefix="t30_")
for s in SRC:
    shutil.copy2(s, os.path.join(WORK, os.path.basename(s)))

FAILS = []
def check(label, ok, detail=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {label}{'  ' + detail if detail else ''}", flush=True)
    if not ok:
        FAILS.append(label)

REAL_OCR_CALLS = []
_real = appmod.run_ocr_and_parse
def counting_ocr(path, *a, **k):
    REAL_OCR_CALLS.append(os.path.basename(path))
    return _real(path, *a, **k)
appmod.run_ocr_and_parse = counting_ocr


def main(page: ft.Page):
    imgs = list_images_in_folder(WORK)
    print(f"images: {[os.path.basename(p) for p in imgs]}", flush=True)
    v = SelectableImageViewer(image_src=imgs[0], img_w=2218, img_h=3071,
                              win_w=1600, win_h=900, expand=True)
    page.add(v); v.update_layout(1600, 900); page.update()
    v.sequence = ImageSequence(imgs)
    v._switch_image(imgs[0])

    print("=== 1. the button exists and sits after the PDF button ===", flush=True)
    order = [getattr(c, "tooltip", None) for c in v.controls_row.controls[:5]]
    print(f"  toolbar: {order}", flush=True)
    check("btn_batch_ocr present", hasattr(v, "btn_batch_ocr"))
    check("placed 3rd, right after Open PDF",
          order[2] is not None and "Pre-OCR" in str(order[2]), str(order[2]))

    print()
    print("=== 2. cold start: lazy OCR runs for the page being shown ===", flush=True)
    t = time.time()
    while v.ocr_state not in (OcrState.DONE, OcrState.ERROR) and time.time() - t < 180:
        time.sleep(1)
    print(f"  lazy OCR of page 1 took {time.time()-t:.1f} s, state={v.ocr_state.name}", flush=True)
    check("page 1 OCR'd lazily", v.ocr_state == OcrState.DONE)
    check("[F] lazy OCR wrote a cache file", is_cached(imgs[0]))

    print()
    print("=== 3. THE BUTTON: real batch over both images ===", flush=True)
    REAL_OCR_CALLS.clear()
    t = time.time()
    v.btn_batch_ocr.on_click(None)
    check("batch_running set immediately", v.batch_running is True)
    check("button switched to cancel", v.btn_batch_ocr.icon == ft.Icons.CANCEL,
          str(v.btn_batch_ocr.icon))

    seen_progress = []
    while v.batch_running and time.time() - t < 400:
        if v.batch_progress and v.batch_progress not in seen_progress:
            seen_progress.append(v.batch_progress)
        time.sleep(0.5)
    elapsed = time.time() - t
    print(f"  batch took {elapsed:.1f} s", flush=True)
    print(f"  progress seen: {seen_progress}", flush=True)
    print(f"  status: {v.latest_region_info!r}", flush=True)

    check("batch finished", v.batch_running is False)
    check("button restored", v.btn_batch_ocr.icon == ft.Icons.DOCUMENT_SCANNER)
    check("batch_progress cleared", v.batch_progress is None)
    check("both images cached", is_cached(imgs[0]) and is_cached(imgs[1]))
    check("page 1 was NOT re-OCR'd (already cached)",
          os.path.basename(imgs[0]) not in REAL_OCR_CALLS,
          f"lazy calls during batch: {REAL_OCR_CALLS}")
    check("no lazy OCR ran during the batch", REAL_OCR_CALLS == [],
          str(REAL_OCR_CALLS))

    print()
    print("=== 4. THE POINT: page turns no longer trigger OCR ===", flush=True)
    REAL_OCR_CALLS.clear()
    for i in range(6):
        v._on_next_click(None); v._on_prev_click(None)
    time.sleep(1.0)
    check("12 page turns caused ZERO OCR calls", REAL_OCR_CALLS == [],
          str(REAL_OCR_CALLS))
    t = time.time()
    v._switch_image(imgs[1])
    sw = time.time() - t
    check("switching to a cached page is instant", sw < 1.0, f"{sw:.3f} s")
    check("cached page shows DONE", v.ocr_state == OcrState.DONE)
    check("cached page has real lines", len(v.ocr_results) > 0,
          f"{len(v.ocr_results)} lines")

    print()
    print("=== 5. status string keeps every existing segment ===", flush=True)
    v.batch_progress = (7, 9)
    s = v._get_status_message()
    print(f"  {s}", flush=True)
    for seg in ("File:", "Size:", "Scale:", "Mode:", "Last:", "Pre-OCR: 7/9"):
        check(f"segment present: {seg}", seg in s)
    v.batch_progress = None
    check("no Pre-OCR segment when idle", "Pre-OCR" not in v._get_status_message())

    print()
    print("=== 6. second batch is a no-op ===", flush=True)
    t = time.time()
    v.btn_batch_ocr.on_click(None)
    while v.batch_running and time.time() - t < 60:
        time.sleep(0.2)
    warm = time.time() - t
    check("returns quickly, no model load", warm < 10.0, f"{warm:.2f} s")
    print(f"  status: {v.latest_region_info!r}", flush=True)

    print()
    print(f"=== FAILURES: {len(FAILS)} ===", flush=True)
    for f in FAILS:
        print(f"    - {f}", flush=True)
    print(f"cache dir: {cache_dir_for(imgs[0])}", flush=True)
    page.window.destroy()


ft.app(target=main, view=ft.AppView.FLET_APP_HIDDEN)
shutil.rmtree(WORK, ignore_errors=True)
print("=== main() returned ===", flush=True)
