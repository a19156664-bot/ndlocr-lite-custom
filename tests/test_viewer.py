import pytest
import math
from custom_gui.viewer import original_to_display, display_to_original, calculate_fit_scale

def test_coordinate_conversion_scale_1_0():
    x, y = 100.0, 200.0
    scale = 1.0
    
    dx, dy = original_to_display(x, y, scale)
    rx, ry = display_to_original(dx, dy, scale)
    
    assert math.isclose(x, rx)
    assert math.isclose(y, ry)

def test_coordinate_conversion_scale_2_0():
    x, y = 150.0, 300.0
    scale = 2.0
    
    dx, dy = original_to_display(x, y, scale)
    rx, ry = display_to_original(dx, dy, scale)
    
    assert math.isclose(x, rx)
    assert math.isclose(y, ry)

def test_coordinate_conversion_scale_0_5():
    x, y = 50.0, 75.0
    scale = 0.5
    
    dx, dy = original_to_display(x, y, scale)
    rx, ry = display_to_original(dx, dy, scale)
    
    assert math.isclose(x, rx)
    assert math.isclose(y, ry)

def test_coordinate_conversion_with_offset():
    x, y = 100.0, 200.0
    scale = 1.5
    offset_x = 50.0
    offset_y = -30.0
    
    dx, dy = original_to_display(x, y, scale, offset_x, offset_y)
    rx, ry = display_to_original(dx, dy, scale, offset_x, offset_y)
    
    assert math.isclose(x, rx)
    assert math.isclose(y, ry)

def test_calculate_fit_scale():
    # Image wider than window (aspect ratio-wise)
    img_w, img_h = 1000.0, 500.0
    win_w, win_h = 500.0, 500.0
    # Window ratio = 1.0
    # Image ratio = 2.0
    # To fit entirely, scale must be determined by width: 500 / 1000 = 0.5
    scale = calculate_fit_scale(img_w, img_h, win_w, win_h)
    assert math.isclose(scale, 0.5)
    
    # Image taller than window (aspect ratio-wise)
    img_w, img_h = 500.0, 1000.0
    win_w, win_h = 500.0, 500.0
    # To fit entirely, scale must be determined by height: 500 / 1000 = 0.5
    scale = calculate_fit_scale(img_w, img_h, win_w, win_h)
    assert math.isclose(scale, 0.5)

def test_calculate_fit_scale_zero():
    scale = calculate_fit_scale(0.0, 0.0, 500.0, 500.0)
    assert scale == 1.0

