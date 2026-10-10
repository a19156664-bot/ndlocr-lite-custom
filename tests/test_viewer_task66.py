"""Task 66: 頁番号を入れて Enter か「移動」で、その頁へ飛ぶ（承認者 10-10 案甲）。"""
from unittest.mock import patch, MagicMock

import flet as ft
import pytest
from PIL import Image

from custom_gui.app import SelectableImageViewer
from custom_gui.image_sequence import ImageSequence, page_index_from_text


class MockPage:
    def run_thread(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


@pytest.mark.parametrize("text,count,want", [
    ("5", 68, 4),
    ("1", 68, 0),
    ("68", 68, 67),
    (" 3 ", 68, 2),
    ("１２", 68, 11),   # 全角の数字
    ("0", 68, None),
    ("69", 68, None),
    ("", 68, None),
    (None, 68, None),
    ("abc", 68, None),
    ("-1", 68, None),
    ("2.5", 68, None),
    ("²", 68, None),    # isdigit は真だが int にできない字
    ("1", 0, None),     # 頁が無い
])
def test_1_page_index_from_text(text, count, want):
    assert page_index_from_text(text, count) == want


@pytest.fixture
def viewer(tmp_path):
    paths = []
    for i in range(4):
        p = tmp_path / f"p{i + 1}.png"
        Image.new("RGB", (200, 150), color="white").save(p)
        paths.append(str(p))
    with patch("custom_gui.app.run_ocr_and_parse", return_value=[]):
        v = SelectableImageViewer(image_src=paths[0], img_w=200, img_h=150, win_w=1000, win_h=800, expand=True)
        v.sequence = ImageSequence(paths)
        v.btn_prev.update = MagicMock()
        v.btn_next.update = MagicMock()
        v.status_row.update = MagicMock()
        v.status_text = MagicMock()
        v.selections_list.update = MagicMock()
        v.image_container.update = MagicMock()
        v.page = MockPage()
        v._switch_image(paths[0])
        yield v, paths


def jump(v, text, how="button"):
    v.page_jump_field.value = text
    if how == "enter":
        v.page_jump_field.on_submit(None)
    else:
        v.btn_page_jump.on_click(None)


def test_2_toolbar_order(viewer):
    """「前へ」「次へ」のすぐ右に、入力欄と「移動」が並ぶ。"""
    v, _ = viewer
    c = v.controls_row.controls
    i = c.index(v.btn_next)
    assert c[i - 1] is v.btn_prev
    assert c[i + 1] is v.page_jump_field
    assert c[i + 2] is v.btn_page_jump
    assert isinstance(v.page_jump_field, ft.TextField)
    assert v.btn_page_jump.text == "移動"


def test_3_jump_by_button(viewer):
    v, paths = viewer
    with patch("custom_gui.app.run_ocr_and_parse", return_value=[]):
        jump(v, "3")
    assert v.sequence.index == 2
    assert v.image_src == paths[2]
    assert v.page_jump_field.value == ""
    assert v.btn_prev.disabled is False and v.btn_next.disabled is False


def test_4_jump_by_enter_to_last(viewer):
    v, paths = viewer
    with patch("custom_gui.app.run_ocr_and_parse", return_value=[]):
        jump(v, "4", how="enter")
    assert v.sequence.index == 3
    assert v.image_src == paths[3]
    assert v.btn_next.disabled is True     # 最後の頁では「次へ」が押せない


@pytest.mark.parametrize("text", ["0", "5", "abc", ""])
def test_5_out_of_range_stays(viewer, text):
    """範囲の外・数でないときは移らず、下の帯で知らせる。入力は消さない（直して打ち直せるように）。"""
    v, paths = viewer
    with patch("custom_gui.app.run_ocr_and_parse", return_value=[]):
        jump(v, "2")
        jump(v, text)
    assert v.sequence.index == 1
    assert v.image_src == paths[1]
    assert "1〜4" in v.latest_region_info
    assert v.page_jump_field.value == text


def test_6_same_page_does_not_reload(viewer):
    v, paths = viewer
    v._switch_image = MagicMock()
    jump(v, "1")
    v._switch_image.assert_not_called()
    assert v.page_jump_field.value == ""


def test_7_edits_survive_round_trip(viewer):
    """飛ぶ前の頁の枠と直した文字は保存され、戻ると元どおり（前へ／次へと同じ道を通る）。"""
    v, paths = viewer
    v.selection_container.add((10, 10, 60, 40))
    rid = v.selection_container.get_all()[-1].rect_id
    v.edits[rid] = "直した字"
    with patch("custom_gui.app.run_ocr_and_parse", return_value=[]):
        jump(v, "3")
        assert v.image_src == paths[2]
        assert rid not in v.edits
        jump(v, "1")
    assert v.image_src == paths[0]
    assert v.edits.get(rid) == "直した字"
    assert [r.rect_id for r in v.selection_container.get_all()].count(rid) == 1
