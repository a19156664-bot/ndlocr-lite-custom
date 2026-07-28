import pytest
from custom_gui.exporter import rows_to_txt_text, rows_to_csv_text

SEP = "｜"

def test_flat_txt_verbatim_example():
    # The original example, updated with image prefix
    rows = [
        {"image_name": "a.jpg", "text": "印棉不買からシムラ會商まで"},
        {"image_name": "a.jpg", "text": "南千壽"},
        {"image_name": "a.jpg", "text": "―寫眞はカルナジタ・ハリソン街の綿糸布市場―"},
        {"image_name": "a.jpg", "text": "土人娘も流行を■ふ"},
        {"image_name": "a.jpg", "text": "デブの遺産四千圓"},
        {"image_name": "a.jpg", "text": "獨木船で世界一周"}
    ]
    out = rows_to_txt_text(rows)
    expected = "a.jpg\t印棉不買からシムラ會商まで｜南千壽｜―寫眞はカルナジタ・ハリソン街の綿糸布市場―｜土人娘も流行を■ふ｜デブの遺産四千圓｜獨木船で世界一周\n"
    assert out == expected
    assert out.count("\t") == 1

def test_flat_txt_real_example():
    # (a) The user's real example: one image named "A案）国際寫眞新聞_028号_000008.jpg"
    rows = [
        {"image_name": "A案）国際寫眞新聞_028号_000008.jpg", "text": "人の時"},
        {"image_name": "A案）国際寫眞新聞_028号_000008.jpg", "text": "桂冠するか?押し切るか?"},
        {"image_name": "A案）国際寫眞新聞_028号_000008.jpg", "text": "靜かに「非常時」を眺める沈默の人牧野内大臣"},
        {"image_name": "A案）国際寫眞新聞_028号_000008.jpg", "text": "(T生)"},
        {"image_name": "A案）国際寫眞新聞_028号_000008.jpg", "text": "国際ヴアリエテ"},
        {"image_name": "A案）国際寫眞新聞_028号_000008.jpg", "text": "フランスの國營富■"},
        {"image_name": "A案）国際寫眞新聞_028号_000008.jpg", "text": "三十五年目に結婚"},
        {"image_name": "A案）国際寫眞新聞_028号_000008.jpg", "text": "世界珍レコード"},
    ]
    out = rows_to_txt_text(rows)
    expected = "A案）国際寫眞新聞_028号_000008.jpg\t人の時｜桂冠するか?押し切るか?｜靜かに「非常時」を眺める沈默の人牧野内大臣｜(T生)｜国際ヴアリエテ｜フランスの國營富■｜三十五年目に結婚｜世界珍レコード\n"
    assert out == expected
    # (b) The line contains exactly ONE tab character
    assert out.count("\t") == 1

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
    # Skip image name for leading/trailing separator check
    content = out.split("\t", 1)[1] if "\t" in out else out
    assert not content.startswith(SEP)
    assert not content.rstrip("\n").endswith(SEP)
    assert out == "a.jpg\tA｜B\n"
    assert out.count("\t") == 1

def test_flat_txt_skip_empty_middle():
    # (d) An empty region in the middle is skipped
    rows = [
        {"image_name": "a.jpg", "text": "A"},
        {"image_name": "a.jpg", "text": ""},
        {"image_name": "a.jpg", "text": "B"}
    ]
    out = rows_to_txt_text(rows)
    assert out == "a.jpg\tA｜B\n"
    assert out.count("\t") == 1

def test_flat_txt_skip_whitespace():
    # (e) A whitespace-only region is skipped
    rows = [
        {"image_name": "a.jpg", "text": "A"},
        {"image_name": "a.jpg", "text": "   "},
        {"image_name": "a.jpg", "text": "B"}
    ]
    out = rows_to_txt_text(rows)
    assert out == "a.jpg\tA｜B\n"
    assert out.count("\t") == 1

def test_flat_txt_newlines_become_separators():
    # (f) Row containing \n becomes segments on ONE line. Also test \r\n.
    rows = [
        {"image_name": "a.jpg", "text": "A\nB\r\nC"}
    ]
    out = rows_to_txt_text(rows)
    # The output should just be one single line (plus the trailing \n)
    assert out.count("\n") == 1
    assert out == "a.jpg\tA｜B｜C\n"
    assert out.count("\t") == 1

def test_flat_txt_all_empty():
    # (c) A single image whose regions are all empty produces ""
    rows = [
        {"image_name": "a.jpg", "text": ""},
        {"image_name": "a.jpg", "text": "   "}
    ]
    out = rows_to_txt_text(rows)
    assert out == ""

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

