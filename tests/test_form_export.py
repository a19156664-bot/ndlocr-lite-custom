import csv
import hashlib
import os
import pytest
import openpyxl

from custom_gui.form_export import (
    spread_rows,
    read_viewer_csv,
    build_keywords,
    write_form,
    main,
)

def build_template(path: str):
    wb = openpyxl.Workbook()
    # rename default sheet
    ws = wb.active
    ws.title = "入力フォーム"
    
    # Header row 1
    ws["A1"] = "頁"
    ws["B1"] = "ノンブル"
    ws["C1"] = "キーワード"
    ws["D1"] = "Count"
    ws["E1"] = "備考"
    ws["F1"] = "=SUM(D3:D143)"
    ws["G1"] = "←合計文字数"
    
    # Header row 2
    ws["A2"] = "PDFの頁"
    ws["B2"] = "原稿記載の頁"
    ws["C2"] = "(instructions)"
    
    # Rows 3..143 with only the D formula
    for r in range(3, 144):
        ws.cell(row=r, column=4).value = f'=IF(LEN(B{r})+LEN(C{r})<>0,LEN(B{r})+LEN(C{r}),"")'
        
    wb.save(path)

def write_csv(path: str, rows: list[dict]):
    fieldnames = ["image_name", "region_id", "x1", "y1", "x2", "y2", "line_count", "text"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            # fill missing with defaults
            full_row = {
                "image_name": row.get("image_name", ""),
                "region_id": row.get("region_id", ""),
                "x1": row.get("x1", "0"),
                "y1": row.get("y1", "0"),
                "x2": row.get("x2", "0"),
                "y2": row.get("y2", "0"),
                "line_count": row.get("line_count", "1"),
                "text": row.get("text", "")
            }
            writer.writerow(full_row)

def test_spread_rows_52():
    rows = spread_rows(52)
    assert len(rows) == 27
    assert rows[0] == ("01", "表紙", [1])
    assert rows[1] == ("02", "表見返し-P.0001", [2, 3])
    assert rows[2] == ("03", "P.0002-P.0003", [4, 5])
    assert rows[25] == ("26", "P.0048-裏見返し", [50, 51])
    assert rows[26] == ("27", "裏表紙", [52])

def test_spread_rows_68():
    rows = spread_rows(68)
    assert len(rows) == 35
    assert rows[33][1] == "P.0064-裏見返し"
    assert rows[33][2] == [66, 67]
    assert rows[34][1] == "裏表紙"

def test_spread_rows_invalid_and_6():
    with pytest.raises(ValueError):
        spread_rows(51)
    with pytest.raises(ValueError):
        spread_rows(4)
        
    rows = spread_rows(6)
    assert rows == [
        ("01", "表紙", [1]),
        ("02", "表見返し-P.0001", [2, 3]),
        ("03", "P.0002-裏見返し", [4, 5]),
        ("04", "裏表紙", [6])
    ]

def test_region_1_excluded():
    csv_rows = [
        {"image_name": "stem_p0004.png", "region_id": "1", "text": "全文の行"},
        {"image_name": "stem_p0004.png", "region_id": "2", "text": "見出し"}
    ]
    keywords = build_keywords(csv_rows, 6)
    assert keywords[2] == "見出し"

def test_mark_first():
    csv_rows = [
        {"image_name": "stem_p0004.png", "region_id": "mark", "text": "【広告】"},
        {"image_name": "stem_p0004.png", "region_id": "2", "text": "見出し"}
    ]
    keywords = build_keywords(csv_rows, 6)
    assert keywords[2] == "【広告】｜見出し"

def test_ascending_pages():
    csv_rows = [
        {"image_name": "stem_p0005.png", "region_id": "2", "text": "後"},
        {"image_name": "stem_p0004.png", "region_id": "2", "text": "前"}
    ]
    keywords = build_keywords(csv_rows, 6)
    assert keywords[2] == "前｜後"

def test_newlines():
    csv_rows = [
        {"image_name": "stem_p0004.png", "region_id": "2", "text": "一行目\n二行目\n\n"}
    ]
    keywords = build_keywords(csv_rows, 6)
    assert keywords[2] == "一行目｜二行目"

def test_cover():
    # no rows for page 1
    csv_rows = []
    keywords = build_keywords(csv_rows, 6)
    assert keywords[0] == "【表紙】"
    
    # page 1 region 2 "写真説明"
    csv_rows = [
        {"image_name": "stem_p0001.png", "region_id": "2", "text": "写真説明"}
    ]
    keywords = build_keywords(csv_rows, 6)
    assert keywords[0] == "【表紙】｜写真説明"
    
    # page 1 mark "【表紙】" + region 2 "写真説明"
    csv_rows = [
        {"image_name": "stem_p0001.png", "region_id": "mark", "text": "【表紙】"},
        {"image_name": "stem_p0001.png", "region_id": "2", "text": "写真説明"}
    ]
    keywords = build_keywords(csv_rows, 6)
    assert keywords[0] == "【表紙】｜写真説明"

def test_tag_dedupe():
    # pages 2 and 3 both mark "【広告】"
    csv_rows = [
        {"image_name": "stem_p0002.png", "region_id": "mark", "text": "【広告】"},
        {"image_name": "stem_p0003.png", "region_id": "mark", "text": "【広告】"}
    ]
    keywords = build_keywords(csv_rows, 6)
    assert keywords[1] == "【広告】"
    
    # page 48 mark "【広告】" region 2 "記事", page 49 region 2 "【社告】", region 3 "記事"
    # Actually for N=52, pages [50, 51] mapped to P.0048-裏見返し
    # But wait, looking at the spec, "page 48 mark '【広告】', page 49..." might mean physical pages or PDF pages?
    # Ah, the test case says "pages 48 and 49", but if N=52, PDF pages 48 and 49 are spread 24 (index 23), wait:
    # 2k-2 = 48 -> 2k = 50 -> k = 25.
    # index 25-3 = 22? No, 2k-2 = 48 -> 2k = 50 -> k = 25.
    # index 25-1 = 24.
    csv_rows = [
        {"image_name": "stem_p0048.png", "region_id": "mark", "text": "【広告】"},
        {"image_name": "stem_p0048.png", "region_id": "2", "text": "記事"},
        {"image_name": "stem_p0049.png", "region_id": "2", "text": "【社告】"},
        {"image_name": "stem_p0049.png", "region_id": "3", "text": "記事"}
    ]
    keywords = build_keywords(csv_rows, 52)
    # the index for PDF pages 48 and 49 is when 2k-2 = 48 -> 2k = 50 -> k = 25.
    # spread_rows has ("25", "P.0046-P.0047", [48, 49]) at index 24. Let's check spread_rows.
    assert keywords[24] == "【広告】｜記事｜【社告】｜記事"

def test_empty_spread():
    csv_rows = []
    keywords = build_keywords(csv_rows, 6)
    assert keywords[1] is None

def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def test_end_to_end_write_form(tmp_path):
    template_path = str(tmp_path / "template.xlsx")
    out_path = str(tmp_path / "out.xlsx")
    build_template(template_path)
    tmpl_hash = file_hash(template_path)
    
    csv_rows = []
    keywords = build_keywords(csv_rows, 52)
    write_form(template_path, out_path, 52, keywords)
    
    assert file_hash(template_path) == tmpl_hash
    
    wb = openpyxl.load_workbook(out_path)
    assert "入力フォーム" in wb.sheetnames
    ws = wb["入力フォーム"]
    
    assert ws["A3"].value == "01"
    assert ws["B3"].value == "表紙"
    
    assert ws["A29"].value == "27"
    assert ws["B29"].value == "裏表紙"
    
    assert ws["A30"].value is None
    assert ws["B30"].value is None
    
    assert ws["D3"].value == '=IF(LEN(B3)+LEN(C3)<>0,LEN(B3)+LEN(C3),"")'
    
    assert ws["F1"].value == "=SUM(D3:D143)"
    assert ws["G1"].value == "←合計文字数"
    assert ws["A2"].value == "PDFの頁"
    assert ws["B2"].value == "原稿記載の頁"
    assert ws["C2"].value == "(instructions)"

def test_write_form_refusals(tmp_path):
    template_path = str(tmp_path / "template.xlsx")
    out_path = str(tmp_path / "out.xlsx")
    build_template(template_path)
    
    with open(out_path, "w") as f:
        f.write("exists")
        
    keywords = build_keywords([], 6)
    with pytest.raises(FileExistsError):
        write_form(template_path, out_path, 6, keywords)
        
    with pytest.raises(ValueError):
        write_form(template_path, template_path, 6, keywords)

def test_page_numbers():
    assert build_keywords([{"image_name": "国際寫眞新聞_141号_p0004.png", "region_id": "2", "text": "a"}], 6)[2] == "a"
    assert build_keywords([{"image_name": "国際寫眞新聞_028号_000004.jpg", "region_id": "2", "text": "a"}], 6)[2] == "a"
    
    with pytest.raises(ValueError):
        build_keywords([{"image_name": "cover.png", "region_id": "2", "text": "a"}], 6)
        
    with pytest.raises(ValueError):
        build_keywords([{"image_name": "stem_p0053.png", "region_id": "2", "text": "a"}], 52)
        
    with pytest.raises(ValueError):
        build_keywords([
            {"image_name": "stemA_p0001.png", "region_id": "2", "text": "a"},
            {"image_name": "stemB_p0002.png", "region_id": "2", "text": "b"}
        ], 6)

def test_main(tmp_path):
    csv_path = str(tmp_path / "data.csv")
    template_path = str(tmp_path / "template.xlsx")
    out_path = str(tmp_path / "out.xlsx")
    
    csv_rows = [
        {"image_name": "stem_p0004.png", "region_id": "mark", "text": "【広告】"},
        {"image_name": "stem_p0004.png", "region_id": "2", "text": "見出し"}
    ]
    write_csv(csv_path, csv_rows)
    build_template(template_path)
    
    argv = ["--csv", csv_path, "--pages", "6", "--template", template_path, "--out", out_path]
    ret = main(argv)
    
    assert ret == 0
    assert os.path.exists(out_path)
    
    expected_keywords = build_keywords(csv_rows, 6)
    
    wb = openpyxl.load_workbook(out_path)
    ws = wb["入力フォーム"]
    # Spread 3 is row index 2 in 0-based spread_rows list, which corresponds to row 5 in sheet
    assert ws["C5"].value == expected_keywords[2]
