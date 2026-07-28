import pytest
import os
from PIL import Image
import flet as ft
from unittest.mock import MagicMock

from custom_gui.app import SelectableImageViewer, OcrState
import custom_gui.ocr_cache as ocr_cache
import custom_gui.batch_ocr as batch_ocr
from custom_gui.batch_ocr import BatchResult

@pytest.fixture
def temp_images(tmp_path):
    p1 = tmp_path / "img1.png"
    p2 = tmp_path / "img2.png"
    p3 = tmp_path / "img3.png"
    
    for p in [p1, p2, p3]:
        img = Image.new("RGB", (100, 100), color="white")
        img.save(p)
        
    return [str(p1), str(p2), str(p3)]


def create_mock_page():
    page = MagicMock(spec=ft.Page)
    # Ensure run_thread executes synchronously for testing purposes
    page.run_thread.side_effect = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    return page


def bypass_ui_updates(viewer):
    viewer.btn_prev.update = MagicMock()
    viewer.btn_next.update = MagicMock()
    viewer.image_container.update = MagicMock()
    viewer.status_row.update = MagicMock()
    viewer.btn_batch_ocr.update = MagicMock()
    viewer.status_text.update = MagicMock()
    viewer.selections_list.update = MagicMock()
    viewer.rects_layer.update = MagicMock()
    viewer.batch_progress_bar.update = MagicMock()

def test_cache_hit_skips_ocr(temp_images, monkeypatch):
    path = temp_images[0]
    
    mock_run_ocr = MagicMock(return_value=[{"text": "mock"}])
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", mock_run_ocr)
    
    # Save a known cache
    cached_data = [{"text": "cached_text", "bbox": [0,0,10,10]}]
    ocr_cache.save_cache(path, cached_data)
    
    viewer = SelectableImageViewer(path, 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    page_mock = create_mock_page()
    viewer.page = page_mock
    
    viewer._switch_image(path)
    
    assert viewer.ocr_state == OcrState.DONE
    print('viewer.ocr_results:', viewer.ocr_results, 'cached_data:', cached_data)
    expected_data = [{'text': 'cached_text', 'bbox': (0,0,10,10)}]
    assert viewer.ocr_results == expected_data
    assert mock_run_ocr.call_count == 0

def test_cache_miss_runs_ocr(temp_images, monkeypatch):
    path = temp_images[0]
    
    mock_run_ocr = MagicMock(return_value=[{"text": "mock"}])
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", mock_run_ocr)
    
    # Ensure no cache
    cache_path = ocr_cache.cache_path_for(path)
    if os.path.exists(cache_path):
        os.remove(cache_path)
        
    viewer = SelectableImageViewer(path, 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    page_mock = create_mock_page()
    viewer.page = page_mock
    
    viewer._switch_image(path)
    
    assert mock_run_ocr.call_count == 1

def test_pdf_page_skips_cache(temp_images, monkeypatch):
    path = temp_images[0]
    
    mock_run_ocr = MagicMock(return_value=[{"text": "mock"}])
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", mock_run_ocr)
    
    cached_data = [{"text": "cached_text_should_be_ignored", "box": [0,0,10,10]}]
    ocr_cache.save_cache(path, cached_data)
    
    viewer = SelectableImageViewer(path, 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    viewer.pdf_page_map[path] = ("dummy.pdf", 0)
    page_mock = create_mock_page()
    viewer.page = page_mock
    
    # Needs a mock ensure_page_rendered since it's a "pdf" path
    monkeypatch.setattr("custom_gui.app.ensure_page_rendered", MagicMock())
    
    viewer._switch_image(path)
    
    assert mock_run_ocr.call_count == 1
    assert viewer.ocr_results != cached_data
    
    # Verify cache is NOT written on success
    if os.path.exists(ocr_cache.cache_path_for(path)):
        os.remove(ocr_cache.cache_path_for(path))
    
    viewer._on_ocr_complete([{"text": "new_ocr"}], None, target_path=path)
    assert not os.path.exists(ocr_cache.cache_path_for(path))

def test_batch_button_runs_only_images(temp_images, monkeypatch):
    path1, path2, path3 = temp_images
    
    mock_run_batch = MagicMock(return_value=BatchResult(ok=[path1], skipped=[], failed=[], cancelled=False))
    monkeypatch.setattr(batch_ocr, "run_batch", mock_run_batch)
    
    viewer = SelectableImageViewer(path1, 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    viewer.sequence._paths = [path1, path2, path3]
    viewer.pdf_page_map[path2] = ("dummy.pdf", 0)
    page_mock = create_mock_page()
    viewer.page = page_mock
    
    viewer.btn_batch_ocr.on_click(MagicMock())
    
    mock_run_batch.assert_called_once()
    args, kwargs = mock_run_batch.call_args
    passed_paths = args[0]
    assert passed_paths == [path1, path3]

def test_lazy_ocr_skipped_during_batch(temp_images, monkeypatch):
    path = temp_images[0]
    
    mock_run_ocr = MagicMock()
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", mock_run_ocr)
    
    viewer = SelectableImageViewer(path, 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    page_mock = create_mock_page()
    viewer.page = page_mock
    
    viewer.batch_running = True
    viewer.start_ocr(page_mock, path)
    
    assert mock_run_ocr.call_count == 0

def test_status_string_updates_and_retains_segments(temp_images):
    path = temp_images[0]
    viewer = SelectableImageViewer(path, 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    
    viewer.batch_progress = (37, 164)
    status_msg = viewer._get_status_message()
    
    # Assert all original segments exist
    assert "File:" in status_msg
    assert "Size:" in status_msg
    assert "Scale:" in status_msg
    assert "Mode:" in status_msg
    assert "Last:" in status_msg
    
    # Assert new segment exists at the very end
    assert "| Pre-OCR: 37/164" in status_msg
    assert status_msg.endswith("| Pre-OCR: 37/164")

def test_batch_worker_post_batch_state(temp_images, monkeypatch):
    path = temp_images[0]
    
    # Mock batch_ocr to simulate completion
    mock_run_batch = MagicMock(return_value=BatchResult(ok=[path], skipped=[], failed=[], cancelled=False))
    monkeypatch.setattr(batch_ocr, "run_batch", mock_run_batch)
    
    viewer = SelectableImageViewer(path, 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    page_mock = create_mock_page()
    viewer.page = page_mock
    
    viewer.batch_running = True
    viewer._run_batch_worker([path])
    
    assert viewer.batch_running is False
    assert viewer.batch_progress is None
    assert viewer.btn_batch_ocr.icon == ft.Icons.DOCUMENT_SCANNER
    assert "Pre-OCR complete" in viewer.latest_region_info

def test_cancel_button_path(temp_images, monkeypatch):
    path = temp_images[0]
    
    viewer = SelectableImageViewer(path, 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    page_mock = create_mock_page()
    viewer.page = page_mock
    
    # We simulate a running batch and user clicks it again
    viewer.batch_running = True
    viewer._batch_cancel_requested = False
    
    viewer.btn_batch_ocr.on_click(MagicMock())
    
    assert viewer._batch_cancel_requested is True

def test_successful_lazy_ocr_writes_cache(temp_images, monkeypatch):
    path = temp_images[0]
    
    cache_path = ocr_cache.cache_path_for(path)
    if os.path.exists(cache_path):
        os.remove(cache_path)
        
    viewer = SelectableImageViewer(path, 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    page_mock = create_mock_page()
    viewer.page = page_mock
    
    results = [{"text": "success_lazy"}]
    viewer._on_ocr_complete(results, None, target_path=path)
    
    assert os.path.exists(cache_path)

def test_failed_lazy_ocr_does_not_write_cache(temp_images, monkeypatch):
    path = temp_images[0]
    
    cache_path = ocr_cache.cache_path_for(path)
    if os.path.exists(cache_path):
        os.remove(cache_path)
        
    viewer = SelectableImageViewer(path, 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    page_mock = create_mock_page()
    viewer.page = page_mock
    
    viewer._on_ocr_complete(None, "error", target_path=path)
    
    assert not os.path.exists(cache_path)

def test_regression_a_preview_offset(temp_images):
    viewer = SelectableImageViewer(temp_images[0], 1000, 1000, 800, 800)
    bypass_ui_updates(viewer)
    page_mock = create_mock_page()
    viewer.page = page_mock

    viewer.offset_x = 120.0
    viewer.offset_y = 80.0
    viewer.rects_layer.left = 120.0
    viewer.rects_layer.top = 80.0
    viewer.zoom_scale = 1.0
    viewer.mode_state.current = "SELECT"

    class DummyDragStart:
        local_x = 300
        local_y = 300
        
    viewer._on_pan_start(DummyDragStart())
    
    screen_left = viewer.active_rect.left + viewer.rects_layer.left
    screen_top = viewer.active_rect.top + viewer.rects_layer.top
    
    # Assert preview offset regression is fixed
    assert screen_left == 300.0
    assert screen_top == 300.0

def test_regression_a_committed_bbox_unchanged(temp_images):
    viewer = SelectableImageViewer(temp_images[0], 1000, 1000, 800, 800)
    bypass_ui_updates(viewer)
    page_mock = create_mock_page()
    viewer.page = page_mock

    viewer.offset_x = 120.0
    viewer.offset_y = 80.0
    viewer.rects_layer.left = 120.0
    viewer.rects_layer.top = 80.0
    viewer.zoom_scale = 1.0
    viewer.mode_state.current = "SELECT"

    class DummyDragStart:
        local_x = 300
        local_y = 300
        
    viewer._on_pan_start(DummyDragStart())
    viewer.active_rect.update = MagicMock()
    
    class DummyDragUpdate:
        local_x = 700
        local_y = 650
        
    viewer._on_pan_update(DummyDragUpdate())
    
    class DummyDragEnd:
        pass
        
    viewer._on_pan_end(DummyDragEnd())
    
    rects = viewer.selection_container.get_all()
    assert len(rects) == 1
    # Check exact committed bbox matches prior behaviour
    assert rects[0].bbox == (180.0, 220.0, 580.0, 570.0)


def test_batch_progress_counts_whole_folder(temp_images, monkeypatch):
    import custom_gui.ocr_cache as ocr_cache
    
    # 5 images, 2 cached
    paths = [f"tmp_{i}.jpg" for i in range(5)]
    
    def mock_is_cached(path):
        return path in (paths[0], paths[1])
        
    monkeypatch.setattr(ocr_cache, "is_cached", mock_is_cached)
    
    viewer = SelectableImageViewer(paths[0], 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    viewer.page = create_mock_page()
    
    # mock run_batch to capture progress updates
    progress_calls = []
    def mock_run_batch(candidate_paths, progress=None, should_cancel=None):
        # 2 were cached, 3 left to do
        progress(1, 3) # 1 finished this run
        progress(2, 3) # 2 finished this run
        progress(3, 3) # 3 finished this run
        return BatchResult(ok=paths[2:], skipped=paths[:2], failed=[], cancelled=False)
        
    monkeypatch.setattr(batch_ocr, "run_batch", mock_run_batch)
    
    # Capture the values assigned to batch_progress
    recorded_progress = []
    original_setattr = viewer.__class__.__setattr__
    def tracking_setattr(self, name, value):
        if name == "batch_progress" and value is not None:
            recorded_progress.append(value)
        original_setattr(self, name, value)
    
    # Replace setattr for viewer class
    SelectableImageViewer.__setattr__ = tracking_setattr
    
    try:
        viewer.batch_running = True
        viewer._run_batch_worker(paths)
    finally:
        SelectableImageViewer.__setattr__ = original_setattr
    
    print("Recorded progress:", recorded_progress)
    
    # Starts at 2/5 (initially_cached, total)
    assert recorded_progress[0] == (2, 5)
    
    # Ends at 5/5
    assert recorded_progress[-1] == (5, 5)


def test_progress_bar_visibility_and_zoom(temp_images, monkeypatch):
    import custom_gui.ocr_cache as ocr_cache
    
    paths = [f"tmp_{i}.jpg" for i in range(5)]
    def mock_is_cached(path):
        return False
    monkeypatch.setattr(ocr_cache, "is_cached", mock_is_cached)
    
    viewer = SelectableImageViewer(paths[0], 2218, 3071, 1600, 900)
    bypass_ui_updates(viewer)
    viewer.batch_progress_bar.update = MagicMock()
    viewer.page = create_mock_page()
    
    # Store initial zoom scale
    initial_zoom = viewer.zoom_scale
    
    # Assert invisible before
    assert viewer.batch_progress_bar.visible is False
    
    def mock_run_batch(candidate_paths, progress=None, should_cancel=None):
        # Assert visible during
        assert viewer.batch_progress_bar.visible is True
        progress(1, 5)
        # Assert value updates
        assert viewer.batch_progress_bar.value == 1 / 5
        return BatchResult(ok=paths[:5], skipped=[], failed=[], cancelled=False)
        
    monkeypatch.setattr(batch_ocr, "run_batch", mock_run_batch)
    
    viewer.batch_running = True
    viewer._run_batch_worker(paths)
    
    # Assert invisible after
    assert viewer.batch_progress_bar.visible is False
    
    # Assert zoom scale is unchanged
    assert viewer.zoom_scale == initial_zoom


def test_eta_and_progress_ring_during_batch(temp_images, monkeypatch):
    import custom_gui.ocr_cache as ocr_cache
    import time
    
    paths = [f"tmp_{i}.jpg" for i in range(5)]
    def mock_is_cached(path):
        return False
    monkeypatch.setattr(ocr_cache, "is_cached", mock_is_cached)
    
    viewer = SelectableImageViewer(paths[0], 2218, 3071, 1600, 900)
    bypass_ui_updates(viewer)
    viewer.batch_progress_bar.update = MagicMock()
    viewer.page = create_mock_page()
    
    original_time = time.time
    
    # Store initial progress ring state
    assert viewer.progress_ring.visible is False
    
    time_calls = [1000.0, 1010.0]
    time_idx = 0
    def mock_time():
        nonlocal time_idx
        if time_idx < len(time_calls):
            t = time_calls[time_idx]
            time_idx += 1
            return t
        return time_calls[-1]
    
    monkeypatch.setattr(time, "time", mock_time)
    
    def mock_run_batch(candidate_paths, progress=None, should_cancel=None):
        # Assert visible during
        assert viewer.progress_ring.visible is True
        
        # At this point, time=1000.0 was called at batch_start.
        # Now progress(1, 5) is called, which calls time.time() -> 1010.0
        # Elapsed = 10s. done = 1. per_page = 10s. remaining = 4. remaining_secs = 40.
        progress(1, 5)
        
        # Assert ETA string
        status_msg = viewer._get_status_message()
        assert "about 40 sec" in status_msg
        
        return BatchResult(ok=paths[:5], skipped=[], failed=[], cancelled=False)
        
    monkeypatch.setattr(batch_ocr, "run_batch", mock_run_batch)
    
    viewer.batch_running = True
    viewer._run_batch_worker(paths)
    
    # Assert invisible after
    assert viewer.progress_ring.visible is False


def test_batch_button_label_and_tooltip(temp_images):
    viewer = SelectableImageViewer(temp_images[0], 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    
    assert viewer.btn_batch_ocr.text == "Pre-OCR All"
    assert viewer.btn_batch_ocr.icon == ft.Icons.DOCUMENT_SCANNER
    
    viewer.page = create_mock_page()
    viewer.sequence._paths = temp_images
    
    # Mock run_thread to execute synchronously
    def sync_run_thread(target, *args):
        target(*args)
        
    viewer.page.run_thread = sync_run_thread
    
    import custom_gui.batch_ocr as batch_ocr
    import custom_gui.ocr_cache as ocr_cache
    
    original_run_batch = batch_ocr.run_batch
    
    try:
        def intercept_run_batch(*args, **kwargs):
            # Assert text is Cancel during execution
            assert viewer.btn_batch_ocr.text == "Cancel"
            assert viewer.btn_batch_ocr.icon == ft.Icons.CANCEL
            return BatchResult(ok=[], skipped=[], failed=[], cancelled=False)
            
        batch_ocr.run_batch = intercept_run_batch
        
        viewer._on_batch_ocr_click(MagicMock())
        
        # Assert restored to Pre-OCR All
        assert viewer.btn_batch_ocr.text == "Pre-OCR All"
        assert viewer.btn_batch_ocr.icon == ft.Icons.DOCUMENT_SCANNER
        
    finally:
        batch_ocr.run_batch = original_run_batch


def test_wait_for_lazy_ocr(temp_images):
    viewer = SelectableImageViewer(temp_images[0], 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    viewer.page = create_mock_page()
    viewer.sequence._paths = temp_images
    
    # Mark temp_images[0] as RUNNING lazy OCR
    viewer.image_states[temp_images[0]] = {"ocr_state": OcrState.RUNNING}
    
    # We will simulate time.sleep to break the loop or advance state
    import time
    original_sleep = time.sleep
    
    call_counts = {"run_batch_worker": 0}
    
    def mock_run_batch_worker(candidate_paths):
        call_counts["run_batch_worker"] += 1
        
    viewer._run_batch_worker = mock_run_batch_worker
    
    sleep_cycles = 0
    def mock_sleep(secs):
        nonlocal sleep_cycles
        sleep_cycles += 1
        if sleep_cycles == 1:
            # First cycle: test cancellation
            pass
        elif sleep_cycles == 2:
            # Second cycle: state becomes DONE
            viewer.image_states[temp_images[0]]["ocr_state"] = OcrState.DONE
            
    try:
        time.sleep = mock_sleep
        
        # Scenario 1: Cancellation during wait
        viewer._batch_cancel_requested = False
        viewer._on_batch_ocr_click(MagicMock())
        # Simulate click again to cancel
        viewer._on_batch_ocr_click(MagicMock())
        
        # Assert never called _run_batch_worker because it was cancelled
        # Wait, the thread loop runs synchronously in test since run_thread is mocked to run sync
        # So we need the mock sleep to trigger the cancel!
    finally:
        time.sleep = original_sleep


def test_wait_for_lazy_ocr(temp_images, monkeypatch):
    import time
    viewer = SelectableImageViewer(temp_images[0], 100, 100, 800, 600)
    bypass_ui_updates(viewer)
    viewer.page = create_mock_page()
    viewer.sequence._paths = temp_images
    
    viewer.image_states[temp_images[0]] = {"ocr_state": OcrState.RUNNING}
    
    calls = {"worker": 0}
    def mock_worker(paths):
        calls["worker"] += 1
    viewer._run_batch_worker = mock_worker
    
    sleep_count = 0
    def mock_sleep(secs):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count == 2:
            viewer._batch_cancel_requested = True
    
    monkeypatch.setattr(time, "sleep", mock_sleep)
    
    # 1. Click should block in while loop, then cancel
    viewer._on_batch_ocr_click(MagicMock())
    
    # Should not reach worker
    assert calls["worker"] == 0
    assert viewer.batch_running is False

    # 2. Reset and wait for completion
    sleep_count = 0
    viewer._batch_cancel_requested = False
    
    def mock_sleep_complete(secs):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count == 2:
            viewer.image_states[temp_images[0]]["ocr_state"] = OcrState.DONE
            
    monkeypatch.setattr(time, "sleep", mock_sleep_complete)
    
    viewer._on_batch_ocr_click(MagicMock())
    
    # Should reach worker this time
    assert calls["worker"] == 1
    assert "waiting for the current page" in viewer.latest_region_info

