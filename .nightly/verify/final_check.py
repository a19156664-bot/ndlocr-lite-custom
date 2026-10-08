import sys, difflib, openpyxl, unicodedata
sys.stdout.reconfigure(encoding="utf-8")
W = r"C:\Users\user\ndlocr-lite-custom\work"
new = openpyxl.load_workbook(W + r"\国際寫眞新聞_141号_p01-52_20261008_校正済み_記号揃え.xlsx")["入力フォーム"]
old = openpyxl.load_workbook(W + r"\国際寫眞新聞_141号_p01-52_20261008_検品完了_記号揃え_v2.xlsx")["入力フォーム"]
rows = [(r, new.cell(r, 2).value, str(new.cell(r, 3).value or "")) for r in range(3, 31)]
print("行:", len(rows), "空の行:", [f"C{r}" for r, b, c in rows if not c], "B 列が v2 と同じ:", all(new.cell(r, 2).value == old.cell(r, 2).value for r in range(3, 31)))
print("字数:", sum(len(c) for _, _, c in rows), "■:", sum(c.count("■") for _, _, c in rows), [(f"C{r}", c.count("■")) for r, b, c in rows if "■" in c])
ctrl = [(r, repr(ch)) for r, b, c in rows for ch in c if unicodedata.category(ch).startswith("C")]
print("目に見えない字:", len(ctrl), ctrl[:5])
blocks = 0; changed_rows = 0
for r in range(3, 31):
    a, b = str(old.cell(r, 3).value or ""), str(new.cell(r, 3).value or "")
    if a != b:
        changed_rows += 1
        blocks += sum(1 for op in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op[0] != "equal")
print("v2 との違い: 変わった行", changed_rows, "字の違いのかたまり", blocks)
print("D3 の式:", new.cell(3, 4).value)