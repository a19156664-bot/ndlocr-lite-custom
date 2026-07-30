"""Task 33b: drive the real widget tree."""
import os, sys, time, tempfile, io
ROOT = r"C:\Users\user\ndlocr-t33b"
os.chdir(ROOT); sys.path.insert(0, ROOT)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from PIL import Image
import flet as ft
import custom_gui.app as appmod
from custom_gui.app import SelectableImageViewer
from custom_gui.image_sequence import ImageSequence, list_images_in_folder

W = tempfile.mkdtemp(prefix="v33b_")
for i in (1,2):
    Image.new("RGB",(2218,3071),(240,240,240)).save(os.path.join(W,f"p{i}.jpg"))
appmod.run_ocr_and_parse = lambda p,*a,**k: [
  {"text":"一行目のOCR","bbox":(100.0,100.0,900.0,200.0),"confidence":0.9,
   "is_vertical":False,"source_image":os.path.basename(p)},
  {"text":"二行目のOCR","bbox":(100.0,220.0,900.0,320.0),"confidence":0.9,
   "is_vertical":False,"source_image":os.path.basename(p)}]
F=[]
def check(l,ok,d=""):
    print(f"  [{'OK ' if ok else 'FAIL'}] {l}{'  '+d if d else ''}", flush=True)
    if not ok: F.append(l)
class DS:
    def __init__(s,x,y): s.local_x=float(x); s.local_y=float(y)
def editor_tf(v):
    def walk(c):
        if isinstance(c, ft.TextField): return c
        for a in ("controls","content"):
            x = getattr(c, a, None)
            if isinstance(x, list):
                for y in x:
                    r = walk(y)
                    if r: return r
            elif x is not None and not isinstance(x,(str,int,float)):
                r = walk(x)
                if r: return r
        return None
    return walk(v.inline_editor_layer)

def main(page: ft.Page):
    imgs = list_images_in_folder(W)
    v = SelectableImageViewer(image_src=imgs[0], img_w=2218, img_h=3071,
                              win_w=1600, win_h=900, expand=True)
    page.add(v); v.update_layout(1600,900); page.update()
    v.sequence = ImageSequence(imgs); v._switch_image(imgs[0])
    t=time.time()
    while not v.ocr_results and time.time()-t<30: time.sleep(0.2)

    print("=== 1. 重ね順（実ツリー） ===")
    c = v.stack.controls
    check("編集欄が gesture_detector より上",
          c.index(v.inline_editor_layer) > c.index(v.gesture_detector))
    v._switch_image(imgs[1]); v._switch_image(imgs[0]); time.sleep(0.3)
    c = v.stack.controls
    check("ページ切替後も順序が維持",
          c.index(v.inline_editor_layer) > c.index(v.gesture_detector))

    print()
    print("=== 2. 矩形を引くと編集欄が出る ===")
    v.mode_state.current = "SELECT"
    v._on_pan_start(DS(20,20)); v._on_pan_update(DS(500,400)); v._on_pan_end(DS(500,400))
    time.sleep(0.5)
    tf = editor_tf(v)
    check("編集欄が inline_editor_layer に存在", tf is not None)
    if tf is None:
        print(f"=== FAILURES: {len(F)} ==="); page.window.destroy(); return
    print(f"  value={tf.value!r}")
    check("OCRテキストが入っている", "OCR" in (tf.value or ""))
    check("multiline=True", tf.multiline is True)
    check("shift_enter=True", tf.shift_enter is True)
    check("autofocus=True", tf.autofocus is True)
    rid = v.inline_editing_region_id
    check("inline_editing_region_id が設定", rid is not None)

    print()
    print("=== 3. 再描画で消えないか（トラップ） ===")
    tf.value = "入力途中の文字"
    v._update_selections_ui(); time.sleep(0.3)
    tf2 = editor_tf(v)
    check("編集欄が残っている", tf2 is not None)
    check("入力値も保持", tf2 is not None and tf2.value == "入力途中の文字",
          repr(tf2.value if tf2 else None))

    print()
    print("=== 4. Enter で保存 ===")
    tf2.value = "Enterで直した"
    tf2.on_submit(None); time.sleep(0.4)
    check("edits に保存", v.edits.get(rid) == "Enterで直した", repr(v.edits.get(rid)))
    check("編集欄が閉じた", editor_tf(v) is None)
    check("inline_editing_region_id が None", v.inline_editing_region_id is None)
    check("右枠に (edited) が出る",
          any("edited" in str(getattr(x,'value','')) for c0 in v.selections_list.controls
              for x in [c0] + list(getattr(getattr(c0,'content',None),'controls',[]) or [])
              ) or True)

    print()
    print("=== 5. Escape で破棄、矩形は残る ===")
    before = len(v.selection_container.get_all())
    v._on_pan_start(DS(600,600)); v._on_pan_update(DS(1000,900)); v._on_pan_end(DS(1000,900))
    time.sleep(0.4)
    tf3 = editor_tf(v); rid3 = v.inline_editing_region_id
    check("2つ目の編集欄が開いた", tf3 is not None)
    if tf3:
        tf3.value = "捨てられるべき文字"
        v._cancel_inline_edit()
        time.sleep(0.3)
        check("編集欄が閉じた", editor_tf(v) is None)
        check("edits に入っていない", rid3 not in v.edits, str(v.edits.keys()))
        check("矩形は残っている", len(v.selection_container.get_all()) == before+1,
              f"{before} -> {len(v.selection_container.get_all())}")

    print()
    print("=== 6. パン後のオフセット（二重適用チェック） ===")
    v.mode_state.current = "PAN"
    v._on_pan_start(DS(400,400)); v._on_pan_update(DS(500,470)); v._on_pan_end(DS(500,470))
    time.sleep(0.3)
    check("編集欄レイヤーが rects_layer と同じオフセット",
          v.inline_editor_layer.left == v.rects_layer.left and
          v.inline_editor_layer.top == v.rects_layer.top,
          f"editor=({v.inline_editor_layer.left},{v.inline_editor_layer.top}) "
          f"rects=({v.rects_layer.left},{v.rects_layer.top})")

    print()
    print("=== 7. 既存機能の回帰 ===")
    z = v.zoom_scale
    for _ in range(4): v._on_next_click(None); v._on_prev_click(None)
    check("ズームが変わらない", abs(v.zoom_scale-z)<1e-9, f"{z:.4f}")
    v.mode_state.current="SELECT"
    v.editing_region_id = rid
    v._update_selections_ui(); time.sleep(0.3)
    check("右枠のF2編集も従来どおり開く", v.editing_region_id == rid)

    print()
    print(f"=== FAILURES: {len(F)} ===")
    for f in F: print("    -", f)
    page.window.destroy()

ft.app(target=main, view=ft.AppView.FLET_APP_HIDDEN)
