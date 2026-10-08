# -*- coding: utf-8 -*-
"""Antigravity 2 回目（14〜24 頁）26 件の、指揮官が画像で見た判定を一覧にする（10-08）。"""
import os, sys, csv, glob
sys.stdout.reconfigure(encoding="utf-8")
D = r"C:\Users\user\ndlocr-lite-custom\work\proofread"
items = []
for p in sorted(glob.glob(os.path.join(D, "141号_p*_校正案.csv"))):
    if 14 <= int(os.path.basename(p)[6:10]) <= 24:
        items += list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))
judge = {n: ("当たり", "") for n in range(1, len(items) + 1)}
judge[1] = ("当たり", "印刷では片仮名エと漢字工が見分けにくい。エ國＝エチオピアの意味から当たり")
judge[13] = ("当たり", "字の並び（古篇代 篇→古代篇）が当たり。括弧と数字の幅は見本どおりに機械で揃える")
judge[6] = ("外れ", "印刷は濁点の無い「デサイナー」。入力が印刷どおり")
judge[11] = ("外れ", "印刷は「ジエームスウイルス君」で「・」が無い。入力が印刷どおり")
judge[14] = ("外れ", "印刷は「重體量」。入力が印刷どおり")
judge[26] = ("外れ", "印刷は「(同上右)」。入力が印刷どおり")
judge[25] = ("要判断", "印刷はくの字点「ゾロ〳〵」。■ を埋めるのは正しいが、「ゾロゾロ」と開くか「〳〵」のままかは承認者が決める（見本 28号に例なし）")
out = os.path.join(D, "141号_2回目_指揮官の確認.csv")
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["番号", "頁", "枠", "入力値", "正しくは（Antigravity）", "確からしさ", "指揮官の判定", "メモ"])
    for n, it in enumerate(items, 1):
        j, memo = judge[n]
        w.writerow([n, it["頁"], it["枠"], it["入力値"], it["正しくは"], it["確からしさ(高/中/低)"], j, memo])
from collections import Counter
print(out, len(items), dict(Counter(judge[n][0] for n in range(1, len(items) + 1))))
print("外れの確からしさ:", [(n, items[n - 1]["確からしさ(高/中/低)"]) for n in (6, 11, 14, 26)])
for n, it in enumerate(items, 1):
    if judge[n][0] == "当たり":
        print(f'| {it["頁"]} | Region {it["枠"]} | {it["入力値"]} | {it["正しくは"]} |')
