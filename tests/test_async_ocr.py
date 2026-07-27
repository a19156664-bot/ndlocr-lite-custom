import pytest
from custom_gui.app import OcrState, get_ocr_status_text, SelectableImageViewer

def test_ocr_status_text_generation():
    assert get_ocr_status_text(OcrState.IDLE) == "OCR pending..."
    assert get_ocr_status_text(OcrState.RUNNING) == "OCR processing..."
    assert get_ocr_status_text(OcrState.ERROR) == "OCR failed"
    assert get_ocr_status_text(OcrState.DONE, 26) == "Lines: 26"

def test_viewer_init_does_not_run_ocr(monkeypatch):
    ocr_called = False
    
    def fake_run_ocr(*args, **kwargs):
        nonlocal ocr_called
        ocr_called = True
        return []
        
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", fake_run_ocr)
    
    # Pass arbitrary paths/dims to create the viewer
    # Since we mocked the OCR function, if __init__ still calls it, ocr_called will be True.
    viewer = SelectableImageViewer(
        image_src="dummy.jpg", 
        img_w=100, img_h=100, 
        win_w=100, win_h=100
    )
    
    assert ocr_called is False
    assert viewer.ocr_results == []

def test_update_selections_ui_no_crash_with_empty_ocr(monkeypatch):
    viewer = SelectableImageViewer(
        image_src="dummy.jpg", 
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

def test_on_ocr_complete_success():
    viewer = SelectableImageViewer(
        image_src="dummy.jpg", 
        img_w=100, img_h=100, 
        win_w=100, win_h=100
    )
    
    mock_results = [
        {"text": "Line 1", "bbox": (0, 0, 10, 10), "confidence": 0.9, "is_vertical": False, "source_image": "dummy.jpg"},
        {"text": "Line 2", "bbox": (0, 10, 10, 20), "confidence": 0.9, "is_vertical": False, "source_image": "dummy.jpg"}
    ]
    
    viewer.progress_ring.visible = True
    viewer.ocr_state = OcrState.RUNNING
    
    viewer._on_ocr_complete(mock_results, None)
    
    assert viewer.progress_ring.visible is False
    assert viewer.ocr_state == OcrState.DONE
    assert len(viewer.ocr_results) == 2
    
    status_msg = viewer._get_status_message()
    assert "Lines: 2" in status_msg

def test_on_ocr_complete_error():
    viewer = SelectableImageViewer(
        image_src="dummy.jpg", 
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
