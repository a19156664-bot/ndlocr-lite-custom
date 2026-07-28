from custom_gui.ocr_scheduler import OcrScheduler
from custom_gui.app import SelectableImageViewer, OcrState
import pytest
import os
from unittest.mock import MagicMock

def test_ocr_scheduler_idle():
    scheduler = OcrScheduler()
    # (a) A request when idle returns "start this one"
    assert scheduler.request_ocr("page1") is True
    assert scheduler.running_page == "page1"
    assert scheduler.pending_page is None

def test_ocr_scheduler_pending():
    scheduler = OcrScheduler()
    scheduler.request_ocr("page1")
    
    # (b) A request while one is running returns "do not start", and the pending page is recorded.
    assert scheduler.request_ocr("page2") is False
    assert scheduler.running_page == "page1"
    assert scheduler.pending_page == "page2"

def test_ocr_scheduler_three_requests():
    scheduler = OcrScheduler()
    scheduler.request_ocr("page1")
    scheduler.request_ocr("page2")
    scheduler.request_ocr("page3")
    
    # (c) Three requests while one is running leave only the LAST as pending.
    assert scheduler.running_page == "page1"
    assert scheduler.pending_page == "page3"

def test_ocr_scheduler_completion_next_page():
    scheduler = OcrScheduler()
    scheduler.request_ocr("page1")
    scheduler.request_ocr("page2")
    
    # (d) On completion, the next page to start is the one the caller says is currently displayed, when it still needs OCR.
    next_page = scheduler.on_ocr_complete(completed_page="page1", current_page="page2", page_needs_ocr=True)
    assert next_page == "page2"
    # The application is supposed to call request_ocr again for next_page to actually start it.
    assert scheduler.running_page is None
    assert scheduler.pending_page is None
    
    # Verify the application calling request_ocr successfully starts it
    assert scheduler.request_ocr("page2") is True
    assert scheduler.running_page == "page2"

def test_ocr_scheduler_completion_idle():
    scheduler = OcrScheduler()
    scheduler.request_ocr("page1")
    scheduler.request_ocr("page2")
    
    # (e) On completion, when the currently displayed page no longer needs OCR, nothing starts and the scheduler is idle.
    next_page = scheduler.on_ocr_complete(completed_page="page1", current_page="page2", page_needs_ocr=False)
    assert next_page is None
    assert scheduler.running_page is None
    assert scheduler.pending_page is None

def test_ocr_scheduler_completion_clears_running():
    scheduler = OcrScheduler()
    scheduler.request_ocr("page1")
    
    # (f) Completion of a job clears "running" even if no new job starts.
    next_page = scheduler.on_ocr_complete(completed_page="page1", current_page="page1", page_needs_ocr=False)
    assert next_page is None
    assert scheduler.running_page is None

def test_ocr_scheduler_same_page():
    scheduler = OcrScheduler()
    scheduler.request_ocr("page1")
    
    # (g) Requesting the SAME page that is already running does not start a second job.
    assert scheduler.request_ocr("page1") is False
    assert scheduler.running_page == "page1"
    assert scheduler.pending_page is None

def test_app_level_ocr_call_count(monkeypatch):
    image_path = os.path.join("resource", "digidepo_2531162_0024.jpg")
    
    # We want to count how many times OCR is actually started
    call_count = 0
    
    def fake_run_ocr(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return []
        
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", fake_run_ocr)
    
    viewer = SelectableImageViewer(
        image_src=image_path,
        img_w=100, img_h=100,
        win_w=100, win_h=100
    )
    
    # Add dummy pages to sequence
    # Since ImageSequence creates them dynamically, we should initialize it with these dummy paths
    dummy_paths = [f"dummy_page_{i}.png" for i in range(5)]
    SelectionContainer = __import__('custom_gui.selection', fromlist=['SelectionContainer']).SelectionContainer
    for p in dummy_paths:
        viewer.image_states[p] = {
            "selections": SelectionContainer(), "ocr_state": OcrState.IDLE, "ocr_results": [], "ocr_error": None, "edits": {}
        }
    viewer.sequence = __import__('custom_gui.image_sequence', fromlist=['ImageSequence']).ImageSequence(dummy_paths)
    
    # Mock threading to just execute directly to simplify, but we don't even need that 
    # since we just call start_ocr which queues it or runs it. Let's make page.run_thread synchronous for test.
    class MockPage:
        def run_thread(self, target, *args, **kwargs):
            target(*args, **kwargs)
            
        def update(self):
            pass
            
    viewer.page = MockPage()
    
    # Since run_thread is synchronous here, we can't test "navigating while running" easily 
    # unless we block the run_thread. Let's patch start_ocr's page.run_thread to DO NOTHING for a moment.
    # We just want to see how many times _run_ocr actually gets called.
    
    # A better way is to capture the target tasks and run them manually if we want, or just verify the scheduler.
    
    # Let's intercept run_thread to just store the tasks
    tasks = []
    
    # Also patch button updates since viewer is not really added to page
    viewer.btn_prev.update = lambda: None
    viewer.btn_next.update = lambda: None
    viewer.image_container.update = lambda: None
    viewer.image_control.update = lambda: None
    viewer.status_row.update = lambda: None
    viewer.highlight_layer.update = lambda: None
    viewer.rects_layer.update = lambda: None
    viewer.selections_list.update = lambda: None
    viewer.status_text.update = lambda: None

    class ThreadRecordingPage:
        def run_thread(self, target, *args, **kwargs):
            tasks.append((target, args, kwargs))
        def update(self): pass
        
    viewer.page = ThreadRecordingPage()
    
    # We mock _switch_image loading from PIL to not crash since dummy_page_{i}.png doesn't exist
    class FakeImage:
        def __init__(self, *args, **kwargs):
            self.size = (100, 100)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
            
    monkeypatch.setattr("PIL.Image.open", FakeImage)

    # We navigate 5 times quickly
    for i in range(5):
        # make sure to patch exists so it stays IDLE instead of ERROR
        monkeypatch.setattr("os.path.exists", lambda path: True)
        viewer._switch_image(f"dummy_page_{i}.png")
        
    # Since we intercept `run_thread` without executing `target`, 
    # the first task will remain running according to our scheduler.
    # Subsequent calls to `start_ocr` will see something is running and return without calling run_thread.
    assert len(tasks) == 1
