import os
import pytest
import flet as ft
from unittest.mock import MagicMock
from PIL import Image

from custom_gui.app import SelectableImageViewer, OcrState
from custom_gui.selection import SelectionRect

class DummyPage:
    def __init__(self):
        self.controls = []
        self.overlay = []
        self.dialog = None

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
def dummy_viewer(tmp_path, monkeypatch):
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", MagicMock(return_value=[]))
    monkeypatch.setattr("flet.core.control.Control.update", MagicMock())
    
    img_path = tmp_path / "test_img.png"
    Image.new("RGB", (100, 100), color="white").save(img_path)
    
    viewer = SelectableImageViewer(str(img_path), 100, 100, 800, 600)
    viewer.page = DummyPage()
    viewer._switch_image(str(img_path))
    viewer.ocr_state = OcrState.DONE
    viewer.ocr_results = [
        {"text": "Line 1", "bbox": (10, 10, 50, 20), "confidence": 0.9, "is_vertical": False, "source_image": str(img_path)}
    ]
    return viewer, str(img_path)

def test_a_toolbar_buttons(dummy_viewer):
    viewer, _ = dummy_viewer
    controls = viewer.controls_row.controls
    
    has_save = False
    has_save_all = False
    has_popup = False
    for c in controls:
        if isinstance(c, ft.IconButton):
            if c.icon == ft.Icons.SAVE:
                has_save = True
            elif c.icon == ft.Icons.SAVE_ALT:
                has_save_all = True
        elif isinstance(c, ft.PopupMenuButton):
            has_popup = True
            
    assert has_save
    assert has_save_all
    assert not has_popup

def test_b_save_current_no_dialog(tmp_path, dummy_viewer, monkeypatch):
    viewer, img_path = dummy_viewer
    
    def failing_save_file(*args, **kwargs):
        raise AssertionError("Should not be called")
        
    monkeypatch.setattr(viewer.file_picker, "save_file", failing_save_file)
    
    viewer.selection_container.add((10, 10, 50, 50), "Region 1")
    viewer.selection_container.add((10, 10, 50, 50), "Region 1")
    viewer._start_export("current")
    
    stem = os.path.splitext(os.path.basename(img_path))[0]
    csv_path = os.path.join(tmp_path, f"{stem}.csv")
    txt_path = os.path.join(tmp_path, f"{stem}.txt")
    
    assert os.path.exists(csv_path)
    assert os.path.exists(txt_path)
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存しました"
    assert len(viewer._save_dialog.actions) == 1
    assert viewer._save_dialog.actions[0].text == "OK"
    
    # Click OK to close dialog
    viewer._save_dialog.actions[0].on_click(None)
    assert viewer._save_dialog is None

def test_d_overwrite_dialog(tmp_path, dummy_viewer, monkeypatch):
    viewer, img_path = dummy_viewer
    
    stem = os.path.splitext(os.path.basename(img_path))[0]
    csv_path = os.path.join(tmp_path, f"{stem}.csv")
    txt_path = os.path.join(tmp_path, f"{stem}.txt")
    
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("SENTINEL")
        
    viewer.selection_container.add((10, 10, 50, 50), "Region 1")
    viewer._start_export("current")
    
    assert viewer._save_dialog is not None
    assert viewer._save_dialog.title.value == "保存しました"
    
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        assert "SENTINEL" not in f.read()

def test_e_save_all(tmp_path, monkeypatch):
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", MagicMock(return_value=[]))
    monkeypatch.setattr("flet.core.control.Control.update", MagicMock())
    
    img1_path = tmp_path / "img1.png"
    img2_path = tmp_path / "img2.png"
    Image.new("RGB", (100, 100), color="white").save(img1_path)
    Image.new("RGB", (100, 100), color="white").save(img2_path)
    
    viewer = SelectableImageViewer(str(img1_path), 100, 100, 800, 600)
    viewer.page = DummyPage()
    
    # Fake a sequence
    viewer.sequence = MagicMock()
    viewer.sequence._paths = [str(img1_path), str(img2_path)]
    viewer.sequence.count = 2
    viewer.sequence.index = 0
    viewer._switch_image(str(img1_path))
    viewer.image_states[str(img1_path)]["ocr_state"] = OcrState.DONE
    viewer.image_states[str(img1_path)]["selections"].add((10, 10, 50, 50), "Region 1")
    
    viewer.image_states[str(img2_path)] = {
        "selections": viewer.selection_container.__class__(),
        "ocr_state": OcrState.DONE,
        "ocr_results": [],
        "edits": {}
    }
    viewer.image_states[str(img2_path)]["selections"].add((10, 10, 50, 50), "Region 1")
    
    viewer._start_export("all")
    
    folder_name = tmp_path.name
    csv_path = os.path.join(tmp_path, f"{folder_name}_all.csv")
    txt_path = os.path.join(tmp_path, f"{folder_name}_all.txt")
    
    assert os.path.exists(csv_path)
    assert os.path.exists(txt_path)

def test_f_panel_breaks(tmp_path, monkeypatch):
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", MagicMock(return_value=[]))
    monkeypatch.setattr("flet.core.control.Control.update", MagicMock())
    
    img_path = tmp_path / "test_img.png"
    Image.new("RGB", (100, 100), color="white").save(img_path)
    
    viewer = SelectableImageViewer(str(img_path), 100, 100, 800, 600)
    viewer.page = DummyPage()
    viewer._switch_image(str(img_path))
    
    viewer.ocr_state = OcrState.DONE
    viewer.ocr_results = [
        {"text": "Line 1", "bbox": (10, 10, 50, 20), "confidence": 0.9, "is_vertical": True, "source_image": str(img_path)},
        {"text": "Line 2", "bbox": (10, 20, 50, 30), "confidence": 0.9, "is_vertical": True, "source_image": str(img_path)},
        {"text": "Line 3", "bbox": (10, 30, 50, 40), "confidence": 0.9, "is_vertical": True, "source_image": str(img_path)},
    ]
    
    rect = viewer.selection_container.add((0, 0, 100, 100), "Region 1"); rect_id = rect.rect_id
    viewer._update_selections_ui()
    
    # Find the header text in the real ui tree
    header_text = None
    for item in viewer.selections_list.controls:
        # item is ft.Container -> content=ft.Column -> controls=[ft.Row, content_area]
        if isinstance(item, ft.Container) and isinstance(item.content, ft.Column):
            row = item.content.controls[0]
            if isinstance(row, ft.Row):
                # row.controls[0] is ft.Text
                text_ctrl = row.controls[0]
                if isinstance(text_ctrl, ft.Text):
                    header_text = text_ctrl.value
                    break
                    
    assert header_text == "Region 1 [改行 2]:"
    
    viewer.commit_edit(rect_id, "一行だけ")
    viewer._update_selections_ui()
    
    for item in viewer.selections_list.controls:
        if isinstance(item, ft.Container) and isinstance(item.content, ft.Column):
            row = item.content.controls[0]
            if isinstance(row, ft.Row):
                text_ctrl = row.controls[0]
                if isinstance(text_ctrl, ft.Text):
                    header_text = text_ctrl.value
                    break
                    
    assert header_text == "Region 1 (edited) [改行 0]:"

