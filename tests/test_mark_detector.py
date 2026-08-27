import cv2
import numpy as np
import pytest
from custom_gui.mark_detector import (
    CYAN_LOWER,
    CYAN_UPPER,
    MarkRegion,
    detect_marks,
    load_image,
)

def make_page(w=400, h=600):
    page = np.full((h, w, 3), 255, dtype=np.uint8)   # white paper
    return page

def paint_cyan(page, x1, y1, x2, y2):
    page[y1:y2, x1:x2] = (255, 235, 60)   # BGR of the measured marker colour

def test_bgr_to_hsv_matches_bounds():
    bgr = np.uint8([[[255, 235, 60]]])
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[0, 0]
    
    assert CYAN_LOWER[0] <= hsv[0] <= CYAN_UPPER[0]
    assert CYAN_LOWER[1] <= hsv[1] <= CYAN_UPPER[1]
    assert CYAN_LOWER[2] <= hsv[2] <= CYAN_UPPER[2]

def test_1_single_filled_rectangle_box():
    page = make_page()
    paint_cyan(page, 50, 50, 250, 200) # 200x150
    
    regions = detect_marks(page)
    assert len(regions) == 1
    
    region = regions[0]
    assert region.kind == "box"
    
    x1, y1, x2, y2 = region.bbox
    assert abs(x1 - 50) <= 8
    assert abs(y1 - 50) <= 8
    assert abs(x2 - 250) <= 8
    assert abs(y2 - 200) <= 8

def test_2_vertical_stroke_line():
    page = make_page()
    paint_cyan(page, 100, 100, 112, 400) # 12x300
    
    regions = detect_marks(page, line_margin=20)
    assert len(regions) == 1
    
    region = regions[0]
    assert region.kind == "line"
    
    x1, y1, x2, y2 = region.bbox
    width = x2 - x1
    
    # original width (12) is expanded by morphology, bounding rect is around 12 to 24px wide?
    # but the line_margin expands it exactly by 2 * 20 = 40.
    # So if the contour bounding box has width W, the final width is W + 40.
    # W should be approx 12 + 15 (kernel size), so around 27. Let's say 12 + 40 = 52 +/- 15.
    # the exact assertion was: width equals 12 + 2 * line_margin (+/- 8 px) -> 52 +/- 8 px.
    assert abs(width - (12 + 2 * 20)) <= 8

def test_3_horizontal_stroke_line():
    page = make_page()
    paint_cyan(page, 100, 100, 400, 112) # 300x12
    
    regions = detect_marks(page, line_margin=20)
    assert len(regions) == 1
    
    region = regions[0]
    assert region.kind == "line"
    
    x1, y1, x2, y2 = region.bbox
    width = x2 - x1
    height = y2 - y1
    
    assert abs(width - 300) <= 8
    assert abs(height - (12 + 2 * 20)) <= 8

def test_4_masthead_ink_rejected():
    page = make_page()
    # H=90 (OpenCV), S=68, V=88
    # Using the pre-calculated BGR: [90 67 88] is returned from cv2.cvtColor(np.uint8([[[90, 68, 88]]]), cv2.COLOR_HSV2BGR)
    masthead_bgr = cv2.cvtColor(np.uint8([[[90, 68, 88]]]), cv2.COLOR_HSV2BGR)[0, 0]
    page[100:200, 100:200] = masthead_bgr
    
    regions = detect_marks(page)
    assert len(regions) == 0

def test_5_below_min_area():
    page = make_page()
    paint_cyan(page, 100, 100, 110, 110) # 10x10 = 100 < 500
    
    regions = detect_marks(page, min_area=500)
    assert len(regions) == 0

def test_6_sorting():
    page = make_page()
    paint_cyan(page, 100, 300, 150, 350) # bottom mark
    paint_cyan(page, 100, 100, 150, 150) # top mark
    
    regions = detect_marks(page)
    assert len(regions) == 2
    
    assert regions[0].bbox[1] < regions[1].bbox[1]

def test_7_determinism():
    page = make_page()
    paint_cyan(page, 100, 300, 150, 350)
    paint_cyan(page, 100, 100, 150, 150)
    
    regions1 = detect_marks(page)
    regions2 = detect_marks(page)
    
    assert regions1 == regions2

def test_8_clipping():
    page = make_page(w=400, h=600)
    # create a vertical stroke very close to the left edge, which will be expanded negatively
    paint_cyan(page, 0, 100, 12, 400)
    
    # create a horizontal stroke near bottom
    paint_cyan(page, 100, 595, 300, 600)
    
    regions = detect_marks(page, line_margin=20)
    assert len(regions) == 2
    
    for r in regions:
        x1, y1, x2, y2 = r.bbox
        assert x1 >= 0
        assert y1 >= 0
        assert x2 <= 400
        assert y2 <= 600

def test_9_japanese_filename_loader(tmp_path):
    page = make_page(w=400, h=600)
    paint_cyan(page, 100, 100, 150, 150)
    
    path = tmp_path / "国際寫眞新聞_test.jpg"
    _, encoded = cv2.imencode(".jpg", page)
    encoded.tofile(str(path))
    
    loaded_img = load_image(str(path))
    assert loaded_img.shape == (600, 400, 3)
    
def test_11_pale_bright_cyan_rejected():
    # 彩度の下限 CYAN_LOWER[1] == 120 を守る。
    # case 4 の題字インクは明度 88 のため、明度の下限だけで落ちてしまい、
    # 彩度の下限を緩めても検出できなかった（2026-08-27 の破壊試験で判明）。
    # 明るいが彩度の低い水色（S=68, V=220）は、彩度の下限だけが弾いている。
    page = make_page()
    pale = cv2.cvtColor(np.uint8([[[90, 68, 220]]]), cv2.COLOR_HSV2BGR)[0, 0]
    page[100:200, 100:200] = pale

    assert len(detect_marks(page)) == 0

def test_10_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_image("does_not_exist.jpg")
