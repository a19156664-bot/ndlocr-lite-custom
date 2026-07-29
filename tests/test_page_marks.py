import os
import pytest
from custom_gui.page_marks import MARK_AD, MARK_COVER, mark_line, append_mark_line

def test_mark_line():
    assert mark_line("a/b/foo.jpg", MARK_AD) == "foo.jpg\t【広告】"
    assert mark_line("C:\\scan\\foo.jpg", MARK_COVER) == "foo.jpg\t【表紙】"
    assert mark_line("foo.jpg", MARK_AD) == "foo.jpg\t【広告】"
    assert "\n" not in mark_line("foo.jpg", MARK_AD)

def test_append_mark_line(tmp_path):
    txt_path = tmp_path / "test.txt"
    line = "foo.jpg\t【広告】"
    
    # Missing file
    assert append_mark_line(str(txt_path), line) is True
    assert txt_path.read_text(encoding='utf-8') == "foo.jpg\t【広告】\n"
    
    # Existing file with other content
    txt_path.write_text("other\n", encoding='utf-8')
    assert append_mark_line(str(txt_path), line) is True
    assert txt_path.read_text(encoding='utf-8') == "other\nfoo.jpg\t【広告】\n"
    
    # Same line already present
    assert append_mark_line(str(txt_path), line) is False
    assert txt_path.read_text(encoding='utf-8') == "other\nfoo.jpg\t【広告】\n"
    
    # File whose last line has no trailing newline
    txt_path.write_text("foo.jpg\t【広告】", encoding='utf-8')
    assert append_mark_line(str(txt_path), line) is False
