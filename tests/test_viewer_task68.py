"""Task 68: 右の一覧の枠を押すと、画像のその枠が見えている所の真ん中へ来る（承認者 10-10）。
枠を探して画像を動かす手間を省くため。動かすのは Pan と同じずらし量。倍率は変えない。"""
import pytest

from custom_gui.app import center_offset
from tests.test_marks_to_rects import get_app, make_clean_page


@pytest.mark.parametrize("center,img_len,scale,view_len,want", [
    (140, 400, 2.0, 480, -40.0),     # 240 - 280
    (140, 600, 2.0, 500, -30.0),     # 250 - 280
    (10, 400, 2.0, 480, 220.0),      # 端の枠も真ん中へ（画像の外が見えてもよい）
    (390, 400, 2.0, 480, -540.0),
    (140, 400, 1.2, 480, 0.0),       # 400*1.2 = 480 は収まる → 動かさない
    (140, 400, 0.5, 480, 0.0),
])
def test_1_center_offset(center, img_len, scale, view_len, want):
    assert center_offset(center, img_len, scale, view_len) == pytest.approx(want)


@pytest.fixture
def dummy_page():
    class DummyPage:
        def __init__(self):
            self.controls = []
            self.overlay = []
        def add(self, *args):
            pass
        def update(self, *args):
            pass
        def run_thread(self, target, *args, **kwargs):
            target(*args, **kwargs)
        window_width = 800
        window_height = 600
        session_id = "test"
    return DummyPage()


def prepared(dummy_page, tmp_path):
    # 窓 800x600 → 画像の見えている所 480x500（win_w / win_h）。画像 400x600
    app, path = get_app(dummy_page, tmp_path, make_clean_page)
    app.ocr_results = []
    app.selection_container._rects = []
    r2 = app.selection_container.add((0, 0, 60, 30))
    r2.rect_id, r2.label = "2", "Region 2"
    r3 = app.selection_container.add((80, 80, 200, 200))
    r3.rect_id, r3.label = "3", "Region 3"
    app.edits = {}
    app.image_states[str(path)]["edits"] = app.edits
    app.zoom_scale = 2.0
    app._update_selections_ui()
    return app


def where(app):
    return [(c.left, c.top) for c in (app.image_control, app.highlight_layer, app.rects_layer, app.inline_editor_layer)]


def test_2_click_row_centers_that_region(dummy_page, tmp_path):
    app = prepared(dummy_page, tmp_path)
    assert (app.win_w, app.win_h) == (480, 500)
    app.selections_list.controls[1].on_click(None)          # Region 3 の行
    assert (app.offset_x, app.offset_y) == pytest.approx((-40.0, -30.0))
    assert where(app) == [(app.offset_x, app.offset_y)] * 4  # 画像と枠の層が同じだけ動く（ずれない）
    assert app.active_region_id == "3"
    assert app.zoom_scale == 2.0

    app.selections_list.controls[0].on_click(None)          # Region 2 の行（真ん中 30,15）
    assert (app.offset_x, app.offset_y) == pytest.approx((180.0, 220.0))
    assert where(app) == [(180.0, 220.0)] * 4
    assert app.active_region_id == "2"


def test_3_click_active_row_again_recenters(dummy_page, tmp_path):
    app = prepared(dummy_page, tmp_path)
    app.selections_list.controls[1].on_click(None)
    app.offset_x, app.offset_y = 5.0, 7.0                   # そのあと Pan で動かした
    app.selections_list.controls[1].on_click(None)          # 同じ行をもう一度
    assert (app.offset_x, app.offset_y) == pytest.approx((-40.0, -30.0))
    assert app.image_control.left == pytest.approx(-40.0)


def test_4_fitting_direction_does_not_move(dummy_page, tmp_path):
    app = prepared(dummy_page, tmp_path)
    app.zoom_scale = 1.0                                    # 横 400 は 480 に収まる・縦 600 は 500 を超える
    app.offset_x, app.offset_y = 12.0, 34.0
    app.center_on_region("3")
    assert (app.offset_x, app.offset_y) == pytest.approx((0.0, 110.0))   # 250 - 140

    app.zoom_scale = 0.5                                    # どちらも収まる（Fit より小さい）
    app.center_on_region("3")
    assert (app.offset_x, app.offset_y) == (0.0, 0.0)


def test_5_scroll_back_to_zero(dummy_page, tmp_path):
    app = prepared(dummy_page, tmp_path)
    calls = []
    outer = app.scrollable_image
    inner = app.scrollable_image.controls[0]
    outer.page = dummy_page
    inner.page = dummy_page
    outer.scroll_to = lambda **kw: calls.append(("outer", kw))
    inner.scroll_to = lambda **kw: calls.append(("inner", kw))
    app.center_on_region("3")
    assert calls == [("outer", {"offset": 0}), ("inner", {"offset": 0})]


def test_6_unknown_region_does_nothing(dummy_page, tmp_path):
    app = prepared(dummy_page, tmp_path)
    app.offset_x, app.offset_y = 5.0, 7.0
    app.center_on_region("99")
    assert (app.offset_x, app.offset_y) == (5.0, 7.0)


def test_7_changes_nothing_else(dummy_page, tmp_path):
    app = prepared(dummy_page, tmp_path)
    app.edits["3"] = "直した文字"
    before_ids = [r.rect_id for r in app.selection_container.get_all()]
    before_bbox = [tuple(r.bbox) for r in app.selection_container.get_all()]
    app.center_on_region("3")
    assert app.edits == {"3": "直した文字"}
    assert [r.rect_id for r in app.selection_container.get_all()] == before_ids
    assert [tuple(r.bbox) for r in app.selection_container.get_all()] == before_bbox
    assert app.editing_region_id is None
