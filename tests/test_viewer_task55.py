import flet as ft
from custom_gui.app import SelectableImageViewer
from unittest.mock import MagicMock
from pytest import approx
import json
import tempfile
import os
from PIL import Image

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
    
    app.selections_list.update = MagicMock()
    app.highlight_layer.update = MagicMock()
    app.rects_layer.update = MagicMock()
    app.inline_editor_layer.update = MagicMock()
    app.gesture_detector.update = MagicMock()
    if hasattr(app, 'mark_label'):
        app.mark_label.update = MagicMock()
        
    return app

def test_task55(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # --- Setup S ---
    app = get_app(dummy_page())
    
    # Restore rects 2 and 3
    from custom_gui.selection import SelectionRect
    app.selection_container.restore([
        SelectionRect("2", (100, 200, 300, 400), "Region 2"),
        SelectionRect("3", (500, 600, 700, 800), "Region 3")
    ])
    
    # Fake ocr results for both
    app.ocr_results = [
        {'text': "Text 2", 'bbox': (150, 250, 250, 350), 'confidence': 0.9, 'is_vertical': False, 'source_image': "dummy.dat"},
        {'text': "Text 3", 'bbox': (550, 650, 650, 750), 'confidence': 0.9, 'is_vertical': False, 'source_image': "dummy.dat"}
    ]
    
    app._update_selections_ui()
    s = app.zoom_scale
    
    # Baseline
    assert len(app.rects_layer.controls) == 4
    assert len(app.highlight_layer.controls) == 2
    
    # Extract eye button for rect 2
    row2 = app.selections_list.controls[0]
    row3 = app.selections_list.controls[1]
    
    if "Region 3" in row2.content.controls[0].controls[0].value:
        row2, row3 = row3, row2
    
    buttons_row2 = row2.content.controls[0].controls[1]
    
    tooltips = [c.tooltip for c in buttons_row2.controls]
    
    # 1. Check tooltips and icon
    assert tooltips == ["Edit", "右から変換", "この枠だけOCR", "画像の枠を隠す", "縦で読む", "Delete"]
    eye_button_2 = buttons_row2.controls[3]
    assert eye_button_2.icon == ft.Icons.VISIBILITY
    
    # 2. Press eye button
    old_selections_list_controls = id(app.selections_list.controls)
    
    class FakeEvent:
        def __init__(self, control):
            self.control = control
            
    eye_button_2.on_click(FakeEvent(eye_button_2))
    
    assert len(app.rects_layer.controls) == 2
    border_3 = app.rects_layer.controls[0]
    label_3 = app.rects_layer.controls[1]
    if border_3.bgcolor != ft.Colors.TRANSPARENT: # Label is first
        border_3, label_3 = label_3, border_3
    
    assert border_3.left == approx(500 * s)
    assert border_3.top == approx(600 * s)
    assert label_3.content.value == "Region 3"
    
    assert len(app.highlight_layer.controls) == 1
    
    assert eye_button_2.icon == ft.Icons.VISIBILITY_OFF
    assert eye_button_2.tooltip == "画像の枠を表示"
    
    assert "Text 2" in row2.content.controls[1].value
    
    # 3. Not rebuilt
    assert id(app.selections_list.controls) == old_selections_list_controls
    
    # 4. Press again
    eye_button_2.on_click(FakeEvent(eye_button_2))
    
    assert len(app.rects_layer.controls) == 4
    assert len(app.highlight_layer.controls) == 2
    assert eye_button_2.icon == ft.Icons.VISIBILITY
    assert eye_button_2.tooltip == "画像の枠を隠す"
    
    # 5. Hide "2" then zoom in
    eye_button_2.on_click(FakeEvent(eye_button_2))
    app.zoom_in(None)
    new_s = app.zoom_scale
    assert len(app.rects_layer.controls) == 2
    
    border_3 = app.rects_layer.controls[0]
    label_3 = app.rects_layer.controls[1]
    if border_3.bgcolor != ft.Colors.TRANSPARENT:
        border_3, label_3 = label_3, border_3
    assert border_3.left == approx(500 * new_s)
    
    # 6. Not saved
    import copy
    from custom_gui.work_state import load_work_state, work_path_for
    app._persist_work_state()
    w1 = load_work_state(app.image_src)
    
    eye_button_2.on_click(FakeEvent(eye_button_2)) # Show "2"
    app._persist_work_state()
    w2 = load_work_state(app.image_src)
    
    # Check loaded results are equal
    assert w1 == w2
    
    # 7. Per page
    p1 = tmp_path / "1.png"
    p2 = tmp_path / "2.png"
    Image.new("RGB", (50, 50)).save(p1)
    Image.new("RGB", (50, 50)).save(p2)
    
    app_multi = get_app(dummy_page())
    app_multi.image_src = str(p1)
    app_multi.sequence = MagicMock()
    app_multi.sequence.images = [str(p1), str(p2)]
    app_multi.sequence.count = 2
    app_multi.sequence.index = 0
    
    app_multi.selection_container.restore([
        SelectionRect("2", (100, 200, 300, 400), "Region 2")
    ])
    app_multi._update_selections_ui()
    
    row2_multi = app_multi.selections_list.controls[0]
    eye_multi = row2_multi.content.controls[0].controls[1].controls[3]
    eye_multi.on_click(FakeEvent(eye_multi)) # Hide 2
    
    assert str("2") in app_multi._hidden_ids()
    
    # mock load_persisted_state
    app_multi._load_persisted_state = MagicMock(return_value=(MagicMock(), {}, None))
    app_multi.btn_prev = MagicMock()
    app_multi.btn_next = MagicMock()
    app_multi.page_text = MagicMock()
    app_multi.status_text = MagicMock()
    app_multi.image_container = MagicMock()
    app_multi.controls_row = MagicMock()
    app_multi.status_row = MagicMock()
    
    app_multi.status_text = MagicMock()
    app_multi.image_container = MagicMock()
    app_multi.controls_row = MagicMock()
    app_multi.status_row = MagicMock()
    app_multi.btn_prev.disabled = False
    app_multi.btn_next.disabled = False
    app_multi.sequence.has_prev = MagicMock(return_value=False)
    app_multi.sequence.has_next = MagicMock(return_value=True)

    # Switch to page 2
    app_multi.image_src = str(p2) # just fake the image src since _switch_image is complex
    
    app_multi.selection_container.restore([
        SelectionRect("2", (100, 200, 300, 400), "Region 2")
    ])
    app_multi._redraw_overlays()
    
    # Rect 2 IS drawn on page two
    assert len(app_multi.rects_layer.controls) == 2
    
    app_multi.image_src = str(p1)
    
    # Rect 2 is still hidden on page 1
    assert str("2") in app_multi._hidden_ids()
    
    # 8. Restart
    app_new = SelectableImageViewer(
        image_src=str(p1), img_w=1000, img_h=1000, win_w=1000, win_h=1000
    )
    assert app_new.hidden_regions == {}
    app_new.selection_container.restore([
        SelectionRect("2", (100, 200, 300, 400), "Region 2")
    ])
    app_new.page = dummy_page()
    app_new._redraw_overlays()
    assert len(app_new.rects_layer.controls) == 2
    
    # 9. Tap
    app_tap = get_app(dummy_page())
    app_tap.selection_container.restore([
        SelectionRect("2", (100, 200, 300, 400), "Region 2"),
        SelectionRect("4", (0, 0, 900, 900), "Region 4")
    ])
    app_tap.mode_state.current = "SELECT"
    app_tap._update_selections_ui()
    
    from custom_gui.viewer import original_to_display
    dx, dy = original_to_display(200, 300, app_tap.zoom_scale, app_tap.offset_x, app_tap.offset_y)
    
    class TapEvent:
        def __init__(self, lx, ly):
            self.local_x = lx
            self.local_y = ly
            
    app_tap._on_tap_up(TapEvent(dx, dy))
    assert app_tap.active_region_id == "2"
    
    # Hide 2
    app_tap.toggle_region_visible("2")
    app_tap.active_region_id = None
    app_tap._on_tap_up(TapEvent(dx, dy))
    assert app_tap.active_region_id == "4"
    
    # 10. Typing is kept
    app_typing = get_app(dummy_page())
    app_typing.selection_container.restore([
        SelectionRect("2", (100, 200, 300, 400), "Region 2"),
        SelectionRect("3", (500, 600, 700, 800), "Region 3")
    ])
    app_typing.editing_region_id = "3"
    app_typing._update_selections_ui()
    
    row2_t = app_typing.selections_list.controls[0]
    row3_t = app_typing.selections_list.controls[1]
    
    if "Region 3" in row2_t.content.controls[0].controls[0].value:
        row2_t, row3_t = row3_t, row2_t
        
    tf = row3_t.content.controls[1]
    tf.value = "途中の入力"
    
    tf_id = id(tf)
    
    eye_t = row2_t.content.controls[0].controls[1].controls[3]
    eye_t.on_click(FakeEvent(eye_t))
    
    # Check same text field
    row3_t_new = app_typing.selections_list.controls[1]
    if "Region 3" in app_typing.selections_list.controls[0].content.controls[0].controls[0].value:
        row3_t_new = app_typing.selections_list.controls[0]
        
    tf_new = row3_t_new.content.controls[1]
    assert id(tf_new) == tf_id
    assert tf_new.value == "途中の入力"