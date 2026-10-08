# -*- coding: utf-8 -*-
"""Antigravity 4 回目（39〜49 頁）31 件の判定を、置き換えの列つきで書く（10-08）。"""
import os, sys, csv, glob
sys.stdout.reconfigure(encoding="utf-8")
D = r"C:\Users\user\ndlocr-lite-custom\work\proofread"
items = []
for p in sorted(glob.glob(os.path.join(D, "141号_p*_校正案.csv"))):
    if 39 <= int(os.path.basename(p)[6:10]) <= 49:
        items += list(csv.DictReader(open(p, encoding="utf-8-sig", newline="")))
J = {n: ("当たり", "", "", "") for n in range(1, len(items) + 1)}
J[5] = ("当たり（要確認）", "拡大しても印刷は「近衞歩公第一」の「公」に見える。印刷どおりなら入力が正しい。承認者が画像で確かめる", "", "")
J[16] = ("当たり", "印刷は「銅像泉型は一丈八尺」（泉。原型の誤植と思われるが印刷どおり）。案の「原型」ではなく画像どおりで埋める",
         "銅像■型はい一■八尺", "銅像泉型は一丈八尺")
J[17] = ("当たり", "印刷は「素晴しく」（ら が無い）。画像どおりで埋める", "といふ素■しく巨大な", "といふ素晴しく巨大な")
J[19] = ("当たり", "見出しは旧字「肅」。案は全角空白まで消していたが、空白は人が入れた区切りなので残す", "岡田首相の粛　正放送", "岡田首相の肅　正放送")
J[26] = ("当たり", "「選擧肅正係」の肅は確か。「りでで」は列の頭が切れて確かめきれないので、粛→肅 だけ置き換える。残りは承認者へ",
         "選擧粛正係り", "選擧肅正係り")
J[27] = ("外れ", "印刷は「…ス・マリイ・ミーカーと云ふ」。案の「ミス・メリー・クリスマス」は作り替え。頭の「クリマス」が「クリスマス」の誤りかは承認者が画像で確かめる", "", "")
J[28] = ("当たり", "見出しは旧字「樂しい語ひ」。案の新字「楽」は誤り。い を足すのは正しい", "樂し語ひ", "樂しい語ひ")
J[29] = ("当たり", "印刷は「間牒」（へんが片）。案の「諜」ではなく画像どおりで埋める", "「間■」に出演", "「間牒」に出演")
out = os.path.join(D, "141号_4回目_指揮官の確認.csv")
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["番号", "頁", "枠", "入力値", "正しくは（Antigravity）", "確からしさ", "指揮官の判定", "メモ", "置き換え元", "置き換える文字"])
    for n, it in enumerate(items, 1):
        j, memo, a, b = J[n]
        w.writerow([n, it["頁"], it["枠"], it["入力値"], it["正しくは"], it["確からしさ(高/中/低)"], j, memo, a, b])
from collections import Counter
print(out, len(items), dict(Counter(J[n][0] for n in range(1, len(items) + 1))), "画像どおりに直した案:", sum(1 for n in J if J[n][3]))
