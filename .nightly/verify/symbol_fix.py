# -*- coding: utf-8 -*-
"""141号（検品完了）の C 列の記号の幅を、見本 第28号の決まりに揃えた Excel を別名で作る（承認者 案A・10-08）。
揃える: 中に日本語のある括弧の組 → （）／ ? → ？／ = → ＝／ 半角の空白 → 全角の空白（英字と英字の間の空白は除く）
揃えない: 対になっていない括弧・中が数字英字だけの括弧（弱い決まり）・英字の間の空白 → 一覧に残す
元の Excel は変えない。字そのものは変えず、幅だけを変えたことを最後に確かめる。"""
import sys, re, os, openpyxl
sys.stdout.reconfigure(encoding="utf-8")
SRC = r"C:\Users\user\ndlocr-lite-custom\work\国際寫眞新聞_141号_p01-52_20261008_検品完了.xlsx"
DST = r"C:\Users\user\ndlocr-lite-custom\work\国際寫眞新聞_141号_p01-52_20261008_検品完了_記号揃え.xlsx"
assert not os.path.exists(DST), "出力が既にある"
WIDE = {"(": "（", ")": "）", "?": "？", "=": "＝", " ": "　"}
wb = openpyxl.load_workbook(SRC)
ws = wb["入力フォーム"]
counts = {"括弧の組": 0, "?": 0, "=": 0, "空白": 0}
left = []
for r in range(3, 31):
    t = ws.cell(r, 3).value
    if not t:
        continue
    s = list(t)
    paired = set()
    for m in re.finditer(r"([（(])([^（）()\n]{0,30})([）)])", t):
        inner = m.group(2)
        ascii_only = bool(inner) and re.fullmatch(r"[0-9A-Za-z０-９Ａ-Ｚａ-ｚ\s]+", inner) is not None
        paired.update({m.start(), m.end() - 1})
        if ascii_only:
            if (m.group(1), m.group(3)) != ("(", ")"):
                left.append((f"C{r}", "括弧（中が数字・英字）", t[max(0, m.start() - 6):m.end() + 6]))
            continue
        if (m.group(1), m.group(3)) != ("（", "）"):
            s[m.start()] = "（"; s[m.end() - 1] = "）"; counts["括弧の組"] += 1
    for i, ch in enumerate(t):
        if i in paired:
            continue
        if ch in "()":
            left.append((f"C{r}", "対になっていない括弧", t[max(0, i - 8):i + 8]))
        elif ch == "?":
            s[i] = "？"; counts["?"] += 1
        elif ch == "=":
            s[i] = "＝"; counts["="] += 1
        elif ch == " ":
            prev_c, next_c = (t[i - 1] if i > 0 else ""), (t[i + 1] if i + 1 < len(t) else "")
            if prev_c.isascii() and prev_c.isalpha() and next_c.isascii() and next_c.isalpha():
                left.append((f"C{r}", "英字の間の空白", t[max(0, i - 8):i + 8]))
            else:
                s[i] = "　"; counts["空白"] += 1
    new = "".join(s)
    # 幅だけが変わったか（長さが同じで、違う所はすべて WIDE の対応）
    assert len(new) == len(t)
    for a, b in zip(t, new):
        assert a == b or WIDE.get(a) == b, (r, a, b)
    ws.cell(r, 3).value = new
wb.save(DST)
print("書いた:", DST)
print("揃えた:", counts, "合計", sum(counts.values()))
print("揃えずに残した:", len(left))
for x in left:
    print("  ", x)
