import os
import csv
import io
import pytest
from custom_gui.selection import SelectionRect
from custom_gui.exporter import build_export_rows, rows_to_csv_text, rows_to_txt_text

def get_dummy_ocr_results():
    return [
        {"text": "第一章 序説", "bbox": [10.0, 10.0, 100.0, 30.0], "confidence": 0.99, "is_vertical": False, "source_image": "dummy.jpg"},
        {"text": "この書は", "bbox": [10.0, 40.0, 80.0, 60.0], "confidence": 0.98, "is_vertical": False, "source_image": "dummy.jpg"},
        {"text": "明治三十年に至り", "bbox": [150.0, 10.0, 300.0, 30.0], "confidence": 0.97, "is_vertical": False, "source_image": "dummy.jpg"},
        {"text": "外にあるテキスト", "bbox": [500.0, 500.0, 600.0, 520.0], "confidence": 0.95, "is_vertical": False, "source_image": "dummy.jpg"},
        {"text": "カンマ,入りテキスト", "bbox": [10.0, 100.0, 150.0, 120.0], "confidence": 0.90, "is_vertical": False, "source_image": "dummy.jpg"}
    ]

def get_dummy_rects():
    return [
        SelectionRect(rect_id="1", bbox=(0.0, 0.0, 110.0, 70.0), label="Region 1"),
        SelectionRect(rect_id="2", bbox=(140.0, 0.0, 310.0, 40.0), label="Region 2"),
        SelectionRect(rect_id="3", bbox=(0.0, 90.0, 160.0, 130.0), label="Region 3")
    ]

def test_build_export_rows():
    ocr_results = get_dummy_ocr_results()
    rects = get_dummy_rects()
    
    rows = build_export_rows("C:\\scan\\shiryo\\0002.jpg", rects, ocr_results)
    
    assert len(rows) == 3
    
    # Region 1
    assert rows[0]["image_name"] == "0002.jpg"
    assert rows[0]["region_id"] == "1"
    assert rows[0]["x1"] == 0.0
    assert rows[0]["y1"] == 0.0
    assert rows[0]["x2"] == 110.0
    assert rows[0]["y2"] == 70.0
    assert rows[0]["line_count"] == 2
    assert rows[0]["text"] == "第一章 序説\nこの書は"
    
    # Region 2
    assert rows[1]["image_name"] == "0002.jpg"
    assert rows[1]["region_id"] == "2"
    assert rows[1]["line_count"] == 1
    assert rows[1]["text"] == "明治三十年に至り"
    
    # Region 3 (comma text)
    assert rows[2]["image_name"] == "0002.jpg"
    assert rows[2]["region_id"] == "3"
    assert rows[2]["line_count"] == 1
    assert rows[2]["text"] == "カンマ,入りテキスト"

def test_csv_output():
    ocr_results = get_dummy_ocr_results()
    rects = get_dummy_rects()
    rows = build_export_rows("resource/digidepo_0024.jpg", rects, ocr_results)
    
    csv_text = rows_to_csv_text(rows)
    lines = csv_text.strip().split("\n")
    
    # Check header
    assert lines[0] == "image_name,region_id,x1,y1,x2,y2,line_count,text"
    
    # Use csv reader to parse back and verify
    reader = csv.DictReader(io.StringIO(csv_text))
    parsed_rows = list(reader)
    
    assert len(parsed_rows) == 3
    
    assert parsed_rows[0]["image_name"] == "digidepo_0024.jpg"
    assert parsed_rows[0]["region_id"] == "1"
    assert parsed_rows[0]["text"] == "第一章 序説\nこの書は" # Multiline preserved
    
    assert parsed_rows[2]["text"] == "カンマ,入りテキスト" # Comma preserved
    
def test_txt_output():
    ocr_results = get_dummy_ocr_results()
    rects = get_dummy_rects()
    rows = build_export_rows("resource/digidepo_0024.jpg", rects, ocr_results)
    
    txt_text = rows_to_txt_text(rows)
    
    expected_txt = "第一章 序説｜この書は｜明治三十年に至り｜カンマ,入りテキスト\n"
    assert txt_text == expected_txt

def test_zero_rects():
    rows = build_export_rows("test.jpg", [], [])
    
    csv_text = rows_to_csv_text(rows)
    assert csv_text.strip() == "image_name,region_id,x1,y1,x2,y2,line_count,text"
    
    txt_text = rows_to_txt_text(rows)
    assert txt_text == ""

def test_utf8_bom_writing(tmp_path):
    rows = build_export_rows("test.jpg", [], [])
    csv_text = rows_to_csv_text(rows)
    
    file_path = tmp_path / "test.csv"
    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(csv_text)
        
    with open(file_path, "rb") as f:
        content = f.read()
        
    assert content.startswith(b"\xef\xbb\xbf")
