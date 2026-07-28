import flet as ft
from custom_gui.app import SelectableImageViewer
import os
from custom_gui.image_sequence import ImageSequence

class FakeFile:
    def __init__(self, name, path):
        self.name = name
        self.path = path

class FakeFilePickerResultEvent(ft.FilePickerResultEvent):
    def __init__(self, path=None, files=None):
        self.path = path
        self.files = files
        self.control = None
        self.page = None
        self.target = ""
        self.name = ""
        self.data = ""

def test_pdf_file_picker_result(monkeypatch):
    image_path = os.path.join("resource", "digidepo_2531162_0024.jpg")
    assert os.path.exists(image_path), f"Test image not found at {image_path}"

    def fake_run_ocr(*args, **kwargs):
        pass

    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", fake_run_ocr)

    viewer = SelectableImageViewer(
        image_src=image_path, 
        img_w=100, img_h=100, 
        win_w=100, win_h=100
    )
    
    # Mock plan_pdf_pages to return some dummy pages
    def fake_plan_pdf_pages(pdf_path, cache_dir):
        return [
            ("dummy_page_1.png", pdf_path, 0),
            ("dummy_page_2.png", pdf_path, 1)
        ]
    
    monkeypatch.setattr("custom_gui.app.plan_pdf_pages", fake_plan_pdf_pages)
    
    # Mock ensure_page_rendered
    def fake_ensure_page_rendered(*args, **kwargs):
        pass
    monkeypatch.setattr("custom_gui.app.ensure_page_rendered", fake_ensure_page_rendered)

    viewer._file_picker_mode = "pdf"
    
    initial_sequence_count = viewer.sequence.count
    
    event = FakeFilePickerResultEvent(
        path=None, 
        files=[FakeFile(name="doc.pdf", path="doc.pdf")]
    )
    
    viewer._on_file_picker_result(event)
    
    assert viewer.sequence.count > initial_sequence_count, "The sequence count should have increased."
