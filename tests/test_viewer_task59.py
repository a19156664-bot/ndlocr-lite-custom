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

def test_1_start_color_and_same_objects(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    row_2_before = app.selections_list.controls[0]
    row_3_before = app.selections_list.controls[1]
    
    app.start_region_ocr("3")
    
    assert row_3_before.bgcolor == ft.Colors.ORANGE_100
    assert row_2_before.bgcolor is None
    assert app.selections_list.controls[0] is row_2_before
    assert app.selections_list.controls[1] is row_3_before

def test_2_thread_success(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_region_ocr_text(p, b):
        return "X\nY"
    monkeypatch.setattr("custom_gui.app.region_ocr_text", fake_region_ocr_text)
    
    row_2_before = app.selections_list.controls[0]
    
    app.start_region_ocr("3")
    t, a, k = dummy_page.pending.pop(0)
    t(*a, **k)
    
    assert app.edits["3"] == "X\nY"
    
    row_3_after = app.selections_list.controls[1]
    assert row_3_after.bgcolor is None
    
    # check new row content
    header_text = row_3_after.content.controls[0].controls[0].value
    assert "(edited)" in header_text
    assert "[改行 1]" in header_text
    
    content_area = row_3_after.content.controls[1]
    assert content_area.value == "X\nY"
    
    buttons_row = row_3_after.content.controls[0].controls[1]
    tooltips = [b.tooltip for b in buttons_row.controls if hasattr(b, "tooltip")]
    assert "Revert to OCR" in tooltips
    
    # row 2 unchanged
    assert app.selections_list.controls[0] is row_2_before

def test_3_typing_kept(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_region_ocr_text(p, b):
        return "Z"
    monkeypatch.setattr("custom_gui.app.region_ocr_text", fake_region_ocr_text)
    
    app.editing_region_id = "2"
    app._update_selections_ui()
    
    row_2 = app.selections_list.controls[0]
    tf = row_2.content.controls[1].controls[0]
    tf.value = "途中の入力"
    
    app.start_region_ocr("3")
    t, a, k = dummy_page.pending.pop(0)
    t(*a, **k)
    
    assert app.selections_list.controls[0] is row_2
    assert row_2.content.controls[1].controls[0] is tf
    assert tf.value == "途中の入力"
    assert app.editing_region_id == "2"
    assert app.edits["3"] == "Z"

def test_4_no_text(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_region_ocr_text(p, b):
        return ""
    monkeypatch.setattr("custom_gui.app.region_ocr_text", fake_region_ocr_text)
    
    row_2_before = app.selections_list.controls[0]
    row_3_before = app.selections_list.controls[1]
    
    app.start_region_ocr("3")
    t, a, k = dummy_page.pending.pop(0)
    t(*a, **k)
    
    assert row_3_before.bgcolor is None
    assert "3" not in app.edits
    assert "文字が見つかりません" in app.status_text.value
    assert app.selections_list.controls[0] is row_2_before
    assert app.selections_list.controls[1] is row_3_before

def test_5_error(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_region_ocr_text(p, b):
        raise RuntimeError("boom")
    monkeypatch.setattr("custom_gui.app.region_ocr_text", fake_region_ocr_text)
    
    row_3_before = app.selections_list.controls[1]
    
    app.start_region_ocr("3")
    t, a, k = dummy_page.pending.pop(0)
    t(*a, **k)
    
    assert row_3_before.bgcolor is None
    assert "範囲OCR失敗" in app.status_text.value
    assert app.region_ocr_running[path] == set()

def test_6_page_switched(dummy_page, tmp_path, monkeypatch):
    from PIL import Image
    from unittest.mock import MagicMock
    app, path_one = get_prepared_app(dummy_page, tmp_path)
    
    # mock buttons so _switch_image works without crashing
    app.btn_prev = MagicMock()
    app.btn_next = MagicMock()
    app.nav_text = MagicMock()
    app.image_container = MagicMock()
    app.status_row = MagicMock()
    # We must not mock app.page entirely, just ensure it works
    
    path_two = str(tmp_path / "two.png")
    Image.new("RGB", (100, 100)).save(path_two)
    
    def fake_region_ocr_text(p, b):
        return "Q"
    monkeypatch.setattr("custom_gui.app.region_ocr_text", fake_region_ocr_text)
    
    app.start_region_ocr("3")
    app._switch_image(path_two)
    
    t, a, k = dummy_page.pending.pop(0)
    t(*a, **k)
    
    assert "3" not in app.image_states[path_one].get("edits", {})
    assert app.region_ocr_running[path_one] == set()
    
    app._switch_image(path_one)
    row_3 = app.selections_list.controls[1]
    assert row_3.bgcolor is None

def test_7_rebuild_while_running(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_region_ocr_text(p, b):
        return "M"
    monkeypatch.setattr("custom_gui.app.region_ocr_text", fake_region_ocr_text)
    
    app.start_region_ocr("3")
    
    # Simulate a full rebuild (e.g. from resize)
    app._update_selections_ui()
    
    new_row_3 = app.selections_list.controls[1]
    assert new_row_3.bgcolor == ft.Colors.ORANGE_100
    
    t, a, k = dummy_page.pending.pop(0)
    t(*a, **k)
    
    # Since refresh_row replaces the row entirely, we must get it again
    new_new_row_3 = app.selections_list.controls[1]
    assert new_new_row_3.bgcolor is None

def test_8_same_row_being_edited(dummy_page, tmp_path, monkeypatch):
    app, path = get_prepared_app(dummy_page, tmp_path)
    
    def fake_region_ocr_text(p, b):
        return "Q"
    monkeypatch.setattr("custom_gui.app.region_ocr_text", fake_region_ocr_text)
    
    app.editing_region_id = "3"
    app._update_selections_ui()
    
    row_3 = app.selections_list.controls[1]
    tf = row_3.content.controls[1].controls[0]
    tf.value = "途中"
    
    app.start_region_ocr("3")
    t, a, k = dummy_page.pending.pop(0)
    t(*a, **k)
    
    assert "3" not in app.edits
    assert app.selections_list.controls[1] is row_3
    assert row_3.content.controls[1].controls[0] is tf
    assert tf.value == "途中"
    assert "編集中の枠" in app.status_text.value
    assert row_3.bgcolor is None
