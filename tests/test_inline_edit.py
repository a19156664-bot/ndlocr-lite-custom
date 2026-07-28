import pytest
import os
import flet as ft
from unittest.mock import patch, MagicMock

import custom_gui.app as app_module
from custom_gui.app import SelectableImageViewer

@pytest.fixture
def fake_image_path(tmp_path):
    from PIL import Image
    img = Image.new("RGB", (800, 600), color="white")
    path = tmp_path / "test_image.jpg"
    img.save(path)
    return str(path)

@pytest.fixture
def mock_ocr():
    with patch("custom_gui.app.run_ocr_and_parse") as mock_run:
        mock_run.return_value = [
            {"text": "Hello World", "bbox": (10, 10, 100, 30), "confidence": 0.99, "is_vertical": False, "source_image": "test.jpg"},
            {"text": "Second Line", "bbox": (10, 40, 100, 60), "confidence": 0.95, "is_vertical": False, "source_image": "test.jpg"}
        ]
        yield mock_run

def setup_viewer(fake_image_path):
    viewer = SelectableImageViewer(
        image_src=fake_image_path,
        img_w=800,
        img_h=600,
        win_w=1000,
        win_h=800
    )
    
    def patch_update(control):
        control.update = MagicMock()
        
    viewer.page = MagicMock()
    viewer.status_row.update = MagicMock()
    viewer.status_text.update = MagicMock()
    viewer.progress_ring.update = MagicMock()
    viewer.highlight_layer.update = MagicMock()
    viewer.rects_layer.update = MagicMock()
    viewer.inline_editor_layer.update = MagicMock()
    viewer.selections_list.update = MagicMock()
    viewer.image_container.update = MagicMock()
    return viewer

def simulate_drag(viewer, start, end):
    viewer.mode_state.current = "SELECT"
    
    # Start pan
    e_start = MagicMock(spec=ft.DragStartEvent)
    e_start.local_x, e_start.local_y = start
    viewer._on_pan_start(e_start)
    
    # Update pan
    e_update = MagicMock(spec=ft.DragUpdateEvent)
    e_update.local_x, e_update.local_y = end
    viewer._on_pan_update(e_update)
    
    # End pan
    e_end = MagicMock(spec=ft.DragEndEvent)
    viewer._on_pan_end(e_end)

def test_a_draw_rectangle_opens_editor(fake_image_path, mock_ocr):
    viewer = setup_viewer(fake_image_path)
    viewer._on_ocr_complete(mock_ocr.return_value, None)
    
    simulate_drag(viewer, (5, 5), (105, 35))
    
    assert viewer.inline_editing_region_id is not None
    assert len(viewer.inline_editor_layer.controls) == 1
    
    editor_container = viewer.inline_editor_layer.controls[0]
    tf = editor_container.content
    assert isinstance(tf, ft.TextField)
    assert "Hello World" in tf.value

def test_b_zero_area_drag_no_editor(fake_image_path, mock_ocr):
    viewer = setup_viewer(fake_image_path)
    simulate_drag(viewer, (10, 10), (10, 10))
    
    assert viewer.inline_editing_region_id is None
    assert len(viewer.inline_editor_layer.controls) == 0

def test_c_on_submit_commits(fake_image_path, mock_ocr):
    viewer = setup_viewer(fake_image_path)
    viewer._on_ocr_complete(mock_ocr.return_value, None)
    
    simulate_drag(viewer, (5, 5), (105, 35))
    rid = viewer.inline_editing_region_id
    tf = viewer.inline_editor_layer.controls[0].content
    
    tf.value = "Corrected Text"
    tf.on_submit(MagicMock())
    
    assert viewer.inline_editing_region_id is None
    assert len(viewer.inline_editor_layer.controls) == 0
    assert viewer.edits[rid] == "Corrected Text"
    
    viewer._update_selections_ui()
    found = False
    for item in viewer.selections_list.controls:
        column = item.content
        content_area = column.controls[1]
        if isinstance(content_area, ft.Text) and content_area.value == "Corrected Text":
            found = True
    assert found

def test_d_update_selections_ui_preserves_editor(fake_image_path, mock_ocr):
    viewer = setup_viewer(fake_image_path)
    viewer._on_ocr_complete(mock_ocr.return_value, None)
    
    simulate_drag(viewer, (5, 5), (105, 35))
    tf = viewer.inline_editor_layer.controls[0].content
    tf.value = "Modified Before OCR Update"
    
    viewer._update_selections_ui()
    
    assert viewer.inline_editing_region_id is not None
    assert len(viewer.inline_editor_layer.controls) == 1
    tf_after = viewer.inline_editor_layer.controls[0].content
    assert tf_after.value == "Modified Before OCR Update"

def test_e_escape_and_blur_discard(fake_image_path, mock_ocr):
    viewer = setup_viewer(fake_image_path)
    viewer._on_ocr_complete(mock_ocr.return_value, None)
    
    viewer.selection_container.add((0, 0, 100, 100))
    rid = viewer.selection_container.get_all()[0].rect_id
    viewer.edits[rid] = "Pre-existing edit"
    
    simulate_drag(viewer, (5, 5), (105, 35))
    new_rid = viewer.inline_editing_region_id
    tf = viewer.inline_editor_layer.controls[0].content
    tf.value = "Draft Text"
    
    tf.on_blur(MagicMock())
    
    assert viewer.inline_editing_region_id is None
    assert new_rid not in viewer.edits
    assert viewer.edits[rid] == "Pre-existing edit"
    assert len(viewer.selection_container.get_all()) == 2

def test_f_inline_editor_layer_order(fake_image_path, mock_ocr):
    viewer = setup_viewer(fake_image_path)
    
    controls = viewer.stack.controls
    
    gesture_idx = controls.index(viewer.gesture_detector)
    editor_idx = controls.index(viewer.inline_editor_layer)
    
    assert editor_idx > gesture_idx, "inline_editor_layer must be AFTER gesture_detector"

def test_g_offset_test(fake_image_path, mock_ocr):
    viewer = setup_viewer(fake_image_path)
    
    viewer.mode_state.current = "PAN"
    viewer.offset_x = 50.0
    viewer.offset_y = 60.0
    
    simulate_drag(viewer, (100, 100), (200, 200))
    
    editor_container = viewer.inline_editor_layer.controls[0]
    
    assert viewer.inline_editor_layer.left == 50.0
    assert viewer.inline_editor_layer.top == 60.0
    
    assert editor_container.left == 100.0 - 50.0
    assert editor_container.top == 200.0 - 60.0

def test_h_concurrent_update(fake_image_path, mock_ocr):
    viewer = setup_viewer(fake_image_path)
    
    import threading
    exceptions = []
    
    def worker():
        try:
            viewer._update_selections_ui()
            viewer._update_inline_editor()
        except Exception as e:
            exceptions.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=2.0)
        
    if exceptions:
        raise exceptions[0]

def test_i_right_panel_commit_works(fake_image_path, mock_ocr):
    viewer = setup_viewer(fake_image_path)
    viewer._on_ocr_complete(mock_ocr.return_value, None)
    
    simulate_drag(viewer, (5, 5), (105, 35))
    rid = viewer.inline_editing_region_id
    
    viewer._cancel_inline_edit()
    
    viewer.active_region_id = rid
    viewer.editing_region_id = rid
    viewer._update_selections_ui()
    
    tf = None
    for item in viewer.selections_list.controls:
        column = item.content
        content_area = column.controls[1]
        if isinstance(content_area, ft.Column):
            tf = content_area.controls[0]
            break
            
    assert tf is not None
    tf.value = "Panel Edit"
    
    tf.on_submit(MagicMock())
    
    assert viewer.edits[rid] == "Panel Edit"

