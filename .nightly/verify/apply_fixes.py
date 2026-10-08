# -*- coding: utf-8 -*-
"""指揮官が画像で「当たり」と判定した校正の指摘を、保存（work.json の edits）に機械的に置き換える（承認者 案A・10-08）。

使い方（cwd は ndlocr-lite-custom、python は .venv）:
  .venv\\Scripts\\python.exe .nightly\\verify\\apply_fixes.py <号> <確認の CSV>            … 試すだけ（書かない）
  .venv\\Scripts\\python.exe .nightly\\verify\\apply_fixes.py <号> <確認の CSV> --write    … 書く

確認の CSV の列: 番号,頁,枠,入力値,正しくは（Antigravity）,確からしさ,指揮官の判定,メモ
  置き換えるのは「指揮官の判定」が「当たり」の行だけ。
決まり:
  - 枠に人の直した文字（edits）が無いときは置き換えない（承認者に回す）
  - 「入力値」が枠の文字に、ちょうど 1 回あるときだけ置き換える（0 回・2 回以上は回す）
  - 置き換える範囲に改行があるときは置き換えない（行の区切りが変わるため。回す）
  - --write のときは、ビューア（127.0.0.1:8555）が開いていたら書かずに止まる
  - 書く前に、その号の保存を全部 work\\backup\\<時刻>_置き換え前\\ に写す
  - 書いた後に読み戻し、置き換えた所以外が 1 字も変わっていないことを確かめる
"""
import os, sys, csv, json, shutil, socket, datetime
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"C:\Users\user\ndlocr-lite-custom"
sys.path.insert(0, BASE)
import custom_gui.work_state as work_state
from custom_gui.selection import SelectionRect

def viewer_open():
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", 8555)) == 0

def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    num, csv_path, write = sys.argv[1], sys.argv[2], "--write" in sys.argv
    pdf = os.path.join(BASE, "work", f"国際寫眞新聞_{num}号.pdf")
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig", newline="")))
    plan, skipped = {}, []
    states = {}
    for r in rows:
        if r["指揮官の判定"] != "当たり":
            continue
        pg, fr = int(r["頁"]), str(r["枠"]).replace("region", "").replace("Region", "").strip()
        old, new = r["入力値"], r["正しくは（Antigravity）"]
        if pg not in states:
            states[pg] = work_state.load_work_state(pdf, page_index=pg - 1)
        st = states[pg]
        if not st or fr not in st["edits"]:
            skipped.append((r["番号"], pg, fr, old, "直した文字が無い枠")); continue
        cur = plan.get((pg, fr), st["edits"][fr])
        n = cur.count(old)
        if n != 1:
            if n == 0 and new in cur:
                skipped.append((r["番号"], pg, fr, old, "もう直っている")); continue
            # 改行をまたいでいるかを見る
            flat = cur.replace("\n", "")
            reason = "改行をまたぐ" if flat.count(old) == 1 else f"入力値が {n} 回"
            skipped.append((r["番号"], pg, fr, old, reason)); continue
        plan[(pg, fr)] = cur.replace(old, new, 1)
        print(f"置き換え #{r['番号']} p{pg} R{fr}: {old} → {new}")
    print(f"置き換える枠: {len(plan)}  回す: {len(skipped)}")
    for x in skipped:
        print("  回す:", x)
    if not write:
        print("（試すだけ。書いていない）"); return 0
    if not plan:
        print("書く所が無い"); return 0
    if viewer_open():
        print("ビューア（8555）が開いている。書かずに止めた"); return 1
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(BASE, "work", "backup", f"{stamp}_置き換え前")
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
