import os
import pytest
import flet as ft
from unittest.mock import patch, MagicMock
from PIL import Image
from custom_gui.app import SelectableImageViewer, OcrState
from custom_gui.page_marks import MARK_AD, MARK_COVER

def create_dummy_image(path):
    img = Image.new('RGB', (100, 100), color='white')
    img.save(path)

@pytest.fixture
def viewer_app(tmp_path):
    img1 = str(tmp_path / "page1.jpg")
    img2 = str(tmp_path / "page2.jpg")
    create_dummy_image(img1)
    create_dummy_image(img2)
    
    with patch("custom_gui.app.run_ocr_and_parse") as mock_ocr:
        mock_ocr.return_value = []
        app = SelectableImageViewer(img1, 100, 100, 800, 600)
        app.sequence._paths = [img1, img2]
        
        # Attach dummy page for updates
        page = MagicMock()
        app.page = page
        app.rects_layer.page = page
        app.highlight_layer.page = page
        app.selections_list.page = page
        app.status_text = ft.Text("")
        app.status_text.page = page
        app.btn_prev.page = page
        app.btn_next.page = page
        app.image_container.page = page
        app.status_row.page = page
        
        return app, tmp_path, img1, img2

def walk_tree_for_text(control, text):
    if hasattr(control, "text") and control.text == text:
        return control
    if hasattr(control, "controls"):
        for c in control.controls:
            found = walk_tree_for_text(c, text)
            if found:
                return found
    if hasattr(control, "content"):
        return walk_tree_for_text(control.content, text)
    return None

def test_a_toolbar_buttons(viewer_app):
    app, _, _, _ = viewer_app
    btn_ad = walk_tree_for_text(app.controls_row, "広告")
    btn_cover = walk_tree_for_text(app.controls_row, "表紙")
    
    assert btn_ad is not None, "Button 広告 not found"
    assert btn_cover is not None, "Button 表紙 not found"
    assert btn_ad.tooltip == "このページを【広告】として記録"
    assert btn_cover.tooltip == "このページを【表紙】として記録"

def test_b_c_d_e_firing_buttons(viewer_app):
    app, tmp_path, img1, img2 = viewer_app
    
    # Test (b)
    txt_path = tmp_path / "page1.txt"
    app.btn_mark_ad.on_click(None)
    
    assert txt_path.exists()
    content = txt_path.read_text(encoding='utf-8')
    assert content == "page1.jpg\t【広告】\n"
    assert app._save_dialog is None
    
    # Test (c)
    app.btn_mark_ad.on_click(None)
    content2 = txt_path.read_text(encoding='utf-8')
    assert content2 == content # Byte-identical
    assert "既に記録済み" in app.latest_region_info
    
    # Test (d)
    app.btn_mark_cover.on_click(None)
    content3 = txt_path.read_text(encoding='utf-8')
    lines = content3.splitlines()
    assert len(lines) == 2
    assert lines[1] == "page1.jpg\t【表紙】"
    assert app.mark == "【表紙】"
    
    # Test (e)
    app._switch_image(img2)
    assert app.mark is None
    assert not app.mark_label.visible or app.mark_label.value == ""
    
    app._switch_image(img1)
    assert app.mark == "【表紙】"
    assert app.mark_label.value == "【表紙】"

def test_f_pdf_page(viewer_app):
    app, tmp_path, img1, img2 = viewer_app
    
    # Create fake pdf structure
    pdf_dir = tmp_path / "src"
    pdf_dir.mkdir()
    pdf_path = pdf_dir / "book.pdf"
    
    app.pdf_page_map[img1] = (str(pdf_path), 0)
    
    app.btn_mark_ad.on_click(None)
    
    txt_path = pdf_dir / "page1.txt"
    assert txt_path.exists()
    content = txt_path.read_text(encoding='utf-8')
    assert content == "page1.jpg\t【広告】\n"

def test_g_all_pages_export(viewer_app):
    app, tmp_path, img1, img2 = viewer_app
    
    # Image 1: has region, OCR done
    app._switch_image(img1)
    app.selection_container.add((10, 10, 50, 50), "p1")
    app.ocr_state = OcrState.DONE
    app.image_states[img1]["ocr_state"] = OcrState.DONE
    app.ocr_results = [{"bbox": (10,10,50,50), "text": "Hello", "confidence": 0.9, "is_vertical": False, "source_image": img1}]
    app.image_states[img1]["ocr_results"] = app.ocr_results
    
    # Image 2: NO region, NO OCR, but stamped
    app._switch_image(img2)
    app.image_states[img2]["ocr_state"] = OcrState.IDLE
    app.btn_mark_ad.on_click(None)
    
    # Fire export
    app._start_export("all")
    
    from custom_gui.save_paths import export_targets
    _, txt_path_str = export_targets(img1, "all")
    txt_path = tmp_path / os.path.basename(txt_path_str)
    assert txt_path.exists()
    content = txt_path.read_text(encoding='utf-8')
    
    lines = content.splitlines()
    assert len(lines) == 2
    assert lines[0] == "page1.jpg\tHello"
    assert lines[1] == "page2.jpg\t【広告】"
    
def test_h_save_stamped_page_retains_mark(viewer_app):
    app, tmp_path, img1, img2 = viewer_app
    
    app._switch_image(img1)
    # Give it a rect so we can export it (or the exporter handles 0 rects if marked?)
    # The requirement says: Saving a stamped page does not lose the stamp line.
    app.selection_container.add((10, 10, 50, 50), "p1")
    app.ocr_state = OcrState.DONE
    app.image_states[img1]["ocr_state"] = OcrState.DONE
    app.ocr_results = [{"bbox": (10,10,50,50), "text": "Hello", "confidence": 0.9, "is_vertical": False, "source_image": img1}]
    app.image_states[img1]["ocr_results"] = app.ocr_results
    
    # Press Mark
    app.btn_mark_ad.on_click(None)
    
    txt_path = tmp_path / "page1.txt"
    content_before = txt_path.read_text(encoding='utf-8')
    assert "page1.jpg\t【広告】" in content_before
    
    # Save the page using per-page save
    app._start_export("current")
    
    # Assert dialog appeared due to existing mark line
    assert app._save_dialog is not None
    assert app._save_dialog.title.value == "上書き確認"
    
    # Find and click the overwrite button
    overwrite_action = next(a for a in app._save_dialog.actions if a.text == "上書き保存")
    overwrite_action.on_click(None)
    
    # Actually export_targets is called internally and might save it to page1.txt or page1_current.txt. Let's check export_targets directly in save_paths.py
    from custom_gui.save_paths import export_targets
    _, txt_path_str = export_targets(img1, "current")
    txt_path = tmp_path / os.path.basename(txt_path_str)
    
    content_after = txt_path.read_text(encoding='utf-8')
    # Should still contain the mark
    assert "page1.jpg\t【広告】" in content_after
    assert "Hello" in content_after

