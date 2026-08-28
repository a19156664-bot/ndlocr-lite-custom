import pytest
from custom_gui.rtl import needs_rtl, count_rtl_lines, convert_right_to_left

def test_is_vertical_true_returns_false():
    # 1. is_vertical True, 10 characters -> needs_rtl is False
    line = {"text": "abcdefghij", "is_vertical": True}
    assert needs_rtl(line) is False

def test_is_vertical_false_and_10_chars_returns_true():
    # 2. is_vertical False, 10 characters -> needs_rtl is True
    line = {"text": "abcdefghij", "is_vertical": False}
    assert needs_rtl(line) is True

def test_is_vertical_false_and_1_char_returns_false():
    # 3. is_vertical False, 1 character -> needs_rtl is False
    line = {"text": "a", "is_vertical": False}
    assert needs_rtl(line) is False

def test_is_vertical_false_and_0_chars_returns_false():
    # 4. is_vertical False, 0 characters -> needs_rtl is False
    line = {"text": "", "is_vertical": False}
    assert needs_rtl(line) is False

def test_dict_without_is_vertical_returns_false_no_exception():
    # 5. dict without "is_vertical" -> needs_rtl is False, no exception
    line = {"text": "abcdefghij"}
    assert needs_rtl(line) is False

def test_dict_without_text_returns_false_no_exception():
    # 6. dict without "text" -> needs_rtl is False, no exception
    line = {"is_vertical": False}
    assert needs_rtl(line) is False

def test_count_rtl_lines_empty():
    # 7. count_rtl_lines([]) == 0
    assert count_rtl_lines([]) == 0

def test_count_rtl_lines_with_qualifying_lines():
    # 8. A list of 5 lines, 2 of which qualify -> count_rtl_lines == 2
    lines = [
        {"text": "ab", "is_vertical": False},  # qualifies
        {"text": "abcdefghij", "is_vertical": True},  # vertical
        {"text": "a", "is_vertical": False},  # too short
        {"text": "abc", "is_vertical": False}, # qualifies
        {"text": "abcdefghij"}, # missing is_vertical
    ]
    assert count_rtl_lines(lines) == 2

def test_count_rtl_lines_with_malformed_dict():
    # 9. count_rtl_lines on a list containing one malformed dict counts the good
    #    ones and does not raise.
    lines = [
        {"text": "ab", "is_vertical": False},  # qualifies
        "not a dict", # malformed
        {"text": "abc", "is_vertical": False}, # qualifies
    ]
    assert count_rtl_lines(lines) == 2

def test_real_reversed_example():
    # 10. A real reversed example: build the dict
    #     {"text": "局支クーヨーユニ合聯聞新", "is_vertical": False, "bbox": (0, 0, 400, 20)}
    #     assert needs_rtl is True, and assert that
    #     `convert_right_to_left(line["text"])` equals "新聞聯合ニユーヨーク支局".
    line = {
        "text": "局支クーヨーユニ合聯聞新",
        "is_vertical": False,
        "bbox": (0, 0, 400, 20)
    }
    assert needs_rtl(line) is True
    assert convert_right_to_left(line["text"]) == "新聞聯合ニユーヨーク支局"
