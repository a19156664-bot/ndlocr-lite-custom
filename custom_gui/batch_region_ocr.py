import argparse
import json
import os
import socket
import sys
import time

from custom_gui import work_state, pdf_loader, mark_detector, region_ocr
from custom_gui.selection import SelectionContainer

def viewer_is_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False

def parse_pages_arg(pages_str, count):
    if not pages_str:
        return list(range(1, count + 1))
    
    parts = pages_str.split("-")
    if len(parts) == 1:
        start = int(parts[0])
        end = start
    elif len(parts) == 2:
        start = int(parts[0])
        end = int(parts[1])
    else:
        return []
        
    return [i for i in range(start, end + 1) if 1 <= i <= count]

def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
        
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", required=True)
    parser.add_argument("--pages", default=None)
    parser.add_argument("--base", default=None)
    parser.add_argument("--viewer-port", type=int, default=8555)
    args = parser.parse_args(argv)
    
    base = args.base
    if not base:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    if viewer_is_open(args.viewer_port):
        print(f"ビューアが開いています（127.0.0.1:{args.viewer_port}）。閉じてから走らせてください。")
        return 2
        
    if not os.path.exists(os.path.join(base, "src", "ocr.py")):
        print(f"src/ocr.py not found in {base}")
        return 3

    issue = args.issue
    pdf_path = os.path.join(base, "work", f"国際寫眞新聞_{issue}号.pdf")
    raw_json_path = os.path.join(base, "work", "output", "01_raw_ocr", f"国際寫眞新聞_{issue}号.json")
    png_dir = os.path.join(base, "work", "cache_images", f"{issue}号")
    
    if not os.path.exists(pdf_path):
        print(f"{pdf_path} does not exist.")
        return 1
        
    if not os.path.exists(raw_json_path):
        print(f"{raw_json_path} does not exist.")
        return 1
        
    with open(raw_json_path, "r", encoding="utf-8") as f:
        raw_json = json.load(f)
        
    contents = raw_json.get("contents", [])
    count = len(contents)
    
    pages = []
    if args.pages:
        parts = args.pages.split("-")
        try:
            if len(parts) == 1:
                start = int(parts[0])
                end = start
            elif len(parts) == 2:
                start = int(parts[0])
                end = int(parts[1])
            else:
                raise ValueError
        except ValueError:
            print("Invalid --pages format")
            return 1
            
        if start < 1 or end > count or start > end:
            print(f"--pages outside 1..{count}")
            return 1
        pages = list(range(start, end + 1))
    else:
        pages = list(range(1, count + 1))
        
    written = 0
    skipped_saved = 0
    no_marks = 0
    boxes_ocrd = 0
    boxes_no_text = 0
    errors = 0
    
    for n in sorted(pages):
        page_index = n - 1
        state_path = work_state.work_path_for(pdf_path, page_index)
        
        if os.path.exists(state_path):
            print(f"p{n}: 保存あり → 飛ばす")
            skipped_saved += 1
            continue
            
        png_name = f"国際寫眞新聞_{issue}号_p{n:04d}.png"
        png_path = os.path.join(png_dir, png_name)
        
        pdf_loader.ensure_page_rendered(png_path, pdf_path, page_index)
        
        img = mark_detector.load_image(png_path)
        regions = mark_detector.detect_marks(img, color="lime")
        
        if not regions:
            print(f"p{n}: マーク 0 → 書かない")
            no_marks += 1
            continue
            
        container = SelectionContainer()
        
        page_lines = contents[page_index]
        all_xs = []
        all_ys = []
        
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
            if xs and ys:
                all_xs.extend(xs)
                all_ys.extend(ys)
                
        if all_xs and all_ys:
            min_x = max(0.0, min(all_xs) - 15.0)
            max_x = max(all_xs) + 15.0
            min_y = max(0.0, min(all_ys) - 15.0)
            max_y = max(all_ys) + 15.0
            container.add((min_x, min_y, max_x, max_y))
            
        for region in regions:
            container.add(region.bbox)
            
        edits = {}
        all_rects = container.get_all()
        # Marks are all rects except Region 1 if there were lines
        mark_rects = all_rects[1:] if (all_xs and all_ys) else all_rects
        
        for box in mark_rects:
            t0 = time.time()
            try:
                text = region_ocr.region_ocr_text(png_path, box.bbox)
                t1 = time.time()
                lines_count = text.count("\n") + 1 if text else 0
                
                if text:
                    edits[box.rect_id] = text
                    print(f"p{n} 枠{box.rect_id}: {t1-t0:.0f} 秒 {lines_count} 行", flush=True)
                    boxes_ocrd += 1
                else:
                    print(f"p{n} 枠{box.rect_id}: {t1-t0:.0f} 秒 0 行", flush=True)
                    boxes_no_text += 1
            except Exception as e:
                print(f"Error on p{n} 枠{box.rect_id}: {e}")
                errors += 1
                
        if os.path.exists(state_path):
            print(f"p{n}: 途中で保存された → 書かない")
            skipped_saved += 1
            continue
            
        work_state.save_work_state(pdf_path, container.get_all(), edits, None, page_index=page_index)
        written += 1
        
    print(f"Summary: written={written} skipped={skipped_saved} no_marks={no_marks} ocrd={boxes_ocrd} no_text={boxes_no_text} errors={errors}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
