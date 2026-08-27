import pytest
import flet as ft
from unittest.mock import MagicMock
from PIL import Image

from custom_gui.selection import SelectionRect, find_region_at_point
from custom_gui.app import SelectableImageViewer

@pytest.fixture
def dummy_image(tmp_path):
    img_path = tmp_path / "test_image.jpg"
    img = Image.new("RGB", (1000, 1000), color="white")
    img.save(img_path)
    return str(img_path)

@pytest.fixture
def viewer(dummy_image, monkeypatch):
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", lambda x, y: [])
    page = MagicMock()
    page.width = 800
    page.height = 600
    app_viewer = SelectableImageViewer(
        image_src=dummy_image,
        img_w=1000,
        img_h=1000,
        win_w=800,
        win_h=600
    )
    app_viewer.page = page
    
    app_viewer.gesture_detector.page = page
    app_viewer.mode_toggle.page = page
    app_viewer.status_text = ft.Text("Mode: SELECT")
    app_viewer.status_text.page = page
    app_viewer.highlight_layer.page = page
    app_viewer.rects_layer.page = page
    app_viewer.inline_editor_layer.page = page
    app_viewer.selections_list.page = page

    return app_viewer

def create_tap_event(x, y):
    e = MagicMock()
    e.data = f'{{"lx": {x}, "ly": {y}}}'
    return ft.TapEvent(e)

def create_drag_start(x, y):
    e = MagicMock()
    e.data = f'{{"lx": {x}, "ly": {y}}}'
    return ft.DragStartEvent(e)

def create_drag_update(x, y, dx, dy):
    e = MagicMock()
    e.data = f'{{"lx": {x}, "ly": {y}, "dx": {dx}, "dy": {dy}}}'
    return ft.DragUpdateEvent(e)

def create_drag_end():
    e = MagicMock()
    e.data = '{"vx": 0, "vy": 0}'
    return ft.DragEndEvent(e)

# Tests for find_region_at_point (DoD-1)

def test_find_region_at_point_inside():
    # DoD-1 a
    rects = [SelectionRect("1", (10, 10, 50, 50), "Region 1")]
    rid = find_region_at_point(30, 30, rects, 1.0, 0, 0)
    assert rid == "1"

def test_find_region_at_point_outside():
    # DoD-1 b
    rects = [SelectionRect("1", (10, 10, 50, 50), "Region 1")]
    rid = find_region_at_point(100, 100, rects, 1.0, 0, 0)
    assert rid is None

def test_find_region_at_point_empty_list():
    # DoD-1 c
    rid = find_region_at_point(30, 30, [], 1.0, 0, 0)
    assert rid is None

def test_find_region_at_point_overlapping_smaller_area():
    # DoD-1 d
    rects = [
        SelectionRect("1", (10, 10, 100, 100), "Region 1"),
        SelectionRect("2", (30, 30, 60, 60), "Region 2")
    ]
    rid = find_region_at_point(40, 40, rects, 1.0, 0, 0)
    assert rid == "2"

def test_find_region_at_point_exact_boundary():
    # DoD-1 e
    rects = [SelectionRect("1", (10, 10, 50, 50), "Region 1")]
    rid = find_region_at_point(10, 10, rects, 1.0, 0, 0)
    assert rid == "1"
    
    rid = find_region_at_point(50, 50, rects, 1.0, 0, 0)
    assert rid == "1"
    
    rid = find_region_at_point(30, 10, rects, 1.0, 0, 0)
    assert rid == "1"

def test_find_region_at_point_zero_scale():
    # DoD-1 f
    rects = [SelectionRect("1", (0, 0, 50, 50), "Region 1")]
    # display_to_original returns (0, 0) for scale 0
    rid = find_region_at_point(100, 100, rects, 0.0, 0, 0)
    assert rid == "1"

# Tests for _on_tap_up handler

def test_handler_select_tap_inside(viewer):
    # DoD-2 case 6
    assert viewer.mode_state.current == "SELECT"
    viewer.zoom_scale = 1.0
    viewer.offset_x = 0
    viewer.offset_y = 0
    viewer.selection_container.add((10, 10, 50, 50))
    rect_id = viewer.selection_container.get_all()[0].rect_id
    
    event = create_tap_event(30, 30)
    viewer._on_tap_up(event)
    
    assert viewer.inline_editing_region_id == rect_id
    assert viewer.active_region_id == rect_id

def test_handler_pan_tap_inside(viewer):
    # DoD-2 case 7
    viewer.mode_state.set_mode("PAN")
    assert viewer.mode_state.current == "PAN"
    
    viewer.selection_container.add((10, 10, 50, 50))
    rect_id = viewer.selection_container.get_all()[0].rect_id
    
    viewer.inline_editing_region_id = None
    
    event = create_tap_event(30, 30)
    viewer._on_tap_up(event)
    
    assert viewer.inline_editing_region_id is None

def test_handler_select_tap_empty_space_preserves_editor(viewer):
    # DoD-2 case 8
    assert viewer.mode_state.current == "SELECT"
    
    viewer.selection_container.add((10, 10, 50, 50))
    rect_id = viewer.selection_container.get_all()[0].rect_id
    
    # Open the editor artificially
    viewer.inline_editing_region_id = rect_id
    viewer.active_region_id = rect_id
    
    # Tap outside
    event = create_tap_event(100, 100)
    viewer._on_tap_up(event)
    
    assert viewer.inline_editing_region_id == rect_id
    assert viewer.active_region_id == rect_id

def test_drag_still_creates_and_opens_editor(viewer):
    # DoD-2 case 9
    assert viewer.mode_state.current == "SELECT"
    
    start_event = create_drag_start(10, 10)
    viewer.gesture_detector.on_pan_start(start_event)
    
    update_event = create_drag_update(50, 50, 40, 40)
    viewer.gesture_detector.on_pan_update(update_event)
    
    end_event = create_drag_end()
    viewer.gesture_detector.on_pan_end(end_event)
    
    rects = viewer.selection_container.get_all()
    assert len(rects) == 1
    rect_id = rects[0].rect_id
    
    assert viewer.inline_editing_region_id == rect_id
