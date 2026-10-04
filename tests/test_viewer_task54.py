import pytest
from pytest import approx
import flet as ft
from custom_gui.app import SelectableImageViewer
from custom_gui.selection import SelectionRect
from custom_gui.break_marks import BREAK_MARK
import custom_gui.work_state as work_state
import json

@pytest.fixture
def dummy_page():
    class DummyPage:
        def __init__(self):
            self.overlay = []
            self.controls = []
            self.width = 800
            self.height = 600
        def update(self, *args, **kwargs):
            pass
        def run_thread(self, target, *args, **kwargs):
            target(*args, **kwargs)
        def close(self, dialog):
            pass
        def open(self, dialog):
            pass
    return DummyPage()

def get_app(dummy_page):
    import threading
    app = SelectableImageViewer(
        image_src="dummy.dat",
        img_w=1000, img_h=1000,
        win_w=1000, win_h=1000
    )
    app.selections_lock = threading.RLock()
    app.page = dummy_page
    
    from unittest.mock import MagicMock
    app.selections_list.update = MagicMock()
    app.highlight_layer.update = MagicMock()
    app.rects_layer.update = MagicMock()
    app.inline_editor_layer.update = MagicMock()
    app.gesture_detector.update = MagicMock()
    if hasattr(app, 'mark_label'):
        app.mark_label.update = MagicMock()
        
    return app

def test_zoom_a(dummy_page):
    app = get_app(dummy_page)
    app.selection_container.restore([
        SelectionRect(rect_id="1", bbox=(0, 0, 10, 10), label="Region 1"),
        SelectionRect(rect_id="2", bbox=(100, 200, 300, 400), label="Region 2")
    ])
    app.ocr_results = []
    
    app._update_selections_ui()
    s0 = app.zoom_scale
    
    app.zoom_in(None)
    assert len(app.rects_layer.controls) == 4
    
    c2 = app.rects_layer.controls[2]
    assert c2.left == approx(100 * s0 * 1.2)
    assert c2.top == approx(200 * s0 * 1.2)
    assert c2.width == approx(200 * s0 * 1.2)
    
    app.zoom_out(None)
    c2 = app.rects_layer.controls[2]
    assert c2.left == approx(100 * s0)
    
    app.fit(None)
    c2 = app.rects_layer.controls[2]
    assert c2.left == approx(100 * app.zoom_scale)
    
    app.editing_region_id = "2"
    app._update_selections_ui()
    
    row2 = app.selections_list.controls[1]
    content_area = row2.content.controls[1]
    tf = content_area.controls[0]
    
    before_list = list(app.selections_list.controls)
    
    app.zoom_in(None)
    
    row2_after = app.selections_list.controls[1]
    tf_after = row2_after.content.controls[1].controls[0]
    
    assert tf_after is tf
    assert all(a is b for a, b in zip(before_list, app.selections_list.controls))
    assert len(before_list) == len(app.selections_list.controls)
    
    before_rects = list(app.rects_layer.controls)
    app._update_viewer()
    assert all(a is b for a, b in zip(before_rects, app.rects_layer.controls))
    assert len(before_rects) == len(app.rects_layer.controls)

def test_region_1_b_lime(dummy_page, monkeypatch):
    monkeypatch.setenv("NDLOCR_MARK_COLOR", "lime")
    app = get_app(dummy_page)
    app.selection_container.restore([
        SelectionRect(rect_id="1", bbox=(0, 0, 1000, 1000), label="Region 1"),
        SelectionRect(rect_id="2", bbox=(100, 200, 300, 400), label="Region 2")
    ])
    app.ocr_results = [
        {"bbox": (10, 10, 50, 50), "text": "Line P", "confidence": 0.9, "is_vertical": False, "source_image": "dummy.dat"},
        {"bbox": (150, 250, 200, 300), "text": "Line Q", "confidence": 0.9, "is_vertical": False, "source_image": "dummy.dat"}
    ]
    app._update_selections_ui()
    
    assert len(app.highlight_layer.controls) == 1
    
    hl = app.highlight_layer.controls[0]
    assert hl.left == approx(150 * app.zoom_scale)
    assert hl.top == approx(250 * app.zoom_scale)
    
    assert len(app.rects_layer.controls) >= 2
    r1_border = app.rects_layer.controls[0]
    r1_label = app.rects_layer.controls[1]
    
    assert r1_label.content.value == "Region 1"
    
    row1 = app.selections_list.controls[0]
    text1 = row1.content.controls[1].value
    assert "Line P\nLine Q" == text1 or "Line P" in text1 and "Line Q" in text1
    
    app.selection_container.restore([
        SelectionRect(rect_id="2", bbox=(0, 0, 100, 100), label="Region 2"),
        SelectionRect(rect_id="3", bbox=(100, 200, 300, 400), label="Region 3")
    ])
    app._update_selections_ui()
    assert len(app.highlight_layer.controls) == 2

def test_region_1_b_cyan(dummy_page, monkeypatch):
    monkeypatch.delenv("NDLOCR_MARK_COLOR", raising=False)
    app = get_app(dummy_page)
    app.selection_container.restore([
        SelectionRect(rect_id="1", bbox=(0, 0, 1000, 1000), label="Region 1"),
        SelectionRect(rect_id="2", bbox=(100, 200, 300, 400), label="Region 2")
    ])
    app.ocr_results = [
        {"bbox": (10, 10, 50, 50), "text": "Line P", "confidence": 0.9, "is_vertical": False, "source_image": "dummy.dat"},
        {"bbox": (150, 250, 200, 300), "text": "Line Q", "confidence": 0.9, "is_vertical": False, "source_image": "dummy.dat"}
    ]
    app._update_selections_ui()
    
    assert len(app.highlight_layer.controls) == 3

def test_layout_c(dummy_page):
    app = get_app(dummy_page)
    app.selection_container.restore([
        SelectionRect(rect_id="1", bbox=(0, 0, 10, 10), label="Region 1")
    ])
    app._update_selections_ui()
    
    row1 = app.selections_list.controls[0]
    outer_row = row1.content.controls[0]
    assert isinstance(outer_row, ft.Row)
    assert outer_row.wrap == True
    assert len(outer_row.controls) == 2
    
    text_control = outer_row.controls[0]
    assert isinstance(text_control, ft.Text)
    assert text_control.value.startswith("Region 1")
    
    buttons_row = outer_row.controls[1]
    assert isinstance(buttons_row, ft.Row)
    tooltips = [b.tooltip for b in buttons_row.controls]
    assert "Edit" in tooltips
    assert "右から変換" in tooltips
    assert "この枠だけOCR" in tooltips
    assert "Delete" in tooltips

class FakeEvent:
    def __init__(self, control):
        self.control = control

def test_break_marks_d(dummy_page, tmp_path):
    app = get_app(dummy_page)
    
    app.selection_container.restore([
        SelectionRect(rect_id="2", bbox=(0, 0, 10, 10), label="Region 2")
    ])
    app.edits["2"] = "あ\nい\nう"
    app.editing_region_id = "2"
    app._update_selections_ui()
    
    row = app.selections_list.controls[0]
    header = row.content.controls[0].controls[0]
    tf = row.content.controls[1].controls[0]
    
    assert tf.value == f"あ{BREAK_MARK}\nい{BREAK_MARK}\nう"
    assert "[改行 2]" in header.value
    
    tf.value = f"あ{BREAK_MARK}\nいう"
    e = FakeEvent(tf)
    tf.on_change(e)
    assert "[改行 1]" in header.value
    
    tf.value = f"あ{BREAK_MARK}\nい\nう\nえ"
    tf.on_change(e)
    assert "[改行 3]" in header.value
    
    tf2 = app.selections_list.controls[0].content.controls[1].controls[0]
    assert tf is tf2
    assert tf.value == f"あ{BREAK_MARK}\nい\nう\nえ"
    
    tf.value = f"あ{BREAK_MARK}\nい{BREAK_MARK}うえ"
    save_btn = row.content.controls[1].controls[1].controls[0] # save button
    save_btn.on_click(FakeEvent(save_btn))
    
    assert app.edits["2"] == "あ\nいうえ"
    
    app.image_src = str(tmp_path / "dummy.dat")
    app._persist_work_state()
    ws = work_state.load_work_state(app.image_src)
    assert BREAK_MARK not in json.dumps(ws)
    
    app.editing_region_id = "2"
    app.edits["2"] = "あ\nい\nう"
    app._update_selections_ui()
    
    row = app.selections_list.controls[0]
    tf = row.content.controls[1].controls[0]
    tf.value = f"あ{BREAK_MARK}\nい{BREAK_MARK}うえ"
    
    tf.on_submit(FakeEvent(tf))
    assert app.edits["2"] == "あ\nいうえ"
    
    app.editing_region_id = "2"
    app.edits["2"] = "あ\nい\nう"
    app._update_selections_ui()
    
    row = app.selections_list.controls[0]
    tf = row.content.controls[1].controls[0]
    tf.value = f"あ{BREAK_MARK}\nい{BREAK_MARK}うええええ"
    
    cancel_btn = row.content.controls[1].controls[1].controls[1] # cancel button
    cancel_btn.on_click(FakeEvent(cancel_btn))
    
    assert app.edits["2"] == "あ\nい\nう"
    
    app.edits["2"] = "あ\nいうえ"
    app._update_selections_ui()
    row = app.selections_list.controls[0]
    text_display = row.content.controls[1]
    header = row.content.controls[0].controls[0]
    
    assert isinstance(text_display, ft.Text)
    assert text_display.value == "あ\nいうえ"
    assert BREAK_MARK not in text_display.value
    assert "[改行 1]" in header.value

