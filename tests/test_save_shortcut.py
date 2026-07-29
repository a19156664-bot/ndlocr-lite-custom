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
def dummy_viewer_multi(tmp_path, monkeypatch):
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", MagicMock(return_value=[]))
    monkeypatch.setattr("flet.core.control.Control.update", MagicMock())
    
    img1_path = tmp_path / "img1.png"
    img2_path = tmp_path / "img2.png"
    Image.new("RGB", (100, 100), color="white").save(img1_path)
    Image.new("RGB", (100, 100), color="white").save(img2_path)
    
    viewer = SelectableImageViewer(str(img1_path), 100, 100, 800, 600)
    viewer.page = DummyPage()
    
    viewer.sequence = MagicMock()
    viewer.sequence._paths = [str(img1_path), str(img2_path)]
    viewer.sequence.count = 2
    viewer.sequence.index = 0
    viewer.sequence.has_next = lambda: viewer.sequence.index < viewer.sequence.count - 1
    viewer.sequence.next = lambda: viewer.sequence._paths[1]
    
    viewer.btn_next.disabled = False
    
    viewer._switch_image(str(img1_path))
    viewer.ocr_state = OcrState.DONE
    viewer.ocr_results = [
        {"text": "Line 1", "bbox": (10, 10, 50, 20), "confidence": 0.9, "is_vertical": False, "source_image": str(img1_path)}
    ]
    
    viewer.image_states[str(img1_path)]["selections"].add((10, 10, 50, 50), "Region 1")
    viewer.image_states[str(img2_path)] = {
        "selections": viewer.selection_container.__class__(),
        "ocr_state": OcrState.DONE,
        "ocr_results": [],
        "ocr_error": None,
        "edits": {},
        "mark": None
    }
    
    return viewer, str(img1_path), str(img2_path)

def test_a_completion_dialog_on_page_1(tmp_path, dummy_viewer_multi):
    viewer, img1_path, _ = dummy_viewer_multi
    
    viewer._start_export("current")
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存しました"
    assert "次のページへ進みますか？" in viewer._save_dialog.content.value
    assert len(viewer._save_dialog.actions) == 2
    assert viewer._save_dialog.actions[0].text == "ここに残る"
    assert viewer._save_dialog.actions[1].text == "次へ"
    assert viewer._save_dialog.actions[1].autofocus is True

def test_b_firing_next_action_advances(tmp_path, dummy_viewer_multi):
    viewer, img1_path, img2_path = dummy_viewer_multi
    
    viewer._start_export("current")
    
    assert viewer._save_dialog is not None
    next_action = viewer._save_dialog.actions[1]
    assert next_action.text == "次へ"
    
    next_action.on_click(None)
    
    assert viewer._save_dialog is None
    assert viewer.image_src == img2_path

def test_c_firing_stay_action_stays(tmp_path, dummy_viewer_multi):
    viewer, img1_path, img2_path = dummy_viewer_multi
    
    viewer._start_export("current")
    
    assert viewer._save_dialog is not None
    stay_action = viewer._save_dialog.actions[0]
    assert stay_action.text == "ここに残る"
    
    stay_action.on_click(None)
    
    assert viewer._save_dialog is None
    assert viewer.image_src == img1_path

def test_d_last_page_dialog(tmp_path, dummy_viewer_multi):
    viewer, img1_path, img2_path = dummy_viewer_multi
    
    viewer.sequence.index = 1
    viewer.sequence.has_next = lambda: False
    viewer.btn_next.disabled = True
    
    viewer._switch_image(img2_path)
    viewer.ocr_state = OcrState.DONE
    viewer.image_states[img2_path]["selections"].add((10, 10, 50, 50), "Region 1")
    
    viewer._start_export("current")
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存しました"
    assert "次のページへ進みますか？" not in viewer._save_dialog.content.value
    assert len(viewer._save_dialog.actions) == 1
    assert viewer._save_dialog.actions[0].text == "OK"
    assert viewer._save_dialog.actions[0].autofocus is True

def test_e_all_pages_dialog(tmp_path, dummy_viewer_multi):
    viewer, img1_path, img2_path = dummy_viewer_multi
    
    viewer._start_export("all")
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存しました"
    assert "次のページへ進みますか？" not in viewer._save_dialog.content.value
    assert len(viewer._save_dialog.actions) == 1
    assert viewer._save_dialog.actions[0].text == "OK"
    assert viewer._save_dialog.actions[0].autofocus is True

def test_f_overwrite_dialog_has_no_autofocus(tmp_path, dummy_viewer_multi):
    viewer, img1_path, _ = dummy_viewer_multi
    
    stem = os.path.splitext(os.path.basename(img1_path))[0]
    csv_path = os.path.join(tmp_path, f"{stem}.csv")
    txt_path = os.path.join(tmp_path, f"{stem}.txt")
    
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("SENTINEL")
        
    viewer._start_export("current")
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "上書き確認"
    for action in viewer._save_dialog.actions:
        assert getattr(action, "autofocus", False) is False

def test_g_ctrl_s_shortcut(tmp_path, monkeypatch):
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", MagicMock(return_value=[]))
    monkeypatch.setattr("flet.core.control.Control.update", MagicMock())
    
    img_path = tmp_path / "img1.png"
    Image.new("RGB", (100, 100), color="white").save(img_path)
    
    # We construct main to get the actual global on_keyboard
    page = DummyPage()
    import sys
    monkeypatch.setattr(sys, "argv", ["app.py", str(img_path)])
    
    # Run main which will populate page.on_keyboard_event
    main(page)
    
    viewer = page.controls[0]
    viewer.page = page
    
    viewer._switch_image(str(img_path))
    viewer.ocr_state = OcrState.DONE
    viewer.image_states[str(img_path)]["selections"].add((10, 10, 50, 50), "Region 1")
    
    on_keyboard = page.on_keyboard_event
    assert on_keyboard is not None
    
    stem = os.path.splitext(os.path.basename(str(img_path)))[0]
    csv_path = os.path.join(tmp_path, f"{stem}.csv")
    txt_path = os.path.join(tmp_path, f"{stem}.txt")
    
    # Fire Ctrl+S
    class DummyEvent:
        def __init__(self, key, ctrl):
            self.key = key
            self.ctrl = ctrl
            
    on_keyboard(DummyEvent("S", True))
    
    assert os.path.exists(csv_path)
    assert os.path.exists(txt_path)
    
    # Remove to check if it gets written again
    os.remove(csv_path)
    viewer._save_dialog = None
    
    # Start inline edit
    viewer.editing_region_id = 1
    
    on_keyboard(DummyEvent("S", True))
    
    assert not os.path.exists(csv_path)
    assert viewer._save_dialog is None

