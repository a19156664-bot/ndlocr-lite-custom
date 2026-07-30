"""Task 32: drive the real widget tree - is Enter really wired up?"""
import os, sys, time, tempfile
ROOT = r"C:\Users\user\ndlocr-t32"
os.chdir(ROOT); sys.path.insert(0, ROOT)
from PIL import Image
import flet as ft
import custom_gui.app as appmod
from custom_gui.app import SelectableImageViewer
from custom_gui.image_sequence import ImageSequence, list_images_in_folder

W = tempfile.mkdtemp(prefix="v32_")
Image.new("RGB", (2218, 3071), (240,240,240)).save(os.path.join(W, "a.jpg"))
appmod.run_ocr_and_parse = lambda p, *a, **k: [
    {"text":"元のOCR文字","bbox":(100.0,100.0,900.0,300.0),"confidence":0.9,
     "is_vertical":False,"source_image":"a.jpg"}]
F=[]
def check(l, ok, d=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {l}{'  '+d if d else ''}", flush=True)
    if not ok: F.append(l)
class DS:
    def __init__(s,x,y): s.local_x=float(x); s.local_y=float(y)

def find_tf(v):
    for c in v.selections_list.controls:
        for sub in getattr(getattr(c, "content", None), "controls", []) or []:
            for x in getattr(sub, "controls", []) or []:
                if isinstance(x, ft.TextField): return x
            if isinstance(sub, ft.Column):
                for x in sub.controls:
                    if isinstance(x, ft.TextField): return x
    return None

def main(page: ft.Page):
    imgs = list_images_in_folder(W)
    v = SelectableImageViewer(image_src=imgs[0], img_w=2218, img_h=3071,
                              win_w=1600, win_h=900, expand=True)
    page.add(v); v.update_layout(1600,900); page.update()
    v.sequence = ImageSequence(imgs); v._switch_image(imgs[0])
    t=time.time()
    while not v.ocr_results and time.time()-t < 30: time.sleep(0.2)

    v.mode_state.current = "SELECT"
    v._on_pan_start(DS(20,20)); v._on_pan_update(DS(400,300)); v._on_pan_end(DS(400,300))
    time.sleep(0.4)
    rects = v.selection_container.get_all()
    check("矩形が1つ作られた", len(rects)==1, f"{len(rects)}個")
    rid = rects[0].rect_id

    v.active_region_id = rid; v.editing_region_id = rid
    v._update_selections_ui(); time.sleep(0.4)
    tf = find_tf(v)
    check("編集欄が実ツリーに存在する", tf is not None)
    if tf is None:
        print(f"=== FAILURES: {len(F)} ==="); page.window.destroy(); return

    print(f"  value={tf.value!r}", flush=True)
    check("multiline=True（改行できる）", tf.multiline is True)
    check("shift_enter=True（Enterで送信）", tf.shift_enter is True)
    check("on_submit が設定されている", tf.on_submit is not None)

    print()
    print("=== Enter を模擬（on_submit を発火） ===", flush=True)
    tf.value = "Enterで直した文字"
    tf.on_submit(None)
    time.sleep(0.3)
    check("edits に保存された", v.edits.get(rid) == "Enterで直した文字", repr(v.edits.get(rid)))
    check("編集状態が閉じた", v.editing_region_id is None)
    check("編集欄が消えた", find_tf(v) is None)

    print()
    print("=== ボタン経由と結果が同一か ===", flush=True)
    v.edits.clear(); v.editing_region_id = rid
    v._update_selections_ui(); time.sleep(0.3)
    tf2 = find_tf(v)
    tf2.value = "Enterで直した文字"
    # find the save button in the same item
    saved = None
    for c in v.selections_list.controls:
        for sub in getattr(getattr(c,"content",None), "controls", []) or []:
            for x in getattr(sub,"controls",[]) or []:
                if isinstance(x, ft.Row):
                    for b in x.controls:
                        if getattr(b,"tooltip","")== "Save (Enter)": saved=b
    check("保存ボタンのツールチップが Save (Enter)", saved is not None)
    if saved: saved.on_click(None); time.sleep(0.3)
    check("ボタンでも同じ結果", v.edits.get(rid) == "Enterで直した文字", repr(v.edits.get(rid)))

    print()
    print(f"=== FAILURES: {len(F)} ===", flush=True)
    for f in F: print("    -", f, flush=True)
    page.window.destroy()

ft.app(target=main, view=ft.AppView.FLET_APP_HIDDEN)
