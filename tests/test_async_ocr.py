import os
import pytest
from custom_gui.app import OcrState, get_ocr_status_text, SelectableImageViewer

def test_ocr_status_text_generation():
    assert get_ocr_status_text(OcrState.IDLE) == "OCR not started"
    assert get_ocr_status_text(OcrState.WAITING) == "OCR waiting"
    assert get_ocr_status_text(OcrState.RUNNING) == "OCR running"
    assert get_ocr_status_text(OcrState.ERROR) == "OCR failed"
    assert get_ocr_status_text(OcrState.DONE, 26) == "Lines: 26"

def test_viewer_init_does_not_run_ocr(monkeypatch):
    image_path = os.path.join("resource", "digidepo_2531162_0024.jpg")
    assert os.path.exists(image_path), f"Test image not found at {image_path}"

    def fake_run_ocr(*args, **kwargs):
        raise AssertionError("OCR function was called during __init__!")
        
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", fake_run_ocr)
    
    viewer = SelectableImageViewer(
        image_src=image_path, 
        img_w=100, img_h=100, 
        win_w=100, win_h=100
    )
    
    assert viewer.ocr_results == []
    # Assert state is IDLE since the image exists
    assert viewer.ocr_state == OcrState.IDLE

def test_update_selections_ui_no_crash_with_empty_ocr(monkeypatch):
    image_path = os.path.join("resource", "digidepo_2531162_0024.jpg")
    assert os.path.exists(image_path), f"Test image not found at {image_path}"

    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", lambda *args: [])

    viewer = SelectableImageViewer(
        image_src=image_path, 
        img_w=100, img_h=100, 
        win_w=100, win_h=100
    )
    
    viewer.ocr_results = []
    # Add a mock region to simulate drawing before OCR done
    viewer.selection_container.add((10.0, 10.0, 20.0, 20.0))
    
    # Should not raise any exceptions
    viewer._update_selections_ui()
    # No OCR lines means no extracted text highlights
    assert len(viewer.highlight_layer.controls) == 0
    assert viewer.ocr_state == OcrState.IDLE

def test_on_ocr_complete_success(monkeypatch):
    image_path = os.path.join("resource", "digidepo_2531162_0024.jpg")
    assert os.path.exists(image_path), f"Test image not found at {image_path}"

    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", lambda *args: [])

    viewer = SelectableImageViewer(
        image_src=image_path, 
        img_w=100, img_h=100, 
        win_w=100, win_h=100
    )
    
    mock_results = [
        {"text": "Line 1", "bbox": (0, 0, 10, 10), "confidence": 0.9, "is_vertical": False, "source_image": image_path},
        {"text": "Line 2", "bbox": (0, 10, 10, 20), "confidence": 0.9, "is_vertical": False, "source_image": image_path}
    ]
    
    viewer.progress_ring.visible = True
    viewer.ocr_state = OcrState.RUNNING
    
    viewer._on_ocr_complete(mock_results, None)
    
    assert viewer.progress_ring.visible is False
    assert viewer.ocr_state == OcrState.DONE
    assert len(viewer.ocr_results) == 2
    
    status_msg = viewer._get_status_message()
    assert "Lines: 2" in status_msg

def test_on_ocr_complete_error(monkeypatch):
    image_path = os.path.join("resource", "digidepo_2531162_0024.jpg")
    assert os.path.exists(image_path), f"Test image not found at {image_path}"

    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", lambda *args: [])

    viewer = SelectableImageViewer(
        image_src=image_path, 
        img_w=100, img_h=100, 
        win_w=100, win_h=100
    )
    
    viewer.progress_ring.visible = True
    viewer.ocr_state = OcrState.RUNNING
    
    viewer._on_ocr_complete(None, "File not found")
    
    assert viewer.progress_ring.visible is False
    assert viewer.ocr_state == OcrState.ERROR
    assert viewer.ocr_error == "File not found"
    
    status_msg = viewer._get_status_message()
    assert "OCR failed" in status_msg

def test_viewer_init_missing_file_error():
    image_path = "does_not_exist.jpg"
    assert not os.path.exists(image_path)

    viewer = SelectableImageViewer(
        image_src=image_path,
        img_w=100, img_h=100,
        win_w=100, win_h=100
    )

    assert viewer.ocr_state == OcrState.ERROR

    # start_ocr should return without doing anything
    class MockPage:
        def run_thread(self, *args, **kwargs):
            raise AssertionError("run_thread should not be called when OCR state is ERROR")
            
    viewer.start_ocr(MockPage())
    # State should remain ERROR
    assert viewer.ocr_state == OcrState.ERROR
