import pytest
import flet as ft
from custom_gui.app import SelectableImageViewer
from tests.test_marks_to_rects import get_app, make_clean_page

@pytest.fixture
def dummy_page():
    class DummyPage:
        def __init__(self):
            self.controls = []
            self.overlay = []
            self.pending = []
        def add(self, *args):
            pass
        def update(self, *args):
            pass
        def run_thread(self, target, *args, **kwargs):
            self.pending.append((target, args, kwargs))
        window_width = 800
        window_height = 600
        session_id = "test"
    return DummyPage()

def get_prepared_app(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path, make_clean_page)
    
    app.ocr_results = [
        {"text": "これは", "bbox": (10, 10, 50, 20), "confidence": 0.9, "is_vertical": False, "source_image": "test"},
        {"text": "テスト", "bbox": (100, 100, 150, 120), "confidence": 0.9, "is_vertical": False, "source_image": "test"}
    ]
    
    app.selection_container._rects = []
    r2 = app.selection_container.add((0, 0, 60, 30))
    r2.rect_id = "2"
    r2.label = "Region 2"
    
    r3 = app.selection_container.add((80, 80, 200, 200))
    r3.rect_id = "3"
    r3.label = "Region 3"
    
    app.edits = {}
    app.image_states[str(path)]["edits"] = app.edits
    app._update_selections_ui()
    return app, str(path)

def test_1_button_place(dummy_page, tmp_path):
    app, path = get_prepared_app(dummy_page, tmp_path)
    row_3 = app.selections_list.controls[1]
    
    buttons_row = row_3.content.controls[0].controls[1]
    tooltips = [b.tooltip for b in buttons_row.controls if hasattr(b, "tooltip")]
    assert tooltips == ["Edit", "右から変換", "この枠だけOCR", "画像の枠を隠す", "縦で読む", "Delete"]
    
    vertical_button = buttons_row.controls[4]
    assert vertical_button.icon == ft.Icons.TEXT_ROTATION_DOWN

def test_2_vertical_button_reads_vertical(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    calls_v = []
    def fake_v(p, b):
        calls_v.append((p, b))
        return "縦\n書"
    def fake_r(p, b):
        raise AssertionError("Should not be called")
        
    monkeypatch.setattr("custom_gui.app.vertical_ocr_text", fake_v)
    monkeypatch.setattr("custom_gui.app.region_ocr_text", fake_r)
    
    row_2_before = app.selections_list.controls[0]
    row_3_before = app.selections_list.controls[1]
    buttons_row = row_3_before.content.controls[0].controls[1]
    vertical_button = buttons_row.controls[4]
    
    vertical_button.on_click(None)
    
    assert row_3_before.bgcolor == ft.Colors.ORANGE_100
    
    t, a, k = dummy_page.pending.pop(0)
    t(*a, **k)
    
    assert app.edits["3"] == "縦\n書"
    assert len(calls_v) == 1
    assert calls_v[0][0] == path
    assert calls_v[0][1] == (80, 80, 200, 200)
    
    row_3_after = app.selections_list.controls[1]
    assert row_3_after.bgcolor is None
    content_area = row_3_after.content.controls[1]
    assert content_area.value == "縦\n書"
    
    assert app.selections_list.controls[0] is row_2_before

def test_3_horizontal_button_reads_horizontal(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_v(p, b):
        raise AssertionError("Should not be called")
    def fake_r(p, b):
        return "横"
        
    monkeypatch.setattr("custom_gui.app.vertical_ocr_text", fake_v)
    monkeypatch.setattr("custom_gui.app.region_ocr_text", fake_r)
    
    row_3 = app.selections_list.controls[1]
    buttons_row = row_3.content.controls[0].controls[1]
    horizontal_button = buttons_row.controls[2]
    
    horizontal_button.on_click(None)
    
    t, a, k = dummy_page.pending.pop(0)
    t(*a, **k)
    
    assert app.edits["3"] == "横"

def test_4_edited_row_refused(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    app.edits["3"] = "既に直した"
    app._update_selections_ui()
    
    def fake_v(p, b):
        raise AssertionError("Should not be called")
        
    monkeypatch.setattr("custom_gui.app.vertical_ocr_text", fake_v)
    
    row_3 = app.selections_list.controls[1]
    buttons_row = row_3.content.controls[0].controls[1]
    vertical_button = buttons_row.controls[4]
    
    vertical_button.on_click(None)
    
    assert len(dummy_page.pending) == 0
    assert "編集済みの枠は範囲OCRしません" in app.status_text.value
    assert app.edits["3"] == "既に直した"

def test_5_no_text(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_v(p, b):
        return ""
    monkeypatch.setattr("custom_gui.app.vertical_ocr_text", fake_v)
    
    row_3 = app.selections_list.controls[1]
    buttons_row = row_3.content.controls[0].controls[1]
    vertical_button = buttons_row.controls[4]
    
    vertical_button.on_click(None)
    
    t, a, k = dummy_page.pending.pop(0)
    t(*a, **k)
    
    assert "文字が見つかりません" in app.status_text.value
    assert "3" not in app.edits
    row_3_after = app.selections_list.controls[1]
    assert row_3_after.bgcolor is None
    assert app.region_ocr_running[path] == set()

def test_6_error(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_v(p, b):
        raise RuntimeError("boom")
    monkeypatch.setattr("custom_gui.app.vertical_ocr_text", fake_v)
    
    row_3 = app.selections_list.controls[1]
    buttons_row = row_3.content.controls[0].controls[1]
    vertical_button = buttons_row.controls[4]
    
    vertical_button.on_click(None)
    
    t, a, k = dummy_page.pending.pop(0)
    t(*a, **k)
    
    assert "範囲OCR失敗" in app.status_text.value
    row_3_after = app.selections_list.controls[1]
    assert row_3_after.bgcolor is None
    assert app.region_ocr_running[path] == set()

def test_7_same_row_being_edited(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    app.editing_region_id = "3"
    app._update_selections_ui()
    
    def fake_v(p, b):
        return "Q"
    monkeypatch.setattr("custom_gui.app.vertical_ocr_text", fake_v)
    
    row_3 = app.selections_list.controls[1]
    tf = row_3.content.controls[1].controls[0]
    tf.value = "途中"
    
    buttons_row = row_3.content.controls[0].controls[1]
    vertical_button = buttons_row.controls[4]
    
    vertical_button.on_click(None)
    
    t, a, k = dummy_page.pending.pop(0)
    t(*a, **k)
    
    assert "3" not in app.edits
    assert app.selections_list.controls[1] is row_3
    assert row_3.content.controls[1].controls[0] is tf
    assert tf.value == "途中"
    assert "編集中の枠" in app.status_text.value
