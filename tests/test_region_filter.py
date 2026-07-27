import pytest
from custom_gui.region_filter import filter_lines_by_region

def create_line(bbox, text="dummy", confidence=1.0, is_vertical=False, source_image="dummy.jpg"):
    return {
        "text": text,
        "bbox": bbox,
        "confidence": confidence,
        "is_vertical": is_vertical,
        "source_image": source_image
    }

def test_region_filter_fully_contained():
    # (a) 完全内包: 選択矩形(0,0,100,100)、行bbox(10,10,50,50) → 含まれる
    rect = (0, 0, 100, 100)
    line = create_line((10, 10, 50, 50))
    result = filter_lines_by_region(rect, [line])
    assert len(result) == 1
    assert result[0] == line

def test_region_filter_completely_outside():
    # (b) 完全に外側: 選択矩形(0,0,100,100)、行bbox(200,200,250,250) → 含まれない
    rect = (0, 0, 100, 100)
    line = create_line((200, 200, 250, 250))
    result = filter_lines_by_region(rect, [line])
    assert len(result) == 0

def test_region_filter_partial_overlap_50_percent_or_more():
    # (c) 部分重なり・50%以上: 選択矩形(0,0,100,100)、行bbox(50,50,150,60)
    # 行の面積 100x10=1000、重なり 50x10=500 → 50%ちょうど → 含まれる
    rect = (0, 0, 100, 100)
    line = create_line((50, 50, 150, 60))
    result = filter_lines_by_region(rect, [line])
    assert len(result) == 1
    assert result[0] == line

def test_region_filter_partial_overlap_less_than_50_percent():
    # (d) 部分重なり・50%未満: 選択矩形(0,0,100,100)、行bbox(80,50,180,60)
    # 行の面積 100x10=1000、重なり 20x10=200 → 20% → 含まれない
    rect = (0, 0, 100, 100)
    line = create_line((80, 50, 180, 60))
    result = filter_lines_by_region(rect, [line])
    assert len(result) == 0

def test_region_filter_edge_contact_only():
    # (e) 境界接触のみ: 選択矩形(0,0,100,100)、行bbox(100,100,150,150)
    # 重なり面積0 → 含まれない
    rect = (0, 0, 100, 100)
    line = create_line((100, 100, 150, 150))
    result = filter_lines_by_region(rect, [line])
    assert len(result) == 0

def test_region_filter_degenerate_bbox():
    # (f) 退化bbox: 選択矩形(0,0,100,100)、行bbox(10,10,10,50)（幅0）→ 内包されるので含まれる
    rect = (0, 0, 100, 100)
    line1 = create_line((10, 10, 10, 50))  # Fully contained, width 0
    line2 = create_line((10, 10, 50, 10))  # Fully contained, height 0
    line3 = create_line((10, 10, 10, 10))  # Fully contained, width & height 0
    line4 = create_line((110, 10, 110, 50)) # Outside, width 0
    line5 = create_line((10, 10, 10, 150)) # Partially contained, width 0 (should not be included per rule)

    result = filter_lines_by_region(rect, [line1, line2, line3, line4, line5])
    assert len(result) == 3
    assert result[0] == line1
    assert result[1] == line2
    assert result[2] == line3

def test_region_filter_preserve_order():
    # (g) 順序保持: 5行を入力し、うち3行が該当する場合、戻り値の3行が入力時の順序と同じであること
    rect = (0, 0, 100, 100)
    lines = [
        create_line((10, 10, 50, 50), text="line1"),    # Includes
        create_line((200, 200, 250, 250), text="line2"),# Outside
        create_line((50, 50, 150, 60), text="line3"),   # Includes (50%)
        create_line((80, 50, 180, 60), text="line4"),   # Outside (<50%)
        create_line((20, 20, 60, 60), text="line5")     # Includes
    ]
    result = filter_lines_by_region(rect, lines)
    assert len(result) == 3
    assert result[0]["text"] == "line1"
    assert result[1]["text"] == "line3"
    assert result[2]["text"] == "line5"

def test_region_filter_empty_result():
    # (h) 該当0件の場合に空リストが返ること（None やエラーではないこと）
    rect = (0, 0, 100, 100)
    lines = [
        create_line((200, 200, 250, 250)),
        create_line((80, 50, 180, 60))
    ]
    result = filter_lines_by_region(rect, lines)
    assert isinstance(result, list)
    assert len(result) == 0

def test_region_filter_empty_input():
    rect = (0, 0, 100, 100)
    result = filter_lines_by_region(rect, [])
    assert isinstance(result, list)
    assert len(result) == 0
