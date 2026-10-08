# -*- coding: utf-8 -*-
"""残した 5 か所の幅を見本に揃えた v2 を作る（承認者のご依頼 10-08）。字は足さない・消さない。
C13「（２）」→「(2)」（見本: 数字の括弧は半角が多い 48/65・英数字は半角 124/125）
C18「發同盟)」×2 →「發同盟）」（日本語の中の括弧は全角 96/96。抜けた開き括弧は足さない）
C19「(前半…ところ)」→「（前半…ところ）」（35 字の 1 組）"""
import sys, os, openpyxl
sys.stdout.reconfigure(encoding="utf-8")
SRC = r"C:\Users\user\ndlocr-lite-custom\work\国際寫眞新聞_141号_p01-52_20261008_検品完了_記号揃え.xlsx"
DST = r"C:\Users\user\ndlocr-lite-custom\work\国際寫眞新聞_141号_p01-52_20261008_検品完了_記号揃え_v2.xlsx"
assert not os.path.exists(DST)
wb = openpyxl.load_workbook(SRC); ws = wb["入力フォーム"]
plan = [
    (13, "篇（２）－", "篇(2)－", 1),
    (18, "テデングトン發同盟)", "テデングトン發同盟）", 1),
    (18, "バルセロナ發同盟)", "バルセロナ發同盟）", 1),
    (19, "對全關西戰　(前半", "對全關西戰　（前半", 1),
    (19, "阻むところ)", "阻むところ）", 1),
]
for r, a, b, n in plan:
    t = ws.cell(r, 3).value
    assert t.count(a) == n, (r, a, t.count(a))
    nt = t.replace(a, b)
    assert len(nt) == len(t)
    ws.cell(r, 3).value = nt
    print(f"C{r}: {a} → {b}")
wb.save(DST)
print("書いた:", DST)
