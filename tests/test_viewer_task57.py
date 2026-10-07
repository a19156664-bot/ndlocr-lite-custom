import os
import json
import pytest
from PIL import Image
import flet as ft
from unittest.mock import MagicMock

from custom_gui.app import SelectableImageViewer
import custom_gui.work_state as work_state

@pytest.fixture
def real_images(tmp_path):
    img1_path = tmp_path / "img1.png"
    img2_path = tmp_path / "img2.png"
    
    img = Image.new("RGB", (100, 100), color="white")
    img.save(img1_path)
    img.save(img2_path)
    
    return str(img1_path), str(img2_path)

@pytest.fixture
def dummy_page():
    page = MagicMock(spec=ft.Page)
    page.overlay = []
    page.session = MagicMock()
    page.client_storage = MagicMock()
    page.window_width = 800
    page.window_height = 600
    return page

def create_app(image_path, page, monkeypatch):
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", lambda *args, **kwargs: [])
    app = SelectableImageViewer(image_src=image_path, img_w=100, img_h=100, win_w=800, win_h=600)
    app.page = page
    
    original_update = ft.Control.update
    def safe_update(self, *args, **kwargs):
        if not getattr(self, 'page', None) and not getattr(self, '_Control__page', None):
            return
        original_update(self, *args, **kwargs)
        
    monkeypatch.setattr(ft.Control, "update", safe_update)
    
    app.did_mount()
    return app

def draw_rect(app, x1, y1, x2, y2):
    app.mode_state.set_mode("SELECT")
    
    class MockControlEvent:
        def __init__(self, data):
            self.data = data
            self.target = ""
            self.name = ""
            self.control = MagicMock()
            self.page = MagicMock()

    mock_start_event = MockControlEvent(json.dumps({"lx": x1, "ly": y1}))
    start_ev = ft.DragStartEvent(mock_start_event)
    app._on_pan_start(start_ev)
    
    mock_update_event = MockControlEvent(json.dumps({"lx": x2, "ly": y2, "dx": x2-x1, "dy": y2-y1}))
    update_ev = ft.DragUpdateEvent(mock_update_event)
    app._on_pan_update(update_ev)
    
    mock_end_event = MockControlEvent("{}")
    end_ev = ft.DragEndEvent(mock_end_event)
    app._on_pan_end(end_ev)

def pan(app, x1, y1, x2, y2):
    app.mode_state.set_mode("PAN")
    
    class MockControlEvent:
        def __init__(self, data):
            self.data = data
            self.target = ""
            self.name = ""
            self.control = MagicMock()
            self.page = MagicMock()

    mock_start_event = MockControlEvent(json.dumps({"lx": x1, "ly": y1}))
    start_ev = ft.DragStartEvent(mock_start_event)
    app._on_pan_start(start_ev)
    
    mock_update_event = MockControlEvent(json.dumps({"lx": x2, "ly": y2, "dx": x2-x1, "dy": y2-y1}))
    update_ev = ft.DragUpdateEvent(mock_update_event)
    app._on_pan_update(update_ev)
    
    mock_end_event = MockControlEvent("{}")
    end_ev = ft.DragEndEvent(mock_end_event)
    app._on_pan_end(end_ev)

def test_task57_1_2_3_4_5(real_images, dummy_page, monkeypatch):
    img1, img2 = real_images
    work_state.clear_work_state(img1)
    work_state.clear_work_state(img2)

    app = create_app(img1, dummy_page, monkeypatch)
    
    # Precondition 1: pan
    pan(app, 50, 50, 10, 20)
    assert app.image_control.left == -40.0
    assert app.image_control.top == -30.0
    assert app.offset_x == -40.0
    assert app.offset_y == -30.0
    assert app.rects_layer.left == -40.0
    assert app.rects_layer.top == -30.0

    # 2. After 1, app._switch_image(image 2). Then ALL of these are exactly 0.0
    app._switch_image(img2)
    assert app.image_control.left == 0.0
    assert app.image_control.top == 0.0
    assert app.offset_x == 0.0
    assert app.offset_y == 0.0
    assert app.highlight_layer.left == 0.0
    assert app.highlight_layer.top == 0.0
    assert app.rects_layer.left == 0.0
    assert app.rects_layer.top == 0.0
    assert app.inline_editor_layer.left == 0.0
    assert app.inline_editor_layer.top == 0.0

    # 3. After 2, app._switch_image(image 1) (back to the first page)
    app._switch_image(img1)
    assert app.image_control.left == 0.0
    assert app.image_control.top == 0.0
    assert app.rects_layer.left == 0.0
    
    # 4. After 2, pan(app, 50, 50, 30, 40) on image 2 (We switch back to image 2 first since we are on img 1)
    app._switch_image(img2)
    pan(app, 50, 50, 30, 40)
    assert app.image_control.left == -20.0
    assert app.image_control.top == -10.0
    assert app.image_control.left == app.rects_layer.left
    assert app.image_control.top == app.rects_layer.top

    # 5. After 2 (a fresh app is fine: repeat 1 and 2), draw a box
    work_state.clear_work_state(img1)
    work_state.clear_work_state(img2)

    app2 = create_app(img1, dummy_page, monkeypatch)
    pan(app2, 50, 50, 10, 20)
    app2._switch_image(img2)
    
    # ensure it's empty
    for r in list(app2.selection_container.get_all()):
        app2.selection_container.delete_by_id(r.rect_id)
    
    draw_rect(app2, 10, 10, 60, 60)
    rects_app2 = app2.selection_container.get_all()
    assert len(rects_app2) == 1
    bbox2 = rects_app2[0].bbox
    assert app2.image_control.left == app2.offset_x

    app_fresh = create_app(img2, dummy_page, monkeypatch)
    for r in list(app_fresh.selection_container.get_all()):
        app_fresh.selection_container.delete_by_id(r.rect_id)
    
    draw_rect(app_fresh, 10, 10, 60, 60)
    rects_fresh = app_fresh.selection_container.get_all()
    assert len(rects_fresh) == 1
    bbox_fresh = rects_fresh[0].bbox

    for v2, vf in zip(bbox2, bbox_fresh):
        assert abs(v2 - vf) < 1e-6
