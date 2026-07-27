import pytest
import math
from custom_gui.selection import SelectionContainer, calculate_normalized_bbox

def test_calculate_normalized_bbox_a():
    # (a) Display (200, 400) -> scale=2.0, offset=(0,0) -> original (100, 200)
    # Let's say drag is from (0,0) to (200,400)
    bbox = calculate_normalized_bbox(
        0.0, 0.0, 200.0, 400.0,
        2.0,
        0.0, 0.0,
        1000.0, 1000.0
    )
    assert math.isclose(bbox[0], 0.0)
    assert math.isclose(bbox[1], 0.0)
    assert math.isclose(bbox[2], 100.0)
    assert math.isclose(bbox[3], 200.0)

def test_calculate_normalized_bbox_b():
    # (b) Display (250, 370) -> scale=2.0, offset=(50,-30) -> original (100, 200)
    # Let's say drag is from (50, -30) to (250, 370)
    bbox = calculate_normalized_bbox(
        50.0, -30.0, 250.0, 370.0,
        2.0,
        50.0, -30.0,
        1000.0, 1000.0
    )
    assert math.isclose(bbox[0], 0.0)
    assert math.isclose(bbox[1], 0.0)
    assert math.isclose(bbox[2], 100.0)
    assert math.isclose(bbox[3], 200.0)

def test_calculate_normalized_bbox_c():
    # (c) bottom-right to top-left normalization
    # Start (300, 300) -> End (100, 100), scale=1.0, offset=0
    # Original start (300, 300) -> End (100, 100) -> Normalized to (100, 100, 300, 300)
    bbox = calculate_normalized_bbox(
        300.0, 300.0, 100.0, 100.0,
        1.0,
        0.0, 0.0,
        1000.0, 1000.0
    )
    assert math.isclose(bbox[0], 100.0)
    assert math.isclose(bbox[1], 100.0)
    assert math.isclose(bbox[2], 300.0)
    assert math.isclose(bbox[3], 300.0)

def test_calculate_normalized_bbox_d():
    # (d) Clipping bounds
    # Image size 500x500. Drag Start (-50, -50) -> End (600, 600). scale=1.0, offset=0
    # Expected: (0, 0, 500, 500)
    bbox = calculate_normalized_bbox(
        -50.0, -50.0, 600.0, 600.0,
        1.0,
        0.0, 0.0,
        500.0, 500.0
    )
    assert math.isclose(bbox[0], 0.0)
    assert math.isclose(bbox[1], 0.0)
    assert math.isclose(bbox[2], 500.0)
    assert math.isclose(bbox[3], 500.0)

def test_selection_container_add_delete():
    # (e) Add 3, delete middle, verify length and remaining IDs
    container = SelectionContainer()
    rect1 = container.add((10, 10, 20, 20))
    rect2 = container.add((30, 30, 40, 40))
    rect3 = container.add((50, 50, 60, 60))
    
    assert len(container.get_all()) == 3
    
    deleted = container.delete_by_id(rect2.rect_id)
    assert deleted is True
    
    rects = container.get_all()
    assert len(rects) == 2
    assert rects[0].rect_id == rect1.rect_id
    assert rects[1].rect_id == rect3.rect_id
