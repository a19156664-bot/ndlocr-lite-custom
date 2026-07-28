import pytest
import threading
import flet as ft
from custom_gui.app import SelectableImageViewer
from unittest.mock import MagicMock, patch

def test_race():
    v = SelectableImageViewer("dummy.jpg", 1000, 1000, 800, 800)
    v.page = MagicMock()
    
    # Mock all updates to prevent Flet AssertionError in headless
    def mock_update(*args, **kwargs):
        pass
    v.rects_layer.update = mock_update
    v.highlight_layer.update = mock_update
    v.selections_list.update = mock_update
    v.image_control.update = mock_update
    
    v.mode_state.current = "PAN"
    v.ocr_results = []
    for i in range(120):
        v.ocr_results.append({"bbox": (10, i*10, 100, i*10+8), "text": f"Line {i}"})
    v.selection_container.add((0, 0, 500, 2000))
    v._update_selections_ui()
    
    errors = []
    
    def worker():
        try:
            for i in range(20):
                # Fake event class with local_x, local_y
                class DummyEvent:
                    local_x = i
                    local_y = i
                
                e = DummyEvent()
                v.drag_start_point = (0, 0)
                v.drag_current_point = (i-1, i-1)
                v._on_pan_update(e)
        except Exception as ex:
            errors.append(ex)
            
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    assert not errors

def test_update_selections_ui_concurrent():
    v = SelectableImageViewer("dummy.jpg", 1000, 1000, 800, 800)
    v.page = MagicMock()

    def mock_update(*args, **kwargs):
        pass
    v.rects_layer.update = mock_update
    v.highlight_layer.update = mock_update
    v.selections_list.update = mock_update

    
    v.ocr_results = [{"bbox": (10, i*10, 100, i*10+8), "text": f"Line {i}"} for i in range(120)]
    v.selection_container.add((0, 0, 500, 2000))
    
    errors = []
    
    def worker():
        try:
            for _ in range(20):
                v._update_selections_ui()
        except Exception as ex:
            errors.append(ex)
            
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    assert not errors
    assert len(v.highlight_layer.controls) == 120

def test_control_creation_count():
    v = SelectableImageViewer("dummy.jpg", 1000, 1000, 800, 800)
    v.page = MagicMock()
    
    def mock_update(*args, **kwargs):
        pass
    v.rects_layer.update = mock_update
    v.highlight_layer.update = mock_update
    v.selections_list.update = mock_update
    v.image_control.update = mock_update
    
    v.mode_state.current = "PAN"
    v.ocr_results = [{"bbox": (10, i*10, 100, i*10+8), "text": f"Line {i}"} for i in range(10)]
    v.selection_container.add((0, 0, 500, 100))
    v._update_selections_ui()
    
    initial_highlight_count = len(v.highlight_layer.controls)
    assert initial_highlight_count == 10
    
    class DummyEvent:
        local_x = 10
        local_y = 10
        
    e = DummyEvent()
    v.drag_start_point = (0, 0)
    v.drag_current_point = (5, 5)
    
    for _ in range(5):
        v._on_pan_update(e)
        
    assert len(v.highlight_layer.controls) == 10

@patch('custom_gui.app.SelectableImageViewer._switch_image')
@patch('custom_gui.batch_ocr.run_batch')
def test_batch_worker_no_switch_image(mock_run_batch, mock_switch_image):
    v = SelectableImageViewer("dummy.jpg", 1000, 1000, 800, 800)
    v.page = MagicMock()
    class DummySequence:
        def __init__(self):
            self._paths = ['dummy.jpg']
            self.index = 0
            self.count = 1
    v.sequence = DummySequence()
    v.pdf_page_map = {}
    v.btn_batch_ocr = MagicMock()
    v.status_row = MagicMock()
    
    class DummyResult:
        skipped = []
        ok = ["dummy.jpg"]
        failed = []
        cancelled = False
    mock_run_batch.return_value = DummyResult()
    
    v._run_batch_worker(["dummy.jpg"])
    
    assert mock_switch_image.call_count == 0

def test_pan_alignment():
    v = SelectableImageViewer("dummy.jpg", 1000, 1000, 800, 800)
    v.page = MagicMock()
    
    def mock_update(*args, **kwargs):
        pass
    v.rects_layer.update = mock_update
    v.highlight_layer.update = mock_update
    v.selections_list.update = mock_update
    v.image_control.update = mock_update
    
    v.zoom_scale = 1.5
    v.offset_x = 10.0
    v.offset_y = 20.0
    
    v.ocr_results = [{"bbox": (10, 10, 100, 50), "text": "Line 1"}]
    v.selection_container.add((0, 0, 500, 100))
    
    v._update_selections_ui()
    
    # Check layer position
    assert v.highlight_layer.left == 10.0
    assert v.highlight_layer.top == 20.0
    
    class DummyEvent:
        local_x = 100
        local_y = 100
        
    e = DummyEvent()
    v.drag_start_point = (0, 0)
    v.drag_current_point = (50, 50)
    v.mode_state.current = "PAN"
    
    v._on_pan_update(e)
    
    # 10 + (100 - 50) = 60
    # 20 + (100 - 50) = 70
    assert v.offset_x == 60.0
    assert v.offset_y == 70.0
    assert v.highlight_layer.left == 60.0
    assert v.highlight_layer.top == 70.0

def test_batch_worker_zoom_offset():
    v = SelectableImageViewer("dummy.jpg", 1000, 1000, 800, 800)
    v.page = MagicMock()
    class DummySequence:
        def __init__(self):
            self._paths = ['dummy.jpg']
            self.index = 0
            self.count = 1
    v.sequence = DummySequence()
    v.pdf_page_map = {}
    v.btn_batch_ocr = MagicMock()
    v.status_row = MagicMock()
    v.zoom_scale = 0.2605
    v.offset_x = 10.0
    v.offset_y = 20.0
    
    with patch('custom_gui.batch_ocr.run_batch') as mock_run_batch:
        class DummyResult:
            skipped = []
            ok = ["dummy.jpg"]
            failed = []
            cancelled = False
        mock_run_batch.return_value = DummyResult()
        
        v._run_batch_worker(["dummy.jpg"])
        
    assert v.zoom_scale == 0.2605
    assert v.offset_x == 10.0
    assert v.offset_y == 20.0
