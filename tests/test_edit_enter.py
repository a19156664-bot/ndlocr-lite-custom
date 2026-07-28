import pytest
from unittest.mock import patch, MagicMock
import flet as ft
from custom_gui.app import SelectableImageViewer
from custom_gui.selection import SelectionRect
from PIL import Image
import os

class DummyEvent:
    def __init__(self, control=None):
        self.control = control

@pytest.fixture
@patch('custom_gui.app.run_ocr_and_parse', return_value=[])
def dummy_app(mock_ocr, tmp_path):
    img_path = tmp_path / "dummy.png"
    Image.new('RGB', (100, 100)).save(img_path)
    
    app = SelectableImageViewer(str(img_path), 100, 100, 800, 600)
    app.page = MagicMock()
    app.current_image_path = str(img_path)
    
    app.selections_list.update = MagicMock()
    app.highlight_layer.update = MagicMock()
    app.rects_layer.update = MagicMock()
    if hasattr(app, 'right_panel'):
        app.right_panel.update = MagicMock()
        
    return app

def find_editing_controls(app):
    for c in app.selections_list.controls:
        col = c.content
        # col: ft.Column([ft.Row([Text, Row(buttons)]), content_area])
        if isinstance(col, ft.Column) and len(col.controls) > 1:
            content_area = col.controls[1]
            if isinstance(content_area, ft.Column):
                if len(content_area.controls) == 2:
                    tf = content_area.controls[0]
                    btn_row = content_area.controls[1]
                    if isinstance(tf, ft.TextField) and isinstance(btn_row, ft.Row):
                        if len(btn_row.controls) >= 2:
                            save_btn = btn_row.controls[0]
                            cancel_btn = btn_row.controls[1]
                            return tf, save_btn, cancel_btn
    return None, None, None

def test_a_textfield_properties(dummy_app):
    dummy_app.selection_container.add((10, 10, 50, 50))
    rect_id = dummy_app.selection_container.get_all()[0].rect_id
    
    dummy_app.editing_region_id = rect_id
    dummy_app._update_selections_ui()
    
    tf, save_btn, cancel_btn = find_editing_controls(dummy_app)
    assert tf is not None
    assert tf.multiline is True
    assert getattr(tf, 'shift_enter', False) is True
    assert getattr(tf, 'on_submit', None) is not None

def test_b_commit_via_enter(dummy_app):
    dummy_app.selection_container.add((10, 10, 50, 50))
    rect_id = dummy_app.selection_container.get_all()[0].rect_id
    
    dummy_app.editing_region_id = rect_id
    dummy_app._update_selections_ui()
    
    tf, save_btn, cancel_btn = find_editing_controls(dummy_app)
    tf.value = "New Text via Enter"
    if tf.on_submit:
        tf.on_submit(DummyEvent(tf))
    else:
        pytest.fail("on_submit is not defined")
    
    assert dummy_app.edits.get(rect_id) == "New Text via Enter"
    assert dummy_app.editing_region_id is None

def test_c_commit_via_save_button(dummy_app):
    dummy_app.selection_container.add((10, 10, 50, 50))
    rect_id = dummy_app.selection_container.get_all()[0].rect_id
    
    dummy_app.editing_region_id = rect_id
    dummy_app._update_selections_ui()
    
    tf, save_btn, cancel_btn = find_editing_controls(dummy_app)
    tf.value = "New Text via Button"
    save_btn.on_click(DummyEvent(save_btn))
    
    assert dummy_app.edits.get(rect_id) == "New Text via Button"
    assert dummy_app.editing_region_id is None

def test_d_cancel_button(dummy_app):
    dummy_app.selection_container.add((10, 10, 50, 50))
    rect_id = dummy_app.selection_container.get_all()[0].rect_id
    
    dummy_app.editing_region_id = rect_id
    dummy_app._update_selections_ui()
    
    tf, save_btn, cancel_btn = find_editing_controls(dummy_app)
    tf.value = "Some text"
    cancel_btn.on_click(DummyEvent(cancel_btn))
    
    assert rect_id not in dummy_app.edits
    assert dummy_app.editing_region_id is None

def test_e_revert_button_and_suffix(dummy_app):
    dummy_app.selection_container.add((10, 10, 50, 50))
    rect_id = dummy_app.selection_container.get_all()[0].rect_id
    
    dummy_app.editing_region_id = rect_id
    dummy_app._update_selections_ui()
    
    tf, save_btn, cancel_btn = find_editing_controls(dummy_app)
    tf.value = "Committed text"
    
    if tf.on_submit:
        tf.on_submit(DummyEvent(tf))
    else:
        save_btn.on_click(DummyEvent(save_btn))
    
    def find_item_controls(app):
        for c in app.selections_list.controls:
            col = c.content
            # col: ft.Column([ft.Row([Text, Row(buttons)]), content_area])
            if isinstance(col, ft.Column) and len(col.controls) > 0:
                title_row = col.controls[0]
                if isinstance(title_row, ft.Row) and len(title_row.controls) == 2:
                    text_control = title_row.controls[0]
                    title_text = text_control.value if isinstance(text_control, ft.Text) else ""
                    btn_row = title_row.controls[1]
                    return title_text, btn_row
        return None, None
        
    title_text, btn_row = find_item_controls(dummy_app)
    assert title_text.endswith("(edited):")
    has_restore = False
    if btn_row:
        for b in btn_row.controls:
            if b.icon == ft.Icons.RESTORE:
                has_restore = True
    assert has_restore

def test_f_commit_empty_string(dummy_app):
    dummy_app.selection_container.add((10, 10, 50, 50))
    rect_id1 = dummy_app.selection_container.get_all()[0].rect_id
    dummy_app.editing_region_id = rect_id1
    dummy_app._update_selections_ui()
    tf1, save_btn1, _ = find_editing_controls(dummy_app)
    tf1.value = ""
    if tf1.on_submit:
        tf1.on_submit(DummyEvent(tf1))
    else:
        save_btn1.on_click(DummyEvent(save_btn1))
    
    dummy_app.selection_container.add((60, 60, 80, 80))
    rect_id2 = dummy_app.selection_container.get_all()[1].rect_id
    dummy_app.editing_region_id = rect_id2
    dummy_app._update_selections_ui()
    tf2, save_btn2, _ = find_editing_controls(dummy_app)
    tf2.value = ""
    save_btn2.on_click(DummyEvent(save_btn2))
    
    assert dummy_app.edits.get(rect_id1) == ""
    assert dummy_app.edits.get(rect_id2) == ""
