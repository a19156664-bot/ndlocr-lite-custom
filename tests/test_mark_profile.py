import os
import pytest
import cv2
import numpy as np
import flet as ft
from custom_gui.mark_profile import current_mark_color, page_mark_enabled, MARK_COLOR_ENV

def test_9_env_unset(monkeypatch):
    monkeypatch.delenv(MARK_COLOR_ENV, raising=False)
    assert current_mark_color() == "cyan"
    assert page_mark_enabled() is True

def test_10_env_lime(monkeypatch):
    monkeypatch.setenv(MARK_COLOR_ENV, "lime")
    assert current_mark_color() == "lime"
    assert page_mark_enabled() is False

def test_11_env_lime_spaced(monkeypatch):
    monkeypatch.setenv(MARK_COLOR_ENV, " LIME ")
    assert current_mark_color() == "lime"
    assert page_mark_enabled() is False

def test_12_env_bogus_and_empty(monkeypatch):
    monkeypatch.setenv(MARK_COLOR_ENV, "bogus")
    assert current_mark_color() == "cyan"
    assert page_mark_enabled() is True
    
    monkeypatch.setenv(MARK_COLOR_ENV, "")
    assert current_mark_color() == "cyan"
    assert page_mark_enabled() is True

def test_13_call_time_read(monkeypatch):
    monkeypatch.delenv(MARK_COLOR_ENV, raising=False)
    assert current_mark_color() == "cyan"
    
    monkeypatch.setenv(MARK_COLOR_ENV, "lime")
    assert current_mark_color() == "lime"

from custom_gui.app import SelectableImageViewer
from custom_gui.page_marks import MARK_AD

class DummyPage:
    def __init__(self):
        self.controls = []
        self.overlay = []
    def add(self, *controls):
        pass
    def update(self, *args):
        pass
    def run_thread(self, target, *args, **kwargs):
        target(*args, **kwargs)

@pytest.fixture
def dummy_page():
    return DummyPage()

from unittest.mock import MagicMock

def get_app(dummy_page, tmp_path, image_maker, w=400, h=600):
    page_img = image_maker(w, h)
    path = tmp_path / "test.jpg"
    _, encoded = cv2.imencode(".jpg", page_img)
    encoded.tofile(str(path))
    
    app = SelectableImageViewer(str(path), w, h, 800, 600)
    app.page = dummy_page
    app.selections_list.update = MagicMock()
    app.status_text.update = MagicMock()
    app.image_control.update = MagicMock()
    app.controls_row.update = MagicMock()
    
    return app, path

def make_lime_and_orange_page(w, h):
    page = np.full((h, w, 3), 255, dtype=np.uint8)
    
    # Lime box (H=45, S=180, V=230, 200x150)
    lime_bgr = cv2.cvtColor(np.uint8([[[45, 180, 230]]]), cv2.COLOR_HSV2BGR)[0, 0]
    page[50:200, 50:250] = lime_bgr
    
    # Orange blob (H=25, S=159, V=237, 120x120)
    orange_bgr = cv2.cvtColor(np.uint8([[[25, 159, 237]]]), cv2.COLOR_HSV2BGR)[0, 0]
    page[300:420, 100:220] = orange_bgr
    
    return page

def make_cyan_only_page(w, h):
    page = np.full((h, w, 3), 255, dtype=np.uint8)
    page[50:200, 50:250] = (255, 235, 60)
    return page

def test_14_lime_env_button_click(dummy_page, tmp_path, monkeypatch):
    monkeypatch.setenv(MARK_COLOR_ENV, "lime")
    app, _ = get_app(dummy_page, tmp_path, make_lime_and_orange_page)
    
    app._on_marks_to_rects_click(None)
    
    rects = app.selection_container.get_all()
    assert len(rects) == 1
    assert app.mark != MARK_AD

def test_15_unset_env_button_click(dummy_page, tmp_path, monkeypatch):
    monkeypatch.delenv(MARK_COLOR_ENV, raising=False)
    app, _ = get_app(dummy_page, tmp_path, make_lime_and_orange_page)
    
    app._on_marks_to_rects_click(None)
    
    rects = app.selection_container.get_all()
    assert len(rects) == 0
    assert app.mark == MARK_AD

def test_16_lime_env_cyan_box(dummy_page, tmp_path, monkeypatch):
    monkeypatch.setenv(MARK_COLOR_ENV, "lime")
    app, _ = get_app(dummy_page, tmp_path, make_cyan_only_page)
    
    app._on_marks_to_rects_click(None)
    
    rects = app.selection_container.get_all()
    assert len(rects) == 0
    assert "マークが見つかりません" in app.status_text.value

def test_17_tooltip_dynamic(dummy_page, tmp_path, monkeypatch):
    # lime
    monkeypatch.setenv(MARK_COLOR_ENV, "lime")
    app, _ = get_app(dummy_page, tmp_path, make_cyan_only_page)
    assert app.btn_marks_to_rects.tooltip == "黄緑のマークから矩形を作る"
    
    # unset
    monkeypatch.delenv(MARK_COLOR_ENV, raising=False)
    app2, _ = get_app(dummy_page, tmp_path, make_cyan_only_page)
    assert app2.btn_marks_to_rects.tooltip == "水色のマークから矩形を作る"
