# -*- coding: utf-8 -*-
"""Antigravity 3 回目（27〜37 頁）15 件の判定を、置き換えの列つきで書く（10-08）。"""
import os, sys, csv, glob
sys.stdout.reconfigure(encoding="utf-8")
D = r"C:\Users\user\ndlocr-lite-custom\work\proofread"
items = []
for p in sorted(glob.glob(os.path.join(D, "141号_p*_校正案.csv"))):
    if 27 <= int(os.path.basename(p)[6:10]) <= 37:
        items += list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))
J = {n: ("当たり", "", "", "") for n in range(1, len(items) + 1)}
J[1] = ("当たり", "旧字「廣」。写真の上の白抜きの字", "", "")
J[3] = ("当たり", "#3〜#5 は同じ所の重なり。画像は「鋼鐵製で直徑約八尺、長さ四マイル」。1 つにまとめて置き換える",
        "サイフオンは鋼繊製で直■約八寸、長さ", "サイフオンは鋼鐵製で直徑約八尺、長さ")
J[4] = ("当たり（#3 にまとめた）", "#3 で置き換える", "", "")
J[5] = ("当たり（#3 にまとめた）", "#3 で置き換える", "", "")
J[12] = ("当たり", "次の列にまたがる「「肅｜正明朗に」」。旧字「肅」", "", "")
J[13] = ("当たり", "■ を埋めるのは正しいが、案の「素晴らしい」は誤り。印刷は「素晴しいもの」（ら が無い）。画像どおりで置き換える",
         "蒲團も特製の素■しいもの", "蒲團も特製の素晴しいもの")
J[14] = ("当たり", "題字は右から左の横書き。本文に「九官鳥」が繰り返し出る", "", "")
J[15] = ("当たり（要確認）", "題字の「藤」が半分ほどしか見えない。承認者が画像で確かめる", "", "")
out = os.path.join(D, "141号_3回目_指揮官の確認.csv")
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["番号", "頁", "枠", "入力値", "正しくは（Antigravity）", "確からしさ", "指揮官の判定", "メモ", "置き換え元", "置き換える文字"])
    for n, it in enumerate(items, 1):
        j, memo, a, b = J[n]
        w.writerow([n, it["頁"], it["枠"], it["入力値"], it["正しくは"], it["確からしさ(高/中/低)"], j, memo, a, b])
from collections import Counter
print(out, len(items), dict(Counter(J[n][0] for n in range(1, len(items) + 1))))
