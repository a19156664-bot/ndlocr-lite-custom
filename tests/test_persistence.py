import os
import json
import pytest
import time
from PIL import Image
import flet as ft
from unittest.mock import MagicMock

from custom_gui.app import SelectableImageViewer
from custom_gui.selection import SelectionRect
import custom_gui.work_state as work_state

@pytest.fixture
def real_images(tmp_path):
    img1_path = tmp_path / "img1.png"
    img2_path = tmp_path / "img2.png"
    
    img = Image.new("RGB", (100, 100), color="white")
    img.save(img1_path)
    img.save(img2_path)
    
    return str(img1_path), str(img2_path)

@pytest.fixture
def dummy_page():
    page = MagicMock(spec=ft.Page)
    page.overlay = []
    page.session = MagicMock()
    page.client_storage = MagicMock()
    page.window_width = 800
    page.window_height = 600
    return page

def create_app(image_path, page, monkeypatch):
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", lambda *args, **kwargs: [])
    app = SelectableImageViewer(image_src=image_path, img_w=100, img_h=100, win_w=800, win_h=600)
    app.page = page
    
    original_update = ft.Control.update
    def safe_update(self, *args, **kwargs):
        if not getattr(self, 'page', None) and not getattr(self, '_Control__page', None):
            return
        original_update(self, *args, **kwargs)
        
    monkeypatch.setattr(ft.Control, "update", safe_update)
    
    app.did_mount()
    return app

def draw_rect(app, x1, y1, x2, y2):
    app.mode_state.set_mode("SELECT")
    
    class MockControlEvent:
        def __init__(self, data):
            self.data = data
            self.target = ""
            self.name = ""
            self.control = MagicMock()
            self.page = MagicMock()

    mock_start_event = MockControlEvent(json.dumps({"lx": x1, "ly": y1}))
    start_ev = ft.DragStartEvent(mock_start_event)
    app._on_pan_start(start_ev)
    
    mock_update_event = MockControlEvent(json.dumps({"lx": x2, "ly": y2, "dx": x2-x1, "dy": y2-y1}))
    update_ev = ft.DragUpdateEvent(mock_update_event)
    app._on_pan_update(update_ev)
    
    mock_end_event = MockControlEvent("{}")
    end_ev = ft.DragEndEvent(mock_end_event)
    app._on_pan_end(end_ev)

def get_button(app, icon):
    app._update_selections_ui()
    for item in app.selections_list.controls:
        # Flet structure in custom_gui/app.py:
        # item is ft.Container -> content=ft.Column(controls=[ft.Row, content_area])
        if isinstance(item, ft.Container) and isinstance(item.content, ft.Column):
            def search(c):
                if isinstance(c, ft.IconButton) and c.icon == icon:
                    return c
                if hasattr(c, 'controls'):
                    for child in getattr(c, 'controls'):
                        res = search(child)
                        if res: return res
                elif hasattr(c, 'content') and c.content:
                    return search(c.content)
                return None
            
            res = search(item.content)
            if res:
                return res
    return None

def test_a_add_rectangle(real_images, dummy_page, monkeypatch):
    img1, _ = real_images
    app = create_app(img1, dummy_page, monkeypatch)
    
    draw_rect(app, 10, 10, 50, 50)
    
    work_path = work_state.work_path_for(img1)
    assert os.path.exists(work_path)
    
    with open(work_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert len(data["rects"]) == 1
    assert data["rects"][0]["bbox"][0] >= 0

def test_b_commit_edit_restore(real_images, dummy_page, monkeypatch):
    img1, img2 = real_images
    app = create_app(img1, dummy_page, monkeypatch)
    
    draw_rect(app, 10, 10, 50, 50)
    
    rects = app.selection_container.get_all()
    rect_id = rects[0].rect_id
    
    app.commit_edit(rect_id, "edited text")
    
    app2 = create_app(img1, dummy_page, monkeypatch)
    
    assert len(app2.selection_container.get_all()) == 1
    restored_rect = app2.selection_container.get_all()[0]
    assert restored_rect.rect_id == rect_id
    assert app2.edits[rect_id] == "edited text"

def test_c_mark_click(real_images, dummy_page, monkeypatch):
    img1, img2 = real_images
    app = create_app(img1, dummy_page, monkeypatch)
    
    class MockClickEvent:
        pass
    app.btn_mark_ad.on_click(MockClickEvent())
    
    app2 = create_app(img1, dummy_page, monkeypatch)
    assert app2.mark == "【広告】"

def test_d_delete_rect(real_images, dummy_page, monkeypatch):
    img1, img2 = real_images
    app = create_app(img1, dummy_page, monkeypatch)
    
    draw_rect(app, 10, 10, 50, 50)
    
    rects = app.selection_container.get_all()
    rect_id = rects[0].rect_id
    
    btn_del = get_button(app, ft.Icons.DELETE)
    assert btn_del is not None
    
    class MockClickEvent:
        pass
    btn_del.on_click(MockClickEvent())
    
    app2 = create_app(img1, dummy_page, monkeypatch)
    assert len(app2.selection_container.get_all()) == 0

def test_e_restore_rect_undo(real_images, dummy_page, monkeypatch):
    img1, _ = real_images
    app = create_app(img1, dummy_page, monkeypatch)
    
    draw_rect(app, 10, 10, 50, 50)
    
    rects = app.selection_container.get_all()
    rect_id = rects[0].rect_id
    
    app.commit_edit(rect_id, "edited text")
    
    btn_restore = get_button(app, ft.Icons.RESTORE)
    assert btn_restore is not None
    
    class MockClickEvent:
        pass
    btn_restore.on_click(MockClickEvent())
    
    work_path = work_state.work_path_for(img1)
    with open(work_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert rect_id not in data.get("edits", {})

def test_f_restore_and_add_new_rect(real_images, dummy_page, monkeypatch):
    img1, img2 = real_images
    app = create_app(img1, dummy_page, monkeypatch)
    
    draw_rect(app, 10, 10, 50, 50)
    rect_id = app.selection_container.get_all()[0].rect_id
    
    app.commit_edit(rect_id, "first edit")
    
    app._switch_image(img2)
    del app.image_states[img1]
    app._switch_image(img1)
    
    rects2 = app.selection_container.get_all()
    assert len(rects2) == 1
    
    draw_rect(app, 60, 60, 80, 80)
    
    rects3 = app.selection_container.get_all()
    new_rect_id = [r.rect_id for r in rects3 if r.rect_id != rect_id][0]
    
    app.commit_edit(new_rect_id, "new edit")
    
    del app.image_states[img1]
    app._switch_image(img2)
    app._switch_image(img1)
    
    assert app.edits[rect_id] == "first edit"
    assert app.edits[new_rect_id] == "new edit"

def test_g_changed_image_size(real_images, dummy_page, monkeypatch):
    img1, img2 = real_images
    app = create_app(img1, dummy_page, monkeypatch)
    
    draw_rect(app, 10, 10, 50, 50)
    
    time.sleep(0.01)
    img = Image.new("RGB", (200, 200), color="red")
    img.save(img1)
    
    # We must explicitly force _load_persisted_state to drop it by calling create_app
    app2 = create_app(img1, dummy_page, monkeypatch)
    
    assert len(app2.selection_container.get_all()) == 0

def test_h_corrupt_json(real_images, dummy_page, monkeypatch):
    img1, _ = real_images
    app = create_app(img1, dummy_page, monkeypatch)
    
    draw_rect(app, 10, 10, 50, 50)
    
    work_path = work_state.work_path_for(img1)
    with open(work_path, "w", encoding="utf-8") as f:
        f.write("{ invalid json")
        
    app2 = create_app(img1, dummy_page, monkeypatch)
    assert len(app2.selection_container.get_all()) == 0

def test_i_save_oserror(real_images, dummy_page, monkeypatch):
    img1, _ = real_images
    app = create_app(img1, dummy_page, monkeypatch)
    
    def mock_save(*args, **kwargs):
        raise OSError("Disk full")
        
    monkeypatch.setattr("custom_gui.app.work_state.save_work_state", mock_save)
    
    draw_rect(app, 10, 10, 50, 50)
    
    assert len(app.selection_container.get_all()) == 1

def test_j_save_nameerror(real_images, dummy_page, monkeypatch):
    img1, _ = real_images
    app = create_app(img1, dummy_page, monkeypatch)
    
    def mock_save(*args, **kwargs):
        raise NameError("Something is undefined")
        
    monkeypatch.setattr("custom_gui.app.work_state.save_work_state", mock_save)
    
    with pytest.raises(NameError):
        draw_rect(app, 10, 10, 50, 50)

def test_k_pdf_page(real_images, dummy_page, monkeypatch, tmp_path):
    img1, _ = real_images
    app = create_app(img1, dummy_page, monkeypatch)
    
    pdf_path = str(tmp_path / "fake_doc.pdf")
    
    with open(pdf_path, "w") as f:
        f.write("dummy")
        
    app.pdf_page_map[img1] = (pdf_path, 0)
    
    draw_rect(app, 10, 10, 50, 50)
    
    png_work_path = work_state.work_path_for(img1)
    pdf_work_path = work_state.work_path_for(pdf_path, page_index=0)
    
    assert not os.path.exists(png_work_path)
    assert os.path.exists(pdf_work_path)
