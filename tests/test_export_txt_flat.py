import pytest
from custom_gui.exporter import rows_to_txt_text, rows_to_csv_text

SEP = "｜"

def test_flat_txt_verbatim_example():
    # (a) The user's real example, verbatim.
    rows = [
        {"image_name": "a.jpg", "text": "印棉不買からシムラ會商まで"},
        {"image_name": "a.jpg", "text": "南千壽"},
        {"image_name": "a.jpg", "text": "―寫眞はカルナジタ・ハリソン街の綿糸布市場―"},
        {"image_name": "a.jpg", "text": "土人娘も流行を■ふ"},
        {"image_name": "a.jpg", "text": "デブの遺産四千圓"},
        {"image_name": "a.jpg", "text": "獨木船で世界一周"}
    ]
    out = rows_to_txt_text(rows)
    expected = "印棉不買からシムラ會商まで｜南千壽｜―寫眞はカルナジタ・ハリソン街の綿糸布市場―｜土人娘も流行を■ふ｜デブの遺産四千圓｜獨木船で世界一周\n"
    assert out == expected

def test_flat_txt_separator():
    # (b) The separator is U+FF5C, not an ASCII pipe.
    rows = [{"image_name": "a.jpg", "text": "A\nB"}]
    out = rows_to_txt_text(rows)
    assert SEP in out
    assert "|" not in out
    
def test_flat_txt_no_leading_trailing():
    # (c) No leading or trailing separator
    rows = [
        {"image_name": "a.jpg", "text": "\nA\nB\n"}
    ]
    out = rows_to_txt_text(rows)
    assert not out.startswith(SEP)
    assert not out.rstrip("\n").endswith(SEP)
    assert out == "A｜B\n"

def test_flat_txt_skip_empty_middle():
    # (d) An empty region in the middle is skipped
    rows = [
        {"image_name": "a.jpg", "text": "A"},
        {"image_name": "a.jpg", "text": ""},
        {"image_name": "a.jpg", "text": "B"}
    ]
    out = rows_to_txt_text(rows)
    assert out == "A｜B\n"

def test_flat_txt_skip_whitespace():
    # (e) A whitespace-only region is skipped
    rows = [
        {"image_name": "a.jpg", "text": "A"},
        {"image_name": "a.jpg", "text": "   "},
        {"image_name": "a.jpg", "text": "B"}
    ]
    out = rows_to_txt_text(rows)
    assert out == "A｜B\n"

def test_flat_txt_newlines_become_separators():
    # (f) Row containing \n becomes segments on ONE line. Also test \r\n.
    rows = [
        {"image_name": "a.jpg", "text": "A\nB\r\nC"}
    ]
    out = rows_to_txt_text(rows)
    # The output should just be one single line (plus the trailing \n)
    assert out.count("\n") == 1
    assert out == "A｜B｜C\n"

def test_flat_txt_multi_image():
    # (g) Two images produce two lines with tab separation
    rows = [
        {"image_name": "img1.jpg", "text": "A"},
        {"image_name": "img2.jpg", "text": "B\nC"}
    ]
    out = rows_to_txt_text(rows)
    expected = "img1.jpg\tA\nimg2.jpg\tB｜C\n"
    assert out == expected

def test_flat_txt_multi_image_empty_skipped():
    # (h) With several images, an image whose rows are all empty produces no line
    rows = [
        {"image_name": "img1.jpg", "text": "A"},
        {"image_name": "img2.jpg", "text": ""},
        {"image_name": "img2.jpg", "text": "   "},
        {"image_name": "img3.jpg", "text": "C"}
    ]
    out = rows_to_txt_text(rows)
    expected = "img1.jpg\tA\nimg3.jpg\tC\n"
    assert out == expected
    assert len(out.strip().split("\n")) == 2

def test_flat_txt_empty_rows():
    # (i) Empty rows returns empty string
    assert rows_to_txt_text([]) == ""

def test_csv_unaffected():
    # (j) CSV is unaffected
    rows = [
        {"image_name": "img1.jpg", "region_id": "1", "x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 10.0, "line_count": 1, "text": "A\nB"},
    ]
    csv_out = rows_to_csv_text(rows)
    # Assert header and data exactly as before
    expected = "image_name,region_id,x1,y1,x2,y2,line_count,text\nimg1.jpg,1,0.0,0.0,10.0,10.0,1,\"A\nB\"\n"
    assert csv_out == expected

