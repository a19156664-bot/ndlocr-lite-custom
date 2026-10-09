# -*- coding: utf-8 -*-
"""夜間の一括処理（custom_gui/batch_region_ocr.py）の、印を「PDF の注釈」から取る版（10-09 夜・166〜170号）。

166号から、作業者の印は黄緑の塗りではなく、PDF の注釈（赤い四角・多角形・手書きの丸）になった。
batch_region_ocr は画像から黄緑を探すため 0 枠になる。ここでは枠の位置だけを annot_rects.py から取り、
ほかは batch_region_ocr と同じにする:
  - 保存（.ndlocr_cache\\*.work.json）がある頁は飛ばす。印が 0 の頁は書かない
  - Region 1 ＝ 全体OCR の全行を囲む四角＋15px（納品に入らない）。印の枠は Region 2 から
  - 枠の並びは batch_region_ocr（detect_marks）と同じ「上から・同じ高さなら左から」
  - 各枠に「この枠だけOCR」（region_ocr_text）をかけ、edits として保存する
違う所:
  - 全体OCR の json がまだ無い号は、できるまで 1 分ごとに待つ（run_full_ocr.py と並べて走らせる）
  - ビューアの口を見る代わりに、launch_viewer.py が同じ号を開いていないかを見る（別の号を開いていても走る）

    .venv\\Scripts\\python.exe .nightly\\verify\\batch_annot_ocr.py 166 167 168 169 170
"""
import os, sys, json, time, datetime, subprocess
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"C:\Users\user\ndlocr-lite-custom"
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, ".nightly", "verify"))
from custom_gui import work_state, pdf_loader, region_ocr
from custom_gui.selection import SelectionContainer
from annot_rects import page_rects

now = lambda: datetime.datetime.now().strftime("%H:%M:%S")


def viewer_issues():
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ForEach-Object { $_.CommandLine }"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = set()
    for line in r.stdout.splitlines():
        if "launch_viewer.py" in line:
            out.add(line.strip().split()[-1])
    return out


def region1(page_lines):
    xs, ys = [], []
    for block in page_lines:
        if "boundingBox" not in block or "text" not in block:
            continue
        for pt in block["boundingBox"]:
            if isinstance(pt, str):
                x, y = map(float, pt.split())
            else:
                x, y = float(pt[0]), float(pt[1])
            xs.append(x); ys.append(y)
    if not xs:
        return None
    return (max(0.0, min(xs) - 15.0), max(0.0, min(ys) - 15.0), max(xs) + 15.0, max(ys) + 15.0)


def run_issue(issue):
    pdf_path = os.path.join(BASE, "work", f"国際寫眞新聞_{issue}号.pdf")
    raw_json = os.path.join(BASE, "work", "output", "01_raw_ocr", f"国際寫眞新聞_{issue}号.json")
    png_dir = os.path.join(BASE, "work", "cache_images", f"{issue}号")
    while not os.path.exists(raw_json):
        print(now(), f"{issue}号: 全体OCR の json を待つ", flush=True)
        time.sleep(60)
    time.sleep(5)  # 書き終わりを待つ
    contents = json.load(open(raw_json, encoding="utf-8"))["contents"]
    marks = page_rects(pdf_path)
    st = dict(written=0, skipped=0, no_marks=0, ocrd=0, no_text=0, errors=0)
    t_issue = time.time()
    for n in sorted(marks):
        if issue in viewer_issues():
            print(now(), f"{issue}号: ビューアがこの号を開いている → 止める", flush=True)
            return st
        page_index = n - 1
        state_path = work_state.work_path_for(pdf_path, page_index)
        if os.path.exists(state_path):
            print(now(), f"{issue}号 p{n}: 保存あり → 飛ばす", flush=True); st["skipped"] += 1; continue
        png_path = os.path.join(png_dir, f"国際寫眞新聞_{issue}号_p{n:04d}.png")
        pdf_loader.ensure_page_rendered(png_path, pdf_path, page_index)
        if not marks[n]:
            print(now(), f"{issue}号 p{n}: 印 0 → 書かない", flush=True); st["no_marks"] += 1; continue
        from PIL import Image
        W, H = Image.open(png_path).size
        boxes = []
        for x1, y1, x2, y2, kind in marks[n]:
            b = (max(0.0, x1), max(0.0, y1), min(float(W), x2), min(float(H), y2))
            if b[2] > b[0] and b[3] > b[1]:
                boxes.append(b)
        boxes.sort(key=lambda b: (b[1], b[0]))
        container = SelectionContainer()
        r1 = region1(contents[page_index]) if page_index < len(contents) else None
        if r1:
            container.add(r1)
        for b in boxes:
            container.add(b)
        rects = container.get_all()
        mark_rects = rects[1:] if r1 else rects
        edits = {}
        for box in mark_rects:
            t0 = time.time()
            try:
                text = region_ocr.region_ocr_text(png_path, box.bbox)
                lines = text.count("\n") + 1 if text else 0
                if text:
                    edits[box.rect_id] = text; st["ocrd"] += 1
                else:
                    st["no_text"] += 1
                print(now(), f"{issue}号 p{n} 枠{box.rect_id}: {time.time()-t0:.0f} 秒 {lines} 行", flush=True)
            except Exception as e:
                print(now(), f"{issue}号 p{n} 枠{box.rect_id}: 誤り {e}", flush=True); st["errors"] += 1
        if os.path.exists(state_path):
            print(now(), f"{issue}号 p{n}: 途中で保存された → 書かない", flush=True); st["skipped"] += 1; continue
        work_state.save_work_state(pdf_path, rects, edits, None, page_index=page_index)
        st["written"] += 1
        print(now(), f"{issue}号 p{n}: 書いた 枠 {len(mark_rects)}", flush=True)
    print(now(), f"{issue}号 終わり {(time.time()-t_issue)/60:.0f} 分", st, flush=True)
    return st


if __name__ == "__main__":
    for issue in sys.argv[1:]:
        run_issue(issue)
    print(now(), "全部 終わり", flush=True)
