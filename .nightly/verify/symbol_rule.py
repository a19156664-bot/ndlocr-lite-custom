# -*- coding: utf-8 -*-
"""見本 第28号と 141号（検品完了）の C 列で、記号の全角・半角を記号ごとに数える。括弧は中身で分ける。読むだけ。"""
import sys, re, openpyxl
sys.stdout.reconfigure(encoding="utf-8")
FILES = [("見本28", r"C:\Users\user\ndlocr-lite-custom\work\mihon\A案）国際寫眞新聞_028号.xlsx"),
         ("141", r"C:\Users\user\ndlocr-lite-custom\work\国際寫眞新聞_141号_p01-52_20261008_検品完了.xlsx")]
PAIRS = [("（", "("), ("）", ")"), ("：", ":"), ("，", ","), ("．", "."), ("＋", "+"), ("－", "-"), ("％", "%"),
         ("＆", "&"), ("＃", "#"), ("／", "/"), ("！", "!"), ("？", "?"), ("＝", "="), ("［", "["), ("］", "]"),
         ("＊", "*"), ("；", ";"), ("＜", "<"), ("＞", ">"), ("～", "~"), ("　", " ")]
def texts(p):
    ws = openpyxl.load_workbook(p)["入力フォーム"]
    return "".join(str(ws.cell(r, 3).value or "") + "\n" for r in range(3, ws.max_row + 1))
T = {k: texts(p) for k, p in FILES}
print("記号      見本(全/半)   141(全/半)")
for fw, hw in PAIRS:
    a, b = T["見本28"], T["141"]
    if a.count(fw) + a.count(hw) + b.count(fw) + b.count(hw) == 0:
        continue
    print(f" {fw}{hw!r:5}   {a.count(fw):4}/{a.count(hw):<4}    {b.count(fw):4}/{b.count(hw):<4}")
# 括弧の中身で分ける
pat = re.compile(r"([（(])([^（）()\n]{0,30})([）)])")
for k in T:
    kinds = {}
    for m in pat.finditer(T[k]):
        inner = m.group(2)
        cls = "中が数字・英字だけ" if inner and re.fullmatch(r"[0-9A-Za-z０-９Ａ-Ｚａ-ｚ\s]+", inner) else ("空" if not inner else "中に日本語")
        key = (cls, m.group(1) + m.group(3))
        kinds[key] = kinds.get(key, 0) + 1
    print(k, "括弧:", sorted(kinds.items()))
