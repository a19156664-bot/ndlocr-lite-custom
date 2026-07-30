import os
import pytest
import flet as ft
from unittest.mock import MagicMock
from PIL import Image

from custom_gui.app import SelectableImageViewer, OcrState, main

class DummyPage:
    def __init__(self):
        self.controls = []
        self.overlay = []
        self.dialog = None
        self.width = 800
        self.height = 600

    def add(self, *controls):
        self.controls.extend(controls)
        
    def update(self):
        pass
        
    def open(self, dialog):
        self.dialog = dialog
        self.overlay.append(dialog)
        
    def close(self, dialog):
        if dialog in self.overlay:
            self.overlay.remove(dialog)
        if self.dialog == dialog:
            self.dialog = None
            
    def run_thread(self, fn, *args):
        fn(*args)

@pytest.fixture
def viewer_app(tmp_path, monkeypatch):
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", MagicMock(return_value=[]))
    monkeypatch.setattr("flet.core.control.Control.update", MagicMock())
    
    img1_path = tmp_path / "img1.png"
    img2_path = tmp_path / "img2.png"
    Image.new("RGB", (100, 100), color="white").save(img1_path)
    Image.new("RGB", (100, 100), color="white").save(img2_path)
    
    page = DummyPage()
    import sys
    monkeypatch.setattr(sys, "argv", ["app.py", str(img1_path)])
    
    main(page)
    
    viewer = page.controls[0]
    viewer.page = page
    
    viewer.sequence = MagicMock()
    viewer.sequence._paths = [str(img1_path), str(img2_path)]
    viewer.sequence.count = 2
    viewer.sequence.index = 0
    viewer.sequence.has_next = lambda: viewer.sequence.index < viewer.sequence.count - 1
    viewer.sequence.next = lambda: viewer.sequence._paths[1]
    
    viewer.btn_next.disabled = False
    
    viewer._switch_image(str(img1_path))
    
    viewer.image_states[str(img2_path)] = {
        "selections": viewer.selection_container.__class__(),
        "ocr_state": OcrState.IDLE,
        "ocr_results": [],
        "ocr_error": None,
        "edits": {},
        "mark": None
    }
    
    return viewer, str(img1_path), str(img2_path), page

def get_save_btn(viewer):
    for c in viewer.controls_row.controls:
        if isinstance(c, ft.IconButton) and c.icon == ft.Icons.SAVE:
            return c
    return None

def test_z1_save_no_rects_no_mark_dialog(viewer_app):
    viewer, img1_path, _, _ = viewer_app
    
    viewer.selection_container.rects = []
    viewer.mark = None
    
    btn = get_save_btn(viewer)
    btn.on_click(None)
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存できません"
    assert viewer._save_dialog.content.value == "OCRデータがございません。"
    
    stem = os.path.splitext(os.path.basename(img1_path))[0]
    csv_path = os.path.join(os.path.dirname(img1_path), f"{stem}.csv")
    txt_path = os.path.join(os.path.dirname(img1_path), f"{stem}.txt")
    assert not os.path.exists(csv_path)
    assert not os.path.exists(txt_path)

def test_z2_ctrl_s_no_rects_no_mark_dialog(viewer_app):
    viewer, img1_path, _, page = viewer_app
    
    viewer.selection_container.rects = []
    viewer.mark = None
    
    class DummyEvent:
        def __init__(self, key, ctrl):
            self.key = key
            self.ctrl = ctrl
            
    page.on_keyboard_event(DummyEvent("S", True))
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存できません"
    assert viewer._save_dialog.content.value == "OCRデータがございません。"

def test_z3_ocr_error_refusal(viewer_app):
    viewer, img1_path, _, _ = viewer_app
    
    viewer.selection_container.add((10, 10, 50, 50), "Region 1")
    viewer.ocr_state = OcrState.ERROR
    viewer.ocr_error = "Mock OCR Error"
    
    btn = get_save_btn(viewer)
    btn.on_click(None)
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存できません"
    assert viewer._save_dialog.content.value == "Mock OCR Error"
    
    stem = os.path.splitext(os.path.basename(img1_path))[0]
    csv_path = os.path.join(os.path.dirname(img1_path), f"{stem}.csv")
    assert not os.path.exists(csv_path)

def test_a_save_twice_overwrites(viewer_app):
    viewer, img1_path, _, _ = viewer_app
    
    viewer.selection_container.add((10, 10, 50, 50), "Region 1")
    viewer.ocr_state = OcrState.DONE
    viewer.ocr_results = [{"bbox": (10,10,50,50), "text": "Hello", "confidence": 0.9, "is_vertical": False, "source_image": img1_path}]
    
    btn = get_save_btn(viewer)
    btn.on_click(None)
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存しました"
    
    stem = os.path.splitext(os.path.basename(img1_path))[0]
    csv_path = os.path.join(os.path.dirname(img1_path), f"{stem}.csv")
    
    with open(csv_path, "a", encoding="utf-8-sig") as f:
        f.write("\nSENTINEL\n")
        
    viewer._save_dialog = None
    btn.on_click(None)
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存しました"
    
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        assert "SENTINEL" not in f.read()

def test_b_ctrl_s_twice_writes(viewer_app):
    viewer, img1_path, _, page = viewer_app
    
    viewer.selection_container.add((10, 10, 50, 50), "Region 1")
    viewer.ocr_state = OcrState.DONE
    
    class DummyEvent:
        def __init__(self, key, ctrl):
            self.key = key
            self.ctrl = ctrl
            
    page.on_keyboard_event(DummyEvent("S", True))
    assert viewer._save_dialog is not None
    
    viewer._save_dialog = None
    page.on_keyboard_event(DummyEvent("S", True))
    assert viewer._save_dialog is not None

def test_c_mark_then_save(viewer_app):
    viewer, img1_path, _, _ = viewer_app
    
    viewer.selection_container.add((10, 10, 50, 50), "Region 1")
    viewer.ocr_state = OcrState.DONE
    
    viewer.btn_mark_ad.on_click(None)
    
    btn = get_save_btn(viewer)
    btn.on_click(None)
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存しました"

def test_d_no_overwrite_dialog_method(viewer_app):
    viewer, _, _, _ = viewer_app
    assert not hasattr(viewer, "_show_overwrite_dialog")

def test_e_queue_save_during_ocr(viewer_app):
    viewer, img1_path, _, _ = viewer_app
    
    viewer.selection_container.add((10, 10, 50, 50), "Region 1")
    viewer.ocr_state = OcrState.WAITING
    
    btn = get_save_btn(viewer)
    btn.on_click(None)
    
    assert viewer._pending_export == img1_path
    
    viewer._on_ocr_complete([{"bbox": (10,10,50,50), "text": "Hello", "confidence": 0.9, "is_vertical": False, "source_image": img1_path}], None)
    
    assert viewer._pending_export is None
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存しました"
    
    stem = os.path.splitext(os.path.basename(img1_path))[0]
    csv_path = os.path.join(os.path.dirname(img1_path), f"{stem}.csv")
    assert os.path.exists(csv_path)

def test_f_queue_save_then_switch_image(viewer_app):
    viewer, img1_path, img2_path, _ = viewer_app
    
    viewer.selection_container.add((10, 10, 50, 50), "Region 1")
    viewer.ocr_state = OcrState.WAITING
    
    btn = get_save_btn(viewer)
    btn.on_click(None)
    
    assert viewer._pending_export == img1_path
    
    viewer._switch_image(img2_path)
    assert viewer._pending_export is None
    
    viewer._on_ocr_complete([{"bbox": (10,10,50,50), "text": "Hello", "confidence": 0.9, "is_vertical": False, "source_image": img1_path}], None, target_path=img1_path)
    
    stem = os.path.splitext(os.path.basename(img1_path))[0]
    csv_path = os.path.join(os.path.dirname(img1_path), f"{stem}.csv")
    assert not os.path.exists(csv_path)

def test_g_queue_save_then_ocr_error(viewer_app):
    viewer, img1_path, _, _ = viewer_app
    
    viewer.selection_container.add((10, 10, 50, 50), "Region 1")
    viewer.ocr_state = OcrState.WAITING
    
    btn = get_save_btn(viewer)
    btn.on_click(None)
    
    viewer._on_ocr_complete([], "Mock OCR Error", target_path=img1_path)
    
    assert viewer._pending_export is None
    assert viewer.latest_region_info == "Mock OCR Error"
    
    stem = os.path.splitext(os.path.basename(img1_path))[0]
    csv_path = os.path.join(os.path.dirname(img1_path), f"{stem}.csv")
    assert not os.path.exists(csv_path)
    
    # Dialog could have been opened for error but in this test it is just in status.
    # We didn't pop up an error dialog from `_on_ocr_complete` specifically, just updated status.

def test_h_save_twice_during_ocr_exports_once(viewer_app, monkeypatch):
    viewer, img1_path, _, _ = viewer_app
    
    viewer.selection_container.add((10, 10, 50, 50), "Region 1")
    viewer.ocr_state = OcrState.WAITING
    
    btn = get_save_btn(viewer)
    btn.on_click(None)
    btn.on_click(None)
    
    call_count = 0
    orig_do_write = viewer._do_write_and_show_done
    def mock_write(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return orig_do_write(*args, **kwargs)
        
    monkeypatch.setattr(viewer, "_do_write_and_show_done", mock_write)
    
    viewer._on_ocr_complete([{"bbox": (10,10,50,50), "text": "Hello", "confidence": 0.9, "is_vertical": False, "source_image": img1_path}], None)
    
    assert call_count == 1

def test_i_all_pages_still_overwrites_no_confirmation(viewer_app):
    viewer, img1_path, img2_path, _ = viewer_app
    
    viewer.selection_container.add((10, 10, 50, 50), "Region 1")
    viewer.ocr_state = OcrState.DONE
    viewer.image_states[img1_path]["ocr_state"] = OcrState.DONE
    
    folder_name = os.path.basename(os.path.dirname(img1_path))
    csv_path = os.path.join(os.path.dirname(img1_path), f"{folder_name}_all.csv")
    
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("SENTINEL")
        
    viewer._start_export("all")
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存しました"
    
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        assert "SENTINEL" not in f.read()

