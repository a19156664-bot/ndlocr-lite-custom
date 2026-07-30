import pytest
import flet as ft
from unittest.mock import MagicMock
from PIL import Image
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

def create_control_event():
    return ft.ControlEvent(target="", name="secondary_tap", data="", control=MagicMock(), page=MagicMock())

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

def test_a_right_click_wired(viewer):
    assert viewer.gesture_detector.on_secondary_tap is not None
    assert viewer.gesture_detector.on_secondary_tap_down is None
    assert viewer.gesture_detector.on_secondary_tap_up is None

def test_b_toggle_mode(viewer):
    assert viewer.mode_state.current == "SELECT"
    assert viewer.mode_toggle.selected == {"SELECT"}

    # First right click
    viewer.gesture_detector.on_secondary_tap(create_control_event())
    assert viewer.mode_state.current == "PAN"
    assert viewer.mode_toggle.selected == {"PAN"}

    # Second right click
    viewer.gesture_detector.on_secondary_tap(create_control_event())
    assert viewer.mode_state.current == "SELECT"
    assert viewer.mode_toggle.selected == {"SELECT"}

def test_c_cursor_updates(viewer):
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.PRECISE

    # First right click
    viewer.gesture_detector.on_secondary_tap(create_control_event())
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.CLICK

    # Second right click
    viewer.gesture_detector.on_secondary_tap(create_control_event())
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.PRECISE

def test_d_pan_mode_drag(viewer):
    # Setup PAN mode
    viewer.gesture_detector.on_secondary_tap(create_control_event())
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.CLICK

    # Drag start
    start_event = create_drag_start(100, 100)
    viewer.gesture_detector.on_pan_start(start_event)
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.ALL_SCROLL

    # Drag update
    update_event = create_drag_update(150, 120, 50, 20)
    viewer.gesture_detector.on_pan_update(update_event)
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.ALL_SCROLL
    assert viewer.offset_x == 50
    assert viewer.offset_y == 20

    # Drag end
    end_event = create_drag_end()
    viewer.gesture_detector.on_pan_end(end_event)
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.CLICK
    assert viewer.offset_x == 50
    assert viewer.offset_y == 20

def test_e_select_mode_drag(viewer):
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.PRECISE
    
    # Start dragging in SELECT mode to create rect
    start_event = create_drag_start(10, 10)
    viewer.gesture_detector.on_pan_start(start_event)
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.PRECISE
    
    # Update dragging
    update_event = create_drag_update(30, 30, 20, 20)
    viewer.gesture_detector.on_pan_update(update_event)
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.PRECISE
    
    # End dragging
    end_event = create_drag_end()
    viewer.gesture_detector.on_pan_end(end_event)
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.PRECISE
    
    assert len(viewer.selection_container.get_all()) == 1

def test_f_right_click_does_not_destroy_state(viewer):
    # Add a rectangle
    start_event = create_drag_start(10, 10)
    viewer.gesture_detector.on_pan_start(start_event)
    update_event = create_drag_update(30, 30, 20, 20)
    viewer.gesture_detector.on_pan_update(update_event)
    end_event = create_drag_end()
    viewer.gesture_detector.on_pan_end(end_event)
    
    assert len(viewer.selection_container.get_all()) == 1
    rect_id = viewer.selection_container.get_all()[0].rect_id
    
    # Add an edit
    viewer.edits[rect_id] = "Test Edit"
    
    zoom_before = viewer.zoom_scale
    
    # Right click
    viewer.gesture_detector.on_secondary_tap(create_control_event())
    
    assert len(viewer.selection_container.get_all()) == 1
    assert viewer.edits.get(rect_id) == "Test Edit"
    assert viewer.zoom_scale == zoom_before

def test_g_toolbar_toggle_refreshes_cursor(viewer):
    class DummyControl:
        def __init__(self, selected):
            self.selected = selected
    
    class DummyEvent:
        def __init__(self, selected):
            self.control = DummyControl(selected)
            
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.PRECISE
    viewer._on_mode_change(DummyEvent({"PAN"}))
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.CLICK

def test_h_full_cycle_real_handlers(viewer):
    # (a) full cycle driven through the REAL handlers:
    # start in SELECT and assert PRECISE
    assert viewer.mode_state.current == "SELECT"
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.PRECISE
    
    # fire `_toggle_mode` (the right-click handler) and assert CLICK
    viewer.gesture_detector.on_secondary_tap(create_control_event())
    assert viewer.mode_state.current == "PAN"
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.CLICK
    
    # fire `_on_pan_start` and assert ALL_SCROLL
    start_event = create_drag_start(100, 100)
    viewer.gesture_detector.on_pan_start(start_event)
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.ALL_SCROLL
    
    # fire `_on_pan_end` and assert CLICK again
    end_event = create_drag_end()
    viewer.gesture_detector.on_pan_end(end_event)
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.CLICK
    
    # fire `_toggle_mode` and assert PRECISE
    viewer.gesture_detector.on_secondary_tap(create_control_event())
    assert viewer.mode_state.current == "SELECT"
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.PRECISE

def test_i_select_mode_drag_keeps_precise(viewer):
    # (b) dragging in SELECT mode keeps PRECISE - `_on_pan_start` must not
    # turn a Select drag into a pan cursor.
    assert viewer.mode_state.current == "SELECT"
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.PRECISE
    
    # Drag start
    start_event = create_drag_start(10, 10)
    viewer.gesture_detector.on_pan_start(start_event)
    assert viewer.gesture_detector.mouse_cursor == ft.MouseCursor.PRECISE
