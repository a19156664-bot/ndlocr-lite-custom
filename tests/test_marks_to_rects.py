import pytest
import numpy as np
import cv2
import os
import flet as ft
from custom_gui.app import SelectableImageViewer
from custom_gui.selection import SelectionRect

def make_marked_page(path, w=400, h=600):
    page = np.full((h, w, 3), 255, dtype=np.uint8)
    # OpenCV uses BGR, so (255, 235, 60) is Cyan
    page[100:250, 50:300] = (255, 235, 60)     # one cyan box
    cv2.imencode(".jpg", page)[1].tofile(str(path))
    return w, h

def make_two_marks_page(path, w=400, h=600):
    page = np.full((h, w, 3), 255, dtype=np.uint8)
    page[50:150, 50:200] = (255, 235, 60)      # top box
    page[300:400, 50:200] = (255, 235, 60)     # bottom box
    cv2.imencode(".jpg", page)[1].tofile(str(path))
    return w, h

def make_clean_page(path, w=400, h=600):
    page = np.full((h, w, 3), 255, dtype=np.uint8)
    cv2.imencode(".jpg", page)[1].tofile(str(path))
    return w, h

def get_app(page, tmp_path, img_maker):
    path = tmp_path / "test_page.jpg"
    w, h = img_maker(path)
    
    app = SelectableImageViewer(str(path), w, h, 800, 600)
    # mock things that app needs
    app.page = page
    app.selections_lock = __import__('threading').Lock()
    # Mock update status to prevent UI exception
    def mock_update_status():
        pass
    app._update_status = mock_update_status
    
    def mock_update_selections_ui():
        pass
    app._update_selections_ui = mock_update_selections_ui
    
    def mock_persist_work_state():
        pass
    app._persist_work_state = mock_persist_work_state

    return app, path

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
            target(*args, **kwargs)
        window_width = 800
        window_height = 600
        session_id = "test"
    return DummyPage()

def test_1_one_cyan_box(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path, make_marked_page)
    app.selection_container._rects = []
    
    app._on_marks_to_rects_click(None)
    
    rects = app.selection_container.get_all()
    assert len(rects) == 1
    
    x1, y1, x2, y2 = rects[0].bbox
    # The painted box is 50, 100, 300, 250
    assert abs(x1 - 50) <= 8
    assert abs(y1 - 100) <= 8
    assert abs(x2 - 300) <= 8
    assert abs(y2 - 250) <= 8
    
    assert "マークから 1" in app.latest_region_info
    
def test_2_twice_no_duplicate(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path, make_marked_page)
    app.selection_container._rects = []
    
    app._on_marks_to_rects_click(None)
    assert len(app.selection_container.get_all()) == 1
    
    app._on_marks_to_rects_click(None)
    assert len(app.selection_container.get_all()) == 1

def test_3_clean_page(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path, make_clean_page)
    app.selection_container._rects = []
    
    app._on_marks_to_rects_click(None)
    assert len(app.selection_container.get_all()) == 0
    assert "マークが見つかりません" in app.latest_region_info

def test_4_clean_page_preserves_existing(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path, make_clean_page)
    app.selection_container._rects = []
    app.selection_container.add((10, 20, 30, 40))
    app.edits = {"foo": "bar"}
    
    app._on_marks_to_rects_click(None)
    rects = app.selection_container.get_all()
    assert len(rects) == 1
    assert rects[0].bbox == (10, 20, 30, 40)
    assert app.edits == {"foo": "bar"}

def test_5_missing_file_handled(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path, make_clean_page)
    os.remove(path)
    
    app._on_marks_to_rects_click(None)
    assert "読み込めません" in app.latest_region_info

def test_6_two_boxes_ordered(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path, make_two_marks_page)
    app.selection_container._rects = []
    
    app._on_marks_to_rects_click(None)
    rects = app.selection_container.get_all()
    assert len(rects) == 2
    
    # Topmost first: y1 should be ~50, then ~300
    assert abs(rects[0].bbox[1] - 50) <= 8
    assert abs(rects[1].bbox[1] - 300) <= 8

def test_7_button_exists(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path, make_clean_page)
    assert hasattr(app, "btn_marks_to_rects")
    assert app.btn_marks_to_rects in app.controls_row.controls

def test_8_cyan_plus_existing(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path, make_marked_page)
    app.selection_container._rects = []
    app.selection_container.add((10, 20, 30, 40))
    
    app._on_marks_to_rects_click(None)
    rects = app.selection_container.get_all()
    assert len(rects) == 2
    
    assert rects[0].bbox == (10, 20, 30, 40)

