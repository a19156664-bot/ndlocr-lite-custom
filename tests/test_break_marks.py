from custom_gui.break_marks import add_break_marks, strip_break_marks, BREAK_MARK

def test_add_break_marks_1():
    assert add_break_marks("a\nb\nc") == f"a{BREAK_MARK}\nb{BREAK_MARK}\nc"

def test_add_break_marks_2():
    assert add_break_marks("a\r\nb") == f"a{BREAK_MARK}\nb"

def test_strip_break_marks_3():
    cases = ["", "abc", "a\nb", "a\n\nb\n", "先生が\n轉んだ"]
    for x in cases:
        assert strip_break_marks(add_break_marks(x)) == x

def test_strip_break_marks_4():
    assert strip_break_marks(f"a{BREAK_MARK}b{BREAK_MARK}\nc") == "ab\nc"

def test_none_5():
    assert add_break_marks(None) == ""
    assert strip_break_marks(None) == ""

def test_break_mark_value_6():
    assert BREAK_MARK == "\U0001F534"
