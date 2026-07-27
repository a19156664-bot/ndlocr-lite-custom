import pytest
from custom_gui.rtl import convert_right_to_left
from custom_gui.app import SelectableImageViewer
from custom_gui.selection import SelectionContainer

def test_convert_right_to_left_digits():
    assert convert_right_to_left("1234567890") == "0987654321"

def test_convert_right_to_left_disambiguation():
    # The exact disambiguation case: lines reversed independently, order kept
    assert convert_right_to_left("ABC\n123") == "CBA\n321"
    assert convert_right_to_left("ABC\n123") != "123\nABC"

def test_convert_right_to_left_real_data():
    input_text = "く近が嬢ヒツリトイデの染馴おんさ皆（合聯發ドツウリハ）\n。すで眞寫の中度支おるす演出に１風暴］書映トンウマラバ"
    expected = "（ハリウツド發聯合）皆さんお馴染のデイトリツヒ嬢が近く\nバラマウント映書［暴風１に出演するお支度中の寫眞です。"
    assert convert_right_to_left(input_text) == expected

def test_convert_right_to_left_bracket_mirroring():
    assert convert_right_to_left("「あい」") == "「いあ」"
    
def test_convert_right_to_left_unmatched_bracket():
    assert convert_right_to_left("あいう）") == "（ういあ"
    
def test_convert_right_to_left_self_inverse():
    s1 = "（ハリウツド發聯合）皆さんお馴染のデイトリツヒ嬢が近く"
    s2 = "This is a test\nWith a trailing newline\n"
    s3 = "A single line with no trailing newline"
    
    assert convert_right_to_left(convert_right_to_left(s1)) == s1
    assert convert_right_to_left(convert_right_to_left(s2)) == s2
    assert convert_right_to_left(convert_right_to_left(s3)) == s3

def test_convert_right_to_left_line_order_3_lines():
    assert convert_right_to_left("Line1\nLine2\nLine3") == "1eniL\n2eniL\n3eniL"

def test_convert_right_to_left_empty_and_newline():
    assert convert_right_to_left("") == ""
    assert convert_right_to_left("\n") == "\n"

class MockPage:
    def __init__(self):
        self.controls = []
        self.overlay = []
    def add(self, *controls):
        pass
    def update(self):
        pass

def test_rtl_rect_handler():
    app = SelectableImageViewer("dummy.jpg", 100, 100, 800, 600)
    app.page = MockPage()
    
    image_path = "dummy.jpg"
    app.image_states[image_path] = {
        "selections": SelectionContainer(),
        "ocr_state": None,
        "ocr_results": [{"bbox": [0,0,10,10], "text": "123"}],
        "ocr_error": None,
        "edits": {}
    }
    app.images = [image_path]
    app.current_image_index = 0
    
    app.selection_container.add((0, 0, 10, 10), "Region 1")
    rect = app.selection_container.get_all()[0]
    
    # Emulate the closure behavior inside _update_selections_ui
    extracted_text = "123"
    current_text = extracted_text
    
    def rtl_rect(rid, curr, orig):
        converted = convert_right_to_left(curr)
        if converted == orig:
            if rid in app.edits:
                del app.edits[rid]
        else:
            app.edits[rid] = converted
    
    # Press 1
    rtl_rect(rect.rect_id, current_text, extracted_text)
    assert app.edits[rect.rect_id] == "321"
    
    # Press 2
    rtl_rect(rect.rect_id, app.edits[rect.rect_id], extracted_text)
    assert rect.rect_id not in app.edits
