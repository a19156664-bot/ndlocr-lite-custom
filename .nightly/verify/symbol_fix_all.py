# -*- coding: utf-8 -*-
"""C 列の記号の幅を、見本 第28号の決まりに 1 回で揃えた Excel を別名で作る（10-08。symbol_fix.py と symbol_fix_v2.py をまとめた版）。
使い方: python symbol_fix_all.py <元の xlsx> <出力の xlsx>
見本の決まり（10-08 に数えた値）:
  括弧の中に日本語 → 全角（）（96/96）。組は 60 字まで探す（141号 C19 に 35 字の組があった）
  括弧の中が数字・英字だけ → 半角()、中の全角英数字も半角（見本 括弧 48/65・英数字 124/125。承認者が C13「(2)」を確定）
  対になっていない半角の括弧 → 全角（日本語の中・96/96）。字は足さない（承認者「先頭の（なしOK」）
  ? → ？／ = → ＝／ 半角の空白 → 全角の空白（英字と英字の間の空白は除く）
字の長さは変えない（幅だけ）。元の Excel は変えない。"""
import sys, re, os, openpyxl
sys.stdout.reconfigure(encoding="utf-8")
SRC, DST = sys.argv[1], sys.argv[2]
assert not os.path.exists(DST), "出力が既にある"
FW = "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"
HW = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
TO_HALF = str.maketrans(FW, HW)
wb = openpyxl.load_workbook(SRC); ws = wb["入力フォーム"]
cnt = {"括弧(日本語)": 0, "括弧(数字英字)": 0, "片割れの括弧": 0, "?": 0, "=": 0, "空白": 0, "英字の間の空白(そのまま)": 0}
for r in range(3, ws.max_row + 1):
    t = ws.cell(r, 3).value
    if not t or not isinstance(t, str):
        continue
    s = list(t); paired = set()
    for m in re.finditer(r"([（(])([^（）()\n]{0,60})([）)])", t):
        inner = m.group(2)
        paired.update({m.start(), m.end() - 1})
        ascii_only = bool(inner) and re.fullmatch(r"[0-9A-Za-z０-９Ａ-Ｚａ-ｚ\s]+", inner) is not None
        if ascii_only:
            want = ("(", ")")
            new_inner = inner.translate(TO_HALF)
            if (m.group(1), m.group(3)) != want or new_inner != inner:
                s[m.start()] = "("; s[m.end() - 1] = ")"
                for i, ch in enumerate(new_inner):
                    s[m.start(2) + i] = ch
                cnt["括弧(数字英字)"] += 1
        elif (m.group(1), m.group(3)) != ("（", "）"):
            s[m.start()] = "（"; s[m.end() - 1] = "）"; cnt["括弧(日本語)"] += 1
    for i, ch in enumerate(t):
        if i in paired:
            continue
        if ch == "(":
            s[i] = "（"; cnt["片割れの括弧"] += 1
        elif ch == ")":
            s[i] = "）"; cnt["片割れの括弧"] += 1
        elif ch == "?":
            s[i] = "？"; cnt["?"] += 1
        elif ch == "=":
            s[i] = "＝"; cnt["="] += 1
        elif ch == " ":
            p_, n_ = (t[i - 1] if i else ""), (t[i + 1] if i + 1 < len(t) else "")
            if p_.isascii() and p_.isalpha() and n_.isascii() and n_.isalpha():
                cnt["英字の間の空白(そのまま)"] += 1
            else:
                s[i] = "　"; cnt["空白"] += 1
    new = "".join(s)
    assert len(new) == len(t)
    ws.cell(r, 3).value = new
wb.save(DST)
print("書いた:", DST); print("揃えた:", cnt)
