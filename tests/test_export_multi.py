import csv
import io
import pytest
from custom_gui.selection import SelectionRect
from custom_gui.exporter import build_export_rows_multi, rows_to_csv_text, rows_to_txt_text

def get_dummy_ocr_results():
    return [
        {"text": "A1 text", "bbox": [10.0, 10.0, 100.0, 30.0], "confidence": 0.99, "is_vertical": False, "source_image": "dummy.jpg"},
        {"text": "A2 text", "bbox": [10.0, 40.0, 80.0, 60.0], "confidence": 0.98, "is_vertical": False, "source_image": "dummy.jpg"},
        {"text": "B text", "bbox": [150.0, 10.0, 300.0, 30.0], "confidence": 0.97, "is_vertical": False, "source_image": "dummy.jpg"},
        {"text": "C text", "bbox": [500.0, 500.0, 600.0, 520.0], "confidence": 0.95, "is_vertical": False, "source_image": "dummy.jpg"}
    ]

def get_dummy_rects_a():
    return [
        SelectionRect(rect_id="1", bbox=(0.0, 0.0, 110.0, 70.0), label="Region 1"),
        SelectionRect(rect_id="2", bbox=(140.0, 0.0, 310.0, 40.0), label="Region 2")
    ]

def get_dummy_rects_c():
    return [
        SelectionRect(rect_id="1", bbox=(490.0, 490.0, 610.0, 530.0), label="Region 1")
    ]

def test_build_export_rows_multi():
    ocr_results = get_dummy_ocr_results()
    
    pages = [
        ("a.jpg", get_dummy_rects_a(), ocr_results, {"1": "Edited A1\nEdited A2"}),
        ("b.jpg", [], ocr_results, None), # empty, should be skipped
        ("c.jpg", get_dummy_rects_c(), ocr_results, None)
    ]
    
    rows = build_export_rows_multi(pages)
    
    # Assert (a): 3 rows total, correct image_names in order
    assert len(rows) == 3
    assert [r["image_name"] for r in rows] == ["a.jpg", "a.jpg", "c.jpg"]
    
    # Assert (b): Rectangle order preserved within image
    assert rows[0]["region_id"] == "1"
    assert rows[1]["region_id"] == "2"
    
    # Assert (c): Edit applied to image A rect 1 but not image C rect 1
    assert rows[0]["text"] == "Edited A1\nEdited A2"
    assert rows[2]["region_id"] == "1"
    assert rows[2]["text"] == "C text"
    
    # Assert (d): line_count tracks raw OCR lines
    assert rows[0]["line_count"] == 2 # "A1 text", "A2 text"
    assert rows[1]["line_count"] == 1 # "B text"
    assert rows[2]["line_count"] == 1 # "C text"
    
    csv_text = rows_to_csv_text(rows)
    lines = csv_text.strip().split("\n")
    
    # Assert (e): Combined CSV has ONE header row
    assert lines[0] == "image_name,region_id,x1,y1,x2,y2,line_count,text"
    reader = csv.DictReader(io.StringIO(csv_text))
    parsed_rows = list(reader)
    assert len(parsed_rows) == 3
    
    txt_text = rows_to_txt_text(rows)
    
    # Assert (f): TXT contains disambiguated names
    assert "=== a.jpg / Region 1 ===" in txt_text
    assert "=== c.jpg / Region 1 ===" in txt_text

def test_empty_pages_sequence():
    # Assert (g): Empty sequence produces CSV with header only and doesn't raise
    rows = build_export_rows_multi([])
    csv_text = rows_to_csv_text(rows)
    assert csv_text.strip() == "image_name,region_id,x1,y1,x2,y2,line_count,text"
