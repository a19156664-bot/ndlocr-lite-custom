# -*- coding: utf-8 -*-
"""案A の 3 段目（AGENTS §8.15 ③）: 読み方の点検で「縦で読み直す」「拾い落とし」に分けられた枠を、
「縦で読む」（custom_gui.vertical_ocr）でまとめて読み直し、保存（work.json の edits）に書く。

使い方（cwd は ndlocr-lite-custom、python は .venv）:
  .venv\\Scripts\\python.exe .nightly\\verify\\reread_vertical.py <号> <読み方の点検 CSV>            … 試すだけ（書かない）
  .venv\\Scripts\\python.exe .nightly\\verify\\reread_vertical.py <号> <読み方の点検 CSV> --write    … 書く

読み方の点検 CSV の列: 頁,枠,分類,… （分類が「縦で読み直す」「拾い落とし」の行だけを読み直す）
決まり:
  - 縦で読んだ結果が空、または屑（ASCII 英数字が 2 割超・同じ字が 6 つ以上続く）なら書かない（回す）
  - 「拾い落とし」は、縦で読んだ字数が今の字数より多いときだけ書く（少なければ回す）
  - 「縦で読み直す」は、縦で読んだ字数が今の MIN_KEEP（7 割）以上のときだけ書く（下回れば回す）
  - 書いた枠の、前の文字と後の文字を <CSV と同じ所>\\<CSV の名前>_縦で読み直し_結果.csv に残す（判定と承認者の確認のため）
  - --write のときは、ビューア（127.0.0.1:8555）が開いていたら書かずに止まる
  - 書く前に、その号の保存を全部 work\\backup\\<時刻>_縦で読み直し前\\ に写す
  - 書いた後に読み戻し、書いた枠以外が 1 字も変わっていないことを確かめる
"""
import os, sys, csv, shutil, socket, datetime
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"C:\Users\user\ndlocr-lite-custom"
sys.path.insert(0, BASE)
import custom_gui.work_state as work_state
from custom_gui.selection import SelectionRect
from custom_gui.vertical_ocr import vertical_ocr_text

KINDS = ("縦で読み直す", "拾い落とし")
# 「縦で読み直す」でも、縦の字数が今の字数のこの割合を下回れば書かずに回す（縦は字を落とすことがある。141号 p41 R4 で 159→109 字）
MIN_KEEP = 0.7
# 縦の結果が屑なら回す: ASCII 英数字がこの割合を超える、または同じ字がこの数以上続く（142号 p5 R7 で「0000…」が 100 字近く出た）
JUNK_ASCII = 0.2
JUNK_RUN = 6

def junk(t):
    s = "".join(str(t).split())
    if not s: return True
    if sum(c.isascii() and c.isalnum() for c in s) / len(s) > JUNK_ASCII: return True
    run = 1
    for p, q in zip(s, s[1:]):
        run = run + 1 if p == q else 1
        if run >= JUNK_RUN: return True
    return False

def viewer_open():
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", 8555)) == 0

def flat(t):
    return "".join(str(t).split())

def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    num, csv_path, write = sys.argv[1], sys.argv[2], "--write" in sys.argv
    pdf = os.path.join(BASE, "work", f"国際寫眞新聞_{num}号.pdf")
    png = os.path.join(BASE, "work", "cache_images", f"{num}号", f"国際寫眞新聞_{num}号_p{{:04d}}.png")
    rows = [r for r in csv.DictReader(open(csv_path, encoding="utf-8-sig", newline="")) if r["分類"].strip() in KINDS]
    states, plan, skipped, log = {}, {}, [], []
    for r in rows:
        pg, fr, kind = int(r["頁"]), str(r["枠"]).replace("region", "").replace("Region", "").strip(), r["分類"].strip()
        if pg not in states:
            states[pg] = work_state.load_work_state(pdf, page_index=pg - 1)
        st = states[pg]
        rect = next((x for x in (st or {}).get("rects", []) if str(x["rect_id"]) == fr), None)
        if rect is None:
            skipped.append((pg, fr, kind, "枠が保存に無い")); continue
        cur = st["edits"].get(fr, "")
        new = vertical_ocr_text(png.format(pg), tuple(rect["bbox"]))
        a, b = len(flat(cur)), len(flat(new))
        if b == 0:
            skipped.append((pg, fr, kind, "縦で読んだ結果が空")); continue
        if junk(new):
            skipped.append((pg, fr, kind, f"縦の結果に屑（英数字が多い・同じ字が続く）（今 {a} 字・縦 {b} 字）")); continue
        if kind == "拾い落とし" and b <= a:
            skipped.append((pg, fr, kind, f"縦で読んでも字数が増えない（今 {a} 字・縦 {b} 字）")); continue
        if kind == "縦で読み直す" and b < a * MIN_KEEP:
            skipped.append((pg, fr, kind, f"縦の字数が今の {MIN_KEEP:.0%} を下回る（今 {a} 字・縦 {b} 字）")); continue
        plan[(pg, fr)] = new
        log.append({"頁": pg, "枠": fr, "分類": kind, "前の字数": a, "後の字数": b, "前の文字": cur, "後の文字": new})
        print(f"読み直す p{pg} R{fr}（{kind}）: {a} 字 → {b} 字")
    print(f"書く枠: {len(plan)}  回す: {len(skipped)}")
    for x in skipped:
        print("  回す:", x)
    stem = os.path.splitext(os.path.basename(csv_path))[0]
    out = os.path.join(os.path.dirname(os.path.abspath(csv_path)), f"{stem}_縦で読み直し_結果.csv")
    if log:
        with open(out, "w", encoding="utf-8-sig", newline="") as fp:
            w = csv.DictWriter(fp, fieldnames=list(log[0].keys())); w.writeheader(); w.writerows(log)
        print("結果:", out)
    if not write:
        print("（試すだけ。保存には書いていない）"); return 0
    if not plan:
        print("書く所が無い"); return 0
    if viewer_open():
        print("ビューア（8555）が開いている。書かずに止めた"); return 1
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(BASE, "work", "backup", f"{stamp}_{num}号_縦で読み直し前")
    os.makedirs(bdir)
    src_dir = work_state.work_dir_for(pdf)
    copied = 0
    for name in os.listdir(src_dir):
        if name.startswith(f"国際寫眞新聞_{num}号_p") and name.endswith(".work.json"):
            shutil.copy2(os.path.join(src_dir, name), bdir); copied += 1
    print(f"控え: {bdir}（{copied} 個）")
    for pg in sorted({p for p, _ in plan}):
        st = states[pg]
        before = dict(st["edits"])
        edits = dict(st["edits"])
        for (p, fr), txt in plan.items():
            if p == pg:
                edits[fr] = txt
        rects = [SelectionRect(rect_id=r["rect_id"], bbox=tuple(r["bbox"]), label=r["label"]) for r in st["rects"]]
        work_state.save_work_state(pdf, rects, edits, st["mark"], page_index=pg - 1)
        back = work_state.load_work_state(pdf, page_index=pg - 1)
        ok = back["edits"] == edits and [r["rect_id"] for r in back["rects"]] == [r["rect_id"] for r in st["rects"]] \
             and back["mark"] == st["mark"] and all(back["edits"][k] == v for k, v in before.items() if (pg, k) not in plan)
        print(f"書いた p{pg}: 読み戻し一致={ok}")
        if not ok:
            print("読み戻しが合わない。止めた（控えから戻せる）"); return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
