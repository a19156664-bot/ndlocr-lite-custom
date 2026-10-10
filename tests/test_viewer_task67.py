"""Task 67: 右の一覧の各枠に「頁と枠番号をコピー」ボタン（承認者 10-10）。
■■NG■■ の枠の「画像の名前 枠の札」をすぐ指揮官へ伝えるため。"""
import flet as ft
import pytest

from custom_gui.app import region_ref_text
from tests.test_marks_to_rects import get_app, make_clean_page

COPY = "頁と枠番号をコピー"


@pytest.mark.parametrize("src,label,want", [
    ("C:\\Users\\user\\work\\cache_images\\143号\\国際寫眞新聞_143号_p0014.png", "Region 3", "国際寫眞新聞_143号_p0014 Region 3"),
    ("C:/Users/user/work/国際寫眞新聞_141号_p0052.png", "Region 12", "国際寫眞新聞_141号_p0052 Region 12"),
    ("/tmp/x/p5.jpg", "Region 2", "p5 Region 2"),
    ("p7", "Region 2", "p7 Region 2"),       # 拡張子なし
    ("", "Region 2", "None Region 2"),
    (None, "Region 2", "None Region 2"),
])
def test_1_region_ref_text(src, label, want):
    assert region_ref_text(src, label) == want


@pytest.fixture
def dummy_page():
    class DummyPage:
        def __init__(self):
            self.controls = []
            self.overlay = []
            self.clipboard = []
        def add(self, *args):
            pass
        def update(self, *args):
            pass
        def run_thread(self, target, *args, **kwargs):
            target(*args, **kwargs)
        def set_clipboard(self, value):
            self.clipboard.append(value)
        window_width = 800
        window_height = 600
        session_id = "test"
    return DummyPage()


def prepared(dummy_page, tmp_path, edits=None):
    app, path = get_app(dummy_page, tmp_path, make_clean_page)
    app.ocr_results = []
    app.selection_container._rects = []
    r2 = app.selection_container.add((0, 0, 60, 30))
    r2.rect_id, r2.label = "2", "Region 2"
    r3 = app.selection_container.add((80, 80, 200, 200))
    r3.rect_id, r3.label = "3", "Region 3"
    app.edits = dict(edits or {})
    app.image_states[str(path)]["edits"] = app.edits
    app._update_selections_ui()
    return app


def buttons_of(row):
    return row.content.controls[0].controls[1].controls


def test_2_button_place(dummy_page, tmp_path):
    app = prepared(dummy_page, tmp_path)
    assert len(app.selections_list.controls) == 2
    for row in app.selections_list.controls:
        bs = buttons_of(row)
        assert [b.tooltip for b in bs] == ["Edit", "右から変換", "この枠だけOCR", "画像の枠を隠す", "縦で読む", COPY, "Delete"]
        assert bs[5].icon == ft.Icons.CONTENT_COPY
        assert row.content.controls[0].controls[1].wrap is True   # Task 67b: 幅を超えたら折り返す


def test_3_button_place_with_edit(dummy_page, tmp_path):
    app = prepared(dummy_page, tmp_path, edits={"3": "■■NG■■"})
    assert app.selections_list.controls[1].content.controls[0].controls[1].wrap is True
    bs = buttons_of(app.selections_list.controls[1])
    assert [b.tooltip for b in bs] == ["Edit", "右から変換", "この枠だけOCR", "画像の枠を隠す", "縦で読む", "Revert to OCR", COPY, "Delete"]


def test_4_click_copies_this_region(dummy_page, tmp_path):
    app = prepared(dummy_page, tmp_path)
    copy3 = [b for b in buttons_of(app.selections_list.controls[1]) if b.tooltip == COPY]
    assert len(copy3) == 1
    copy3[0].on_click(None)
    assert dummy_page.clipboard == ["test_page Region 3"]
    assert app.latest_region_info == "コピーしました: test_page Region 3"
    assert "Last: コピーしました: test_page Region 3" in app.status_text.value

    copy2 = [b for b in buttons_of(app.selections_list.controls[0]) if b.tooltip == COPY]
    copy2[0].on_click(None)
    assert dummy_page.clipboard == ["test_page Region 3", "test_page Region 2"]


def test_5_copy_changes_nothing_else(dummy_page, tmp_path):
    app = prepared(dummy_page, tmp_path, edits={"3": "■■NG■■"})
    before_edits = dict(app.edits)
    before_ids = [r.rect_id for r in app.selection_container.get_all()]
    before_active, before_editing = app.active_region_id, app.editing_region_id
    app.copy_region_ref("3")
    assert dummy_page.clipboard == ["test_page Region 3"]
    assert app.edits == before_edits
    assert [r.rect_id for r in app.selection_container.get_all()] == before_ids
    assert (app.active_region_id, app.editing_region_id) == (before_active, before_editing)


def test_6_unknown_region_does_nothing(dummy_page, tmp_path):
    app = prepared(dummy_page, tmp_path)
    app.latest_region_info = "前の知らせ"
    app.copy_region_ref("99")
    assert dummy_page.clipboard == []
    assert app.latest_region_info == "前の知らせ"


def test_7_no_page_still_shows_text(dummy_page, tmp_path):
    app = prepared(dummy_page, tmp_path)
    app.page = None
    app.status_text.page = None
    app.copy_region_ref("2")
    assert dummy_page.clipboard == []
    assert app.latest_region_info == "コピーしました: test_page Region 2"
