import os
import csv
from io import StringIO
from custom_gui.page_states import page_ocr_enabled, build_page_state, REGION1_MARGIN
from custom_gui.selection import SelectionContainer, SelectionRect
from custom_gui.app import OcrState
from custom_gui.exporter import build_export_rows
from custom_gui.form_export import build_keywords

def test_1_page_ocr_enabled():
    assert page_ocr_enabled({}) == True
    assert page_ocr_enabled({"NDLOCR_PAGE_OCR": "on"}) == True
    assert page_ocr_enabled({"NDLOCR_PAGE_OCR": ""}) == True
    assert page_ocr_enabled({"NDLOCR_PAGE_OCR": "OFF"}) == False
    assert page_ocr_enabled({"NDLOCR_PAGE_OCR": " off "}) == False
    assert page_ocr_enabled({"NDLOCR_PAGE_OCR": "no"}) == True

def test_2_page_ocr_true_empty_container():
    container = SelectionContainer()
    parsed = [
        {"text": "A", "bbox": (10, 20, 110, 40), "confidence": 0.9, "is_vertical": False, "source_image": "doc_p0001.png"},
        {"text": "B", "bbox": (5, 100, 60, 300), "confidence": 0.9, "is_vertical": False, "source_image": "doc_p0001.png"}
    ]
    state = build_page_state(parsed, container, edits={"1": "test"}, mark="X", page_ocr=True)
    
    rects = container.get_all()
    assert len(rects) == 1
    assert rects[0].rect_id == "1"
    # min_x = max(0, 5 - 15) = 0.0
    # min_y = max(0, 20 - 15) = 5.0
    # max_x = 110 + 15 = 125.0
    # max_y = 300 + 15 = 315.0
    assert rects[0].bbox == (0.0, 5.0, 125.0, 315.0)
    
    assert state["ocr_results"] is parsed
    assert state["ocr_state"] == OcrState.DONE
    assert state["edits"] == {"1": "test"}
    assert state["mark"] == "X"

def test_3_page_ocr_true_container_not_empty():
    container = SelectionContainer()
    container.restore([
        SelectionRect(rect_id="4", bbox=(0,0,10,10), label="R4"),
        SelectionRect(rect_id="5", bbox=(0,0,10,10), label="R5")
    ])
    parsed = [{"text": "A", "bbox": (10, 20, 110, 40), "confidence": 0.9, "is_vertical": False, "source_image": "doc_p0001.png"}]
    state = build_page_state(parsed, container, edits={}, mark=None, page_ocr=True)
    
    rects = container.get_all()
    assert len(rects) == 2
    assert set(r.rect_id for r in rects) == {"4", "5"}

def test_4_page_ocr_true_parsed_empty():
    container = SelectionContainer()
    parsed = []
    state = build_page_state(parsed, container, edits={}, mark=None, page_ocr=True)
    
    rects = container.get_all()
    assert len(rects) == 0
    rect = container.add((0,0,10,10))
    assert rect.rect_id == "1"

def test_5_page_ocr_false_empty_container():
    container = SelectionContainer()
    parsed = [{"text": "A", "bbox": (10, 20, 110, 40), "confidence": 0.9, "is_vertical": False, "source_image": "doc_p0001.png"}]
    state = build_page_state(parsed, container, edits={}, mark=None, page_ocr=False)
    
    assert len(container.get_all()) == 0
    assert state["ocr_results"] == []
    
    rect = container.add((0,0,10,10))
    assert rect.rect_id == "2"

def test_6_page_ocr_false_restore():
    container = SelectionContainer()
    container.restore([])
    state = build_page_state([], container, edits={}, mark=None, page_ocr=False)
    rect = container.add((0,0,10,10))
    assert rect.rect_id == "2"
    
    container2 = SelectionContainer()
    container2.restore([
        SelectionRect(rect_id="4", bbox=(0,0,10,10), label="R4"),
        SelectionRect(rect_id="5", bbox=(0,0,10,10), label="R5")
    ])
    state2 = build_page_state([], container2, edits={}, mark=None, page_ocr=False)
    rect2 = container2.add((0,0,10,10))
    assert rect2.rect_id == "6"

def test_7_ensure_next_id_at_least():
    container = SelectionContainer()
    container.ensure_next_id_at_least(2)
    rect1 = container.add((0,0,10,10))
    assert rect1.rect_id == "2"
    
    container.restore([SelectionRect(rect_id="7", bbox=(0,0,10,10), label="R7")])
    container.ensure_next_id_at_least(2)
    rect2 = container.add((0,0,10,10))
    assert rect2.rect_id == "8"

def test_8_export_path_switch_off():
    container = SelectionContainer()
    state = build_page_state([], container, edits={}, mark=None, page_ocr=False)
    container.add((0,0,10,10)) # gets id "2"
    rects = container.get_all()
    
    rows = build_export_rows("x.png", rects, state["ocr_results"], edited_texts={})
    assert len(rows) == 1
    assert rows[0]["text"] == "" # text for "2"
    
    rows_edited = build_export_rows("x.png", rects, state["ocr_results"], edited_texts={"2": "縦書き"})
    assert len(rows_edited) == 1
    assert rows_edited[0]["text"] == "縦書き"

def test_9_row_survives_excel_keyword_step(tmp_path):
    csv_path = tmp_path / "test.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["image_name", "region_id", "x1", "y1", "x2", "y2", "line_count", "text"])
        writer.writerow(["doc_p0001.png", "2", "0.0", "0.0", "10.0", "10.0", "1", "縦書き"])
    
    def read_viewer_csv_dict(path):
        with open(path, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return list(reader)

    rows = read_viewer_csv_dict(csv_path)
    keywords = build_keywords(rows, n_pages=6)
    assert len(keywords) > 0
    assert "縦書き" in keywords[0]
