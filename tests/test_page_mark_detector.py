import cv2
import numpy as np
import pytest
from custom_gui.mark_detector import detect_page_mark, detect_marks
from custom_gui.page_marks import MARK_AD

def make_page(w=400, h=600):
    return np.full((h, w, 3), 255, dtype=np.uint8)

def paint(page, x1, y1, x2, y2, hsv_triple):
    bgr = cv2.cvtColor(np.uint8([[hsv_triple]]), cv2.COLOR_HSV2BGR)[0, 0]
    page[y1:y2, x1:x2] = bgr

def test_1_blank_white_page():
    page = make_page()
    assert detect_page_mark(page) is None

def test_2_orange_patch_100x100():
    page = make_page()
    paint(page, 0, 0, 100, 100, (25, 159, 238))
    assert detect_page_mark(page) == MARK_AD

def test_3_cyan_patch_200x150():
    page = make_page()
    paint(page, 0, 0, 200, 150, (90, 158, 236))
    assert detect_page_mark(page) is None

def test_4_orange_and_cyan():
    page = make_page()
    paint(page, 0, 0, 100, 100, (25, 159, 238)) # orange
    paint(page, 100, 100, 300, 250, (90, 158, 236)) # cyan
    assert detect_page_mark(page) == MARK_AD

def test_5_orange_patch_below_min_area():
    page = make_page()
    paint(page, 0, 0, 40, 40, (25, 159, 238)) # 1600 px < 2000
    assert detect_page_mark(page) is None

def test_6_orange_patch_with_custom_min_area():
    page = make_page()
    paint(page, 0, 0, 40, 40, (25, 159, 238)) # 1600 px
    assert detect_page_mark(page, min_area=1000) == MARK_AD

def test_7_orange_hue_low_saturation_rejected():
    page = make_page()
    paint(page, 0, 0, 100, 100, (25, 68, 220)) # saturation 68 < 120
    assert detect_page_mark(page) is None

def test_8_orange_hue_low_value_rejected():
    page = make_page()
    paint(page, 0, 0, 100, 100, (25, 159, 88)) # value 88 < 180
    assert detect_page_mark(page) is None

def test_9_determinism():
    page = make_page()
    paint(page, 0, 0, 100, 100, (25, 159, 238))
    res1 = detect_page_mark(page)
    res2 = detect_page_mark(page)
    assert res1 == MARK_AD
    assert res1 == res2

def test_10_detect_marks_ignores_orange():
    page = make_page()
    paint(page, 0, 0, 100, 100, (25, 159, 238)) # only orange
    regions = detect_marks(page)
    assert regions == []

