from custom_gui.viewer import calculate_label_position

def test_label_position_plenty_of_room():
    # A rectangle with plenty of room above, e.g. rect_top = 300 and label_height = 20
    # Places the label ABOVE it.
    rect_left = 10.0
    rect_top = 300.0
    label_height = 20.0
    margin = 2.0
    
    label_left, label_top = calculate_label_position(rect_left, rect_top, label_height, margin)
    
    # Expected: 300 - 20 - 2 = 278
    assert label_top == 278.0
    assert label_top < 300.0
    assert label_left == 10.0

def test_label_position_left_edge_equals():
    # The label's left edge equals the rectangle's left edge
    label_left, _ = calculate_label_position(123.4, 300.0, 20.0)
    assert label_left == 123.4

def test_label_position_top_zero():
    # A rectangle at rect_top = 0 does NOT produce a negative y
    rect_left = 10.0
    rect_top = 0.0
    label_height = 20.0
    margin = 2.0
    
    label_left, label_top = calculate_label_position(rect_left, rect_top, label_height, margin)
    
    # Expected: max(0.0, 0 + 2.0) = 2.0
    assert label_top == 2.0
    assert label_top >= 0.0

def test_label_position_not_enough_room():
    # A rectangle at rect_top = 5 with label_height = 20 (not enough room)
    # also does NOT produce a negative y.
    rect_left = 10.0
    rect_top = 5.0
    label_height = 20.0
    margin = 2.0
    
    label_left, label_top = calculate_label_position(rect_left, rect_top, label_height, margin)
    
    # Expected: 5 - 20 - 2 = -17 (negative), so fallback: max(0.0, 5 + 2.0) = 7.0
    assert label_top == 7.0
    assert label_top >= 0.0
