import cv2
import numpy as np
import pytest
from custom_gui.mark_detector import (
    LIME_LOWER,
    LIME_UPPER,
    MarkRegion,
    detect_marks,
)

def make_page(w=400, h=600):
    return np.full((h, w, 3), 255, dtype=np.uint8)

def test_1_lime_bounds():
    assert LIME_LOWER == (35, 60, 140)
    assert LIME_UPPER == (75, 255, 255)

def test_2_lime_box():
    page = make_page()
    # Paint lime box H=45, S=180, V=230, 200x150 px
    lime_bgr = cv2.cvtColor(np.uint8([[[45, 180, 230]]]), cv2.COLOR_HSV2BGR)[0, 0]
    page[50:200, 50:250] = lime_bgr
    
    # Lime mark with lime config
    regions = detect_marks(page, color="lime")
    assert len(regions) == 1
    assert regions[0].kind == "box"
    x1, y1, x2, y2 = regions[0].bbox
    assert abs(x1 - 50) <= 8
    assert abs(y1 - 50) <= 8
    assert abs(x2 - 250) <= 8
    assert abs(y2 - 200) <= 8
    
    # Lime mark with cyan config
    assert len(detect_marks(page)) == 0

def test_3_cyan_box():
    page = make_page()
    page[50:200, 50:250] = (255, 235, 60) # BGR
    
    assert len(detect_marks(page)) == 1
    assert len(detect_marks(page, color="lime")) == 0

def test_4_lime_vertical_stroke():
    page = make_page()
    lime_bgr = cv2.cvtColor(np.uint8([[[45, 180, 230]]]), cv2.COLOR_HSV2BGR)[0, 0]
    page[100:400, 100:112] = lime_bgr # 12x300 px
    
    regions = detect_marks(page, color="lime", line_margin=20)
    assert len(regions) == 1
    assert regions[0].kind == "line"
    x1, y1, x2, y2 = regions[0].bbox
    width = x2 - x1
    assert abs(width - (12 + 40)) <= 8

def test_5_hue_boundaries():
    page = make_page()
    
    # H=34 -> 0
    bgr_34 = cv2.cvtColor(np.uint8([[[34, 180, 230]]]), cv2.COLOR_HSV2BGR)[0, 0]
    hsv_34 = cv2.cvtColor(np.uint8([[bgr_34]]), cv2.COLOR_BGR2HSV)[0, 0]
    assert tuple(hsv_34) == (34, 180, 230)
    page[50:150, 50:150] = bgr_34
    assert len(detect_marks(page, color="lime")) == 0
    
    # H=35 -> 1
    page = make_page()
    bgr_35 = cv2.cvtColor(np.uint8([[[35, 180, 230]]]), cv2.COLOR_HSV2BGR)[0, 0]
    hsv_35 = cv2.cvtColor(np.uint8([[bgr_35]]), cv2.COLOR_BGR2HSV)[0, 0]
    assert tuple(hsv_35) == (35, 180, 230)
    page[50:150, 50:150] = bgr_35
    assert len(detect_marks(page, color="lime")) == 1
    
    # H=75 -> 1
    page = make_page()
    bgr_75 = cv2.cvtColor(np.uint8([[[75, 180, 230]]]), cv2.COLOR_HSV2BGR)[0, 0]
    hsv_75 = cv2.cvtColor(np.uint8([[bgr_75]]), cv2.COLOR_BGR2HSV)[0, 0]
    assert tuple(hsv_75) == (75, 180, 230)
    page[50:150, 50:150] = bgr_75
    assert len(detect_marks(page, color="lime")) == 1
    
    # H=76 -> 0
    page = make_page()
    bgr_76 = cv2.cvtColor(np.uint8([[[76, 180, 230]]]), cv2.COLOR_HSV2BGR)[0, 0]
    hsv_76 = cv2.cvtColor(np.uint8([[bgr_76]]), cv2.COLOR_BGR2HSV)[0, 0]
    assert tuple(hsv_76) == (76, 180, 230)
    page[50:150, 50:150] = bgr_76
    assert len(detect_marks(page, color="lime")) == 0

def test_6_sat_val_boundaries():
    page = make_page()
    
    # S=59,V=230 -> 0 (H=45)
    bgr_s59 = cv2.cvtColor(np.uint8([[[45, 59, 230]]]), cv2.COLOR_HSV2BGR)[0, 0]
    hsv_s59 = cv2.cvtColor(np.uint8([[bgr_s59]]), cv2.COLOR_BGR2HSV)[0, 0]
    # To avoid rounding issues, we adjust if necessary
    if tuple(hsv_s59) != (45, 59, 230):
        # Fallback if precision lost in BGR conversion
        bgr_s59 = cv2.cvtColor(np.uint8([[[45, 59, 230]]]), cv2.COLOR_HSV2BGR)[0, 0]
        hsv_s59 = cv2.cvtColor(np.uint8([[bgr_s59]]), cv2.COLOR_BGR2HSV)[0, 0]
    assert tuple(hsv_s59) == (45, 59, 230)
    page[50:150, 50:150] = bgr_s59
    assert len(detect_marks(page, color="lime")) == 0
    
    # S=60,V=230 -> 1
    page = make_page()
    bgr_s60 = cv2.cvtColor(np.uint8([[[45, 60, 230]]]), cv2.COLOR_HSV2BGR)[0, 0]
    hsv_s60 = cv2.cvtColor(np.uint8([[bgr_s60]]), cv2.COLOR_BGR2HSV)[0, 0]
    assert tuple(hsv_s60) == (45, 60, 230)
    page[50:150, 50:150] = bgr_s60
    assert len(detect_marks(page, color="lime")) == 1
    
    # S=180,V=139 -> 0
    page = make_page()
    bgr_v139 = cv2.cvtColor(np.uint8([[[45, 180, 139]]]), cv2.COLOR_HSV2BGR)[0, 0]
    hsv_v139 = cv2.cvtColor(np.uint8([[bgr_v139]]), cv2.COLOR_BGR2HSV)[0, 0]
    assert tuple(hsv_v139) == (45, 180, 139)
    page[50:150, 50:150] = bgr_v139
    assert len(detect_marks(page, color="lime")) == 0
    
    # S=180,V=140 -> 1
    page = make_page()
    bgr_v140 = cv2.cvtColor(np.uint8([[[45, 180, 140]]]), cv2.COLOR_HSV2BGR)[0, 0]
    hsv_v140 = cv2.cvtColor(np.uint8([[bgr_v140]]), cv2.COLOR_BGR2HSV)[0, 0]
    assert tuple(hsv_v140) == (45, 180, 140)
    page[50:150, 50:150] = bgr_v140
    assert len(detect_marks(page, color="lime")) == 1

def test_7_invalid_color_raises():
    page = make_page()
    with pytest.raises(ValueError) as exc:
        detect_marks(page, color="red")
    assert "red" in str(exc.value)

def test_8_determinism():
    page = make_page()
    lime_bgr = cv2.cvtColor(np.uint8([[[45, 180, 230]]]), cv2.COLOR_HSV2BGR)[0, 0]
    page[50:200, 50:250] = lime_bgr
    
    regions1 = detect_marks(page, color="lime")
    regions2 = detect_marks(page, color="lime")
    assert regions1 == regions2
