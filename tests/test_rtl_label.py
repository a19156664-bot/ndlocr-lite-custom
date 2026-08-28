import pytest
import numpy as np
import cv2
import flet as ft
from unittest.mock import MagicMock
from custom_gui.app import SelectableImageViewer

class DummyPage(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = "test"
        self.window_width = 800
        self.window_height = 600

def make_dummy_page(path, w=400, h=600):
    page = np.full((h, w, 3), 255, dtype=np.uint8)
    cv2.imencode(".jpg", page)[1].tofile(str(path))
    return w, h

def get_app(page, tmp_path):
    path = tmp_path / "test_page.jpg"
    w, h = make_dummy_page(path)
    
    app = SelectableImageViewer(str(path), w, h, 800, 600)
    app.page = page
    app.selections_lock = __import__('threading').Lock()

    app.status_text = ft.Text("")
    app.status_text.page = page

    for name in ("gesture_detector", "highlight_layer", "rects_layer",
                 "inline_editor_layer", "selections_list", "mode_toggle", "controls_row"):
        if hasattr(app, name):
            getattr(app, name).page = page
            
    return app, path

@pytest.fixture
def dummy_page():
    return DummyPage()

def test_11_all_vertical(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path)
    app.ocr_results = [
        {"text": "abc", "is_vertical": True, "bbox": (10, 10, 50, 50)},
        {"text": "def", "is_vertical": True, "bbox": (60, 10, 100, 50)}
    ]
    app.selection_container.add((0, 0, 110, 60))
    app._update_selections_ui()
    
    # Extract label text
    # item_content is ft.Column([ft.Row([ft.Text(...), ...]), content_area])
    # The container `item` has content `item_content`
    label_text_control = app.selections_list.controls[0].content.controls[0].controls[0]
    label_text_control = app.selections_list.controls[0].content.controls[0].controls[0]
    label_text_control = app.selections_list.controls[0].content.controls[0].controls[0]
    label = label_text_control.value
    
    assert "[改行" in label
    assert "横書き" not in label

def test_12_two_horizontal_lines(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path)
    app.ocr_results = [
        {"text": "ab", "is_vertical": False, "bbox": (10, 10, 50, 50)},
        {"text": "cd", "is_vertical": False, "bbox": (60, 10, 100, 50)},
        {"text": "e", "is_vertical": False, "bbox": (110, 10, 150, 50)} # too short, not counted
    ]
    app.selection_container.add((0, 0, 160, 60))
    app._update_selections_ui()
    
    label_text_control = app.selections_list.controls[0].content.controls[0].controls[0]
    label = label_text_control.value
    
    assert "[横書き? 2]" in label

def test_13_marker_order(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path)
    app.ocr_results = [
        {"text": "ab", "is_vertical": False, "bbox": (10, 10, 50, 50)}
    ]
    app.selection_container.add((0, 0, 110, 60))
    app._update_selections_ui()
    
    label_text_control = app.selections_list.controls[0].content.controls[0].controls[0]
    label = label_text_control.value
    
    assert "[横書き? 1]" in label
    assert "[改行" in label
    assert label.index("[横書き? 1]") < label.index("[改行")

def test_14_edited_and_marker(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path)
    app.ocr_results = [
        {"text": "ab", "is_vertical": False, "bbox": (10, 10, 50, 50)}
    ]
    # Add rect
    rect = app.selection_container.add((0, 0, 110, 60))
    # Apply edit
    app.edits[rect.rect_id] = "hello"
    
    app._update_selections_ui()
    
    label_text_control = app.selections_list.controls[0].content.controls[0].controls[0]
    label = label_text_control.value
    
    assert "(edited)" in label
    assert "[横書き? 1]" in label
    assert label.index("(edited)") < label.index("[横書き? 1]")
