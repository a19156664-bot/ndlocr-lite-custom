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
