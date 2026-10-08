# -*- coding: utf-8 -*-
"""141号（検品完了）の C 列から、見本 第28号の記号の使い方と違う所を抜き出す（10-08）。読むのは Excel だけ。
見本の決まり（10-08 に数えた値）:
  括弧の中に日本語 → 全角（）（見本 96/96）
  括弧の中が数字・英字だけ → 半角() が多い（見本 48/65）。全角なら「弱」として挙げる
  ？ ＝ 空白 → 全角（見本 ？5/5・＝15/15・空白45/45）
書く先: work\\proofread\\141号_記号の差.csv（UTF-8 BOM 付き）"""
import sys, re, csv, os, openpyxl
sys.stdout.reconfigure(encoding="utf-8")
SRC = r"C:\Users\user\ndlocr-lite-custom\work\国際寫眞新聞_141号_p01-52_20261008_検品完了.xlsx"
OUT = r"C:\Users\user\ndlocr-lite-custom\work\proofread\141号_記号の差.csv"
ws = openpyxl.load_workbook(SRC)["入力フォーム"]
rows = []
def ctx(t, s, e):
    return t[max(0, s - 8):e + 8].replace("\n", " ")
for r in range(3, 31):
    b, t = ws.cell(r, 2).value, str(ws.cell(r, 3).value or "")
    used = set()
    for m in re.finditer(r"([（(])([^（）()\n]{0,30})([）)])", t):
        inner, o, c = m.group(2), m.group(1), m.group(3)
        ascii_only = bool(inner) and re.fullmatch(r"[0-9A-Za-z０-９Ａ-Ｚａ-ｚ\s]+", inner) is not None
        used.update({m.start(), m.end() - 1})
        if not ascii_only and (o, c) != ("（", "）"):
            rows.append([f"C{r}", b, "括弧（中に日本語）", o + "…" + c, "（…）", "強（見本 96/96）", ctx(t, m.start(), m.end())])
        elif ascii_only and (o, c) != ("(", ")"):
            rows.append([f"C{r}", b, "括弧（中が数字・英字）", o + "…" + c, "(…)", "弱（見本 48/65）", ctx(t, m.start(), m.end())])
    for i, ch in enumerate(t):
        if i in used:
            continue
        if ch in "()":
            rows.append([f"C{r}", b, "対になっていない括弧", ch, "（ か ）", "強（見本 96/96）", ctx(t, i, i + 1)])
        elif ch == "?":
            rows.append([f"C{r}", b, "疑問符", "?", "？", "強（見本 5/5）", ctx(t, i, i + 1)])
        elif ch == "=":
            rows.append([f"C{r}", b, "等号", "=", "＝", "強（見本 15/15）", ctx(t, i, i + 1)])
        elif ch == " ":
            rows.append([f"C{r}", b, "空白", "半角の空白", "全角の空白", "強（見本 45/45）", ctx(t, i, i + 1)])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["セル", "行", "種類", "141号の字", "見本の字", "見本の強さ", "前後"])
    w.writerows(rows)
from collections import Counter
print("書いた:", OUT, "行:", len(rows))
print("種類別:", Counter(x[2] for x in rows))
print("セル別（上位）:", Counter(x[0] for x in rows).most_common(8))
for x in rows[:6]:
    print("  例:", x)
