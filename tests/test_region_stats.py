from custom_gui.region_stats import count_line_breaks

def test_count_line_breaks():
    assert count_line_breaks("") == 0
    assert count_line_breaks("abc") == 0
    assert count_line_breaks("a\nb") == 1
    assert count_line_breaks("a\r\nb") == 1
    assert count_line_breaks("a\nb\n") == 1
    assert count_line_breaks("a\nb\r\n") == 1
    assert count_line_breaks("a\n\nb") == 2
    assert count_line_breaks(None) == 0
