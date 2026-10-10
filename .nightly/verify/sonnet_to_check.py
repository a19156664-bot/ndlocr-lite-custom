# -*- coding: utf-8 -*-
"""④ Sonnet の返事（「頁 | 枠 | 入力値 | 正しくは | 理由 | 確からしさ」の行）を、⑤ の確認の CSV にする（10-09 夜）。
入力値が保存の文字（校正の入力.csv）にちょうど 1 回あるかも数え、メモに書く（0 回・2 回以上は ★）。
数えるときだけ両側を NFKC にそろえる（互換用の漢字 福 U+FA1B などで 0 回にならないように）。保存の字は変えない（10-10 承認者「出来るだけ旧字体」）。
「指揮官の判定」は空のまま。判定は指揮官が画像で入れる。

使い方: .venv\\Scripts\\python.exe .nightly\\verify\\sonnet_to_check.py <号> <返事を貼ったテキスト> <書き先 CSV>
"""
import sys, csv, re, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
nfkc = lambda s: unicodedata.normalize("NFKC", s)
BASE = r"C:\Users\user\ndlocr-lite-custom"
num, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
txt = {(r["頁"], r["枠"]): r["文字"] for r in
       csv.DictReader(open(f"{BASE}\\work\\proofread\\{num}号_校正の入力.csv", encoding="utf-8-sig"))}
rows = []
for line in open(src, encoding="utf-8"):
    parts = [p.strip() for p in line.rstrip("\n").split("|")]
    if len(parts) < 6 or not re.fullmatch(r"p?\d+", parts[0]):
        continue
    pg = str(int(parts[0].lstrip("p"))); fr = parts[1]
    old, new, why, conf = parts[2], parts[3], parts[4], parts[5]
    n = nfkc(txt.get((pg, fr), "")).count(nfkc(old))
    rows.append([len(rows) + 1, pg, fr, old, new, conf, "", ("" if n == 1 else f"★入力値 {n} 回") + "｜" + why, "", ""])
with open(out, "w", encoding="utf-8-sig", newline="") as fp:
    w = csv.writer(fp)
    w.writerow(["番号", "頁", "枠", "入力値", "正しくは（Antigravity）", "確からしさ", "指揮官の判定", "メモ", "置き換え元", "置き換える文字"])
    w.writerows(rows)
bad = [r for r in rows if r[7].startswith("★")]
print(f"{len(rows)} 件 → {out}（入力値が 1 回でない: {len(bad)} 件）")
for r in bad:
    print("  ", r[0], r[1], r[2], r[3], r[7].split("｜")[0])
