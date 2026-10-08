# -*- coding: utf-8 -*-
"""Antigravity 1 回目（1・5〜13 頁）31 件の、指揮官が画像で見た判定を一覧にする（10-08）。"""
import os, sys, csv, glob
sys.stdout.reconfigure(encoding="utf-8")
D = r"C:\Users\user\ndlocr-lite-custom\work\proofread"
items = []
for p in sorted(glob.glob(os.path.join(D, "141号_p*_校正案.csv"))):
    items += list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))
judge = {n: ("当たり", "") for n in range(1, 32)}
judge[2] = ("当たり", "「新」の字。上の方が少し切れていたが「新帝」と読める")
judge[16] = ("当たり", "「歐」の字は半分見えた")
judge[7] = ("外れ", "寫眞(上) の説明は「グヰーン」と濁点つきで印刷されている（(下) と見出しは「クヰーン」）。入力が印刷どおり")
judge[13] = ("外れ", "見出しの太字は「チヱツコ」と印刷されている（本文は「チエツコ」）。入力が印刷どおり")
out = os.path.join(D, "141号_1回目_指揮官の確認.csv")
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["番号", "頁", "枠", "入力値", "正しくは（Antigravity）", "確からしさ", "指揮官の判定", "メモ"])
    for n, it in enumerate(items, 1):
        j, memo = judge[n]
        w.writerow([n, it["頁"], it["枠"], it["入力値"], it["正しくは"], it["確からしさ(高/中/低)"], j, memo])
from collections import Counter
c = Counter(judge[n][0] for n in range(1, len(items) + 1))
print(out, len(items), dict(c))
print("外れの確からしさ:", [(n, items[n - 1]["確からしさ(高/中/低)"]) for n in (7, 13)])
