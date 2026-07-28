import os
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from custom_gui.app import SelectableImageViewer, OcrState
from custom_gui.image_sequence import ImageSequence
from custom_gui.pdf_loader import build_source_list

class MockPage:
    def run_thread(self, fn, *args):
        fn(*args)

def mock_all_updates(viewer):
    # Only mock the things that are safe to mock (not inside the stack, and not under test)
    viewer.btn_prev.update = MagicMock()
    viewer.btn_next.update = MagicMock()
    viewer.status_row.update = MagicMock()
    viewer.status_text = MagicMock()
    viewer.selections_list.update = MagicMock()
    # image_container itself doesn't detach
    viewer.image_container.update = MagicMock()
    # page mock to pretend we are attached
    viewer.page = MockPage()

@patch("custom_gui.app.run_ocr_and_parse")
def test_missing_image_recovery(mock_run_ocr, tmp_path):
    mock_run_ocr.return_value = []
    
    # Create a real image
    good_img_path = str(tmp_path / "good.jpg")
    img = Image.new('RGB', (800, 600), color='white')
    img.save(good_img_path)
    
    missing_img_path = str(tmp_path / "missing.jpg")
    
    viewer = SelectableImageViewer(
        image_src=good_img_path,
        img_w=800,
        img_h=600,
        win_w=1000,
        win_h=800,
        expand=True
    )
    viewer.sequence = ImageSequence([good_img_path, missing_img_path])
    mock_all_updates(viewer)
    
    # Cycle 1: Go to missing image
    viewer._switch_image(missing_img_path)
    assert viewer.ocr_error is not None
    assert "not found" in viewer.ocr_error
    assert viewer.image_states[missing_img_path]["ocr_state"] == OcrState.ERROR
    
    # Cycle 1: Go back to good image
    viewer._switch_image(good_img_path)
    assert viewer.ocr_error is None
    
    # Cycle 2: Go to missing image again
    viewer._switch_image(missing_img_path)
    assert viewer.ocr_error is not None
    assert "not found" in viewer.ocr_error
    
    # Cycle 2: Go back to good image again
    viewer._switch_image(good_img_path)
    assert viewer.ocr_error is None


@patch("custom_gui.app.run_ocr_and_parse")
def test_pdf_cold_start(mock_run_ocr, tmp_path):
    mock_run_ocr.return_value = []
    
    pdf_path = str(tmp_path / "test.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.drawString(100, 100, "Page 1")
    c.showPage()
    c.drawString(100, 100, "Page 2")
    c.save()
    
    cache_dir = str(tmp_path / "cache")
    paths, registry = build_source_list(str(tmp_path), cache_dir)
    
    assert len(paths) == 2
    assert "test_p0001.png" in paths[0]
    
    # Start viewer on first PDF page (cold start, PNG doesn't exist yet)
    viewer = SelectableImageViewer(
        image_src="",
        img_w=800,
        img_h=600,
        win_w=1000,
        win_h=800,
        expand=True
    )
    viewer.sequence = ImageSequence(paths)
    viewer.pdf_page_map = registry
    viewer.pdf_cache_dir = cache_dir
    mock_all_updates(viewer)
    
    # We switch to the first page, which should render it successfully without crashing
    viewer._switch_image(paths[0])
    
    assert viewer.ocr_error is None
    assert viewer.ocr_state in (OcrState.IDLE, OcrState.DONE)
    assert os.path.exists(paths[0])
    # A4 at 300 DPI is 2481x3508
    assert viewer.img_w == 2481
    assert viewer.img_h == 3508
    
    # Navigate to second page
    viewer._switch_image(paths[1])
    assert viewer.ocr_error is None
    assert viewer.ocr_state in (OcrState.IDLE, OcrState.DONE)
    assert os.path.exists(paths[1])
    assert viewer.img_w == 2481
    assert viewer.img_h == 3508


@patch("custom_gui.app.run_ocr_and_parse")
def test_pdf_render_failure(mock_run_ocr, tmp_path):
    mock_run_ocr.return_value = []
    
    fake_pdf_path = str(tmp_path / "fake.pdf")
    with open(fake_pdf_path, "w") as f:
        f.write("This is not a real PDF")
        
    cache_dir = str(tmp_path / "cache")
    png_path = os.path.join(cache_dir, "fake_p0001.png")
    
    viewer = SelectableImageViewer(
        image_src="",
        img_w=800,
        img_h=600,
        win_w=1000,
        win_h=800,
        expand=True
    )
    viewer.sequence = ImageSequence([png_path])
    viewer.pdf_page_map = {png_path: (fake_pdf_path, 0)}
    viewer.pdf_cache_dir = cache_dir
    mock_all_updates(viewer)
    
    viewer._switch_image(png_path)
    
    assert viewer.ocr_error is not None
    assert "Failed to render page" in viewer.ocr_error
    assert viewer.image_states[png_path]["ocr_state"] == OcrState.ERROR

@patch("custom_gui.app.run_ocr_and_parse")
def test_identity_preservation_after_recovery(mock_run_ocr, tmp_path):
    mock_run_ocr.return_value = []
    
    good_img_path = str(tmp_path / "good.jpg")
    img = Image.new('RGB', (800, 600), color='white')
    img.save(good_img_path)
    
    missing_img_path = str(tmp_path / "missing.jpg")
    
    viewer = SelectableImageViewer(
        image_src=good_img_path,
        img_w=800,
        img_h=600,
        win_w=1000,
        win_h=800,
        expand=True
    )
    viewer.sequence = ImageSequence([good_img_path, missing_img_path])
    mock_all_updates(viewer)
    
    # Store original object identities
    orig_stack = viewer.stack
    orig_highlight = viewer.highlight_layer
    orig_rects = viewer.rects_layer
    orig_image_control = viewer.image_control
    
    # Cycle 1: Go to missing image
    viewer._switch_image(missing_img_path)
    
    # Cycle 1: Go back to good image
    viewer._switch_image(good_img_path)
    
    # Verify identities
    assert viewer.image_container.content is viewer.stack
    assert viewer.stack is orig_stack
    assert viewer.highlight_layer is orig_highlight
    assert viewer.rects_layer is orig_rects
    assert viewer.image_control is orig_image_control

