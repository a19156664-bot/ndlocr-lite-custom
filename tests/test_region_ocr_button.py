import os
import pytest
import flet as ft
from custom_gui.app import SelectableImageViewer
from tests.test_marks_to_rects import get_app, dummy_page, make_clean_page

@pytest.fixture
def dummy_page():
    class DummyPage:
        def __init__(self):
            self.controls = []
            self.overlay = []
        def add(self, *args):
            pass
        def update(self, *args):
            pass
        def run_thread(self, target, *args, **kwargs):
            # Run target synchronously for tests
            target(*args, **kwargs)
        window_width = 800
        window_height = 600
        session_id = "test"
    return DummyPage()

def get_prepared_app(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path, make_clean_page)
    
    # Prepare app.ocr_results and selections container
    app.ocr_results = [
        {"text": "これは", "bbox": (10, 10, 50, 20), "confidence": 0.9, "is_vertical": False, "source_image": "test"},
        {"text": "テスト", "bbox": (100, 100, 150, 120), "confidence": 0.9, "is_vertical": False, "source_image": "test"}
    ]
    
    app.selection_container._rects = []
    r2 = app.selection_container.add((0, 0, 60, 30))
    r2.rect_id = "2" # overrides randomly generated UUID to 2
    
    r3 = app.selection_container.add((80, 80, 200, 200))
    r3.rect_id = "3"
    
    app.edits = {}
    app.image_states[str(path)]["edits"] = app.edits
    app._update_selections_ui()
    return app, str(path)

def test_7_button_exists(dummy_page, tmp_path):
    app, _ = get_prepared_app(dummy_page, tmp_path)
    # 2 rows in selections_list. Each has an IconButton with tooltip "この枠だけOCR"
    rows = app.selections_list.controls
    assert len(rows) == 2
    
    for row in rows:
        # row is a Container -> Column -> Row -> Row of buttons
        item_content = row.content
        top_row = item_content.controls[0]
        buttons_row = top_row.controls[1]
        tooltips = [btn.tooltip for btn in buttons_row.controls if hasattr(btn, "tooltip")]
        assert "この枠だけOCR" in tooltips

def test_8_start_region_ocr_success(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_run_ocr_and_parse(p):
        return [{"text": "先生が轉んだので……"}, {"text": "北正夫"}]
    
    monkeypatch.setattr("custom_gui.ocr_bridge.run_ocr_and_parse", fake_run_ocr_and_parse)
    
    app.start_region_ocr("3")
    
    assert app.edits["3"] == "先生が轉んだので……\n北正夫"
    
    # Check label and status
    app._update_selections_ui()
    rows = app.selections_list.controls
    # row 3 is the second one
    r3_label = rows[1].content.controls[0].controls[0].value
    assert "(edited)" in r3_label
    
    assert "範囲OCR: 2 行" in app.status_text.value

def test_9_other_region_untouched(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_run_ocr_and_parse(p):
        return [{"text": "先生が轉んだので……"}, {"text": "北正夫"}]
    monkeypatch.setattr("custom_gui.ocr_bridge.run_ocr_and_parse", fake_run_ocr_and_parse)
    
    app.start_region_ocr("3")
    
    assert "2" not in app.edits
    rows = app.selections_list.controls
    # row 2 is the first one
    # label contains "これは" because region 2 contains line 1 ("これは")
    r2_content = rows[0].content.controls[1].value
    assert r2_content == "これは"

def test_10_empty_result(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_run_ocr_and_parse(p):
        return []
        
    monkeypatch.setattr("custom_gui.ocr_bridge.run_ocr_and_parse", fake_run_ocr_and_parse)
    
    app.start_region_ocr("3")
    
    assert "3" not in app.edits
    assert "範囲OCR: 文字が見つかりません" in app.status_text.value

def test_11_exception(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_run_ocr_and_parse(p):
        raise RuntimeError("boom")
        
    monkeypatch.setattr("custom_gui.ocr_bridge.run_ocr_and_parse", fake_run_ocr_and_parse)
    
    app.start_region_ocr("3")
    
    assert "3" not in app.edits
    assert "範囲OCR失敗" in app.status_text.value
    assert "boom" in app.status_text.value

def test_12_already_edited(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    app.edits["3"] = "人が直した"
    
    call_count = [0]
    def fake_run_ocr_and_parse(p):
        call_count[0] += 1
        return [{"text": "新テキスト"}]
        
    monkeypatch.setattr("custom_gui.ocr_bridge.run_ocr_and_parse", fake_run_ocr_and_parse)
    
    app.start_region_ocr("3")
    
    assert call_count[0] == 0
    assert app.edits["3"] == "人が直した"
    assert "編集済みの枠は範囲OCRしません" in app.status_text.value

def test_13_rect_deleted_during_ocr(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_run_ocr_and_parse(p):
        app.selection_container.delete_by_id("3")
        return [{"text": "先生が轉んだので……"}]
        
    monkeypatch.setattr("custom_gui.ocr_bridge.run_ocr_and_parse", fake_run_ocr_and_parse)
    
    app.start_region_ocr("3")
    
    assert "3" not in app.edits

def test_14_persistence(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_run_ocr_and_parse(p):
        return [{"text": "先生が轉んだので……"}, {"text": "北正夫"}]
        
    monkeypatch.setattr("custom_gui.ocr_bridge.run_ocr_and_parse", fake_run_ocr_and_parse)
    
    app.start_region_ocr("3")
    
    # Verify persistence
    import custom_gui.work_state
    state = custom_gui.work_state.load_work_state(str(path))
    assert "3" in state["edits"]
    assert state["edits"]["3"] == "先生が轉んだので……\n北正夫"

def test_15_button_click(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_run_ocr_and_parse(p):
        return [{"text": "先生が轉んだので……"}, {"text": "北正夫"}]
        
    monkeypatch.setattr("custom_gui.ocr_bridge.run_ocr_and_parse", fake_run_ocr_and_parse)
    
    rows = app.selections_list.controls
    # row 3 is the second one
    buttons_row = rows[1].content.controls[0].controls[1]
    
    # Find OCR button
    ocr_btn = None
    for btn in buttons_row.controls:
        if hasattr(btn, "tooltip") and btn.tooltip == "この枠だけOCR":
            ocr_btn = btn
            break
            
    assert ocr_btn is not None
    
    # Click it
    ocr_btn.on_click(None)
    
    assert app.edits["3"] == "先生が轉んだので……\n北正夫"
    assert "範囲OCR: 2 行" in app.status_text.value
