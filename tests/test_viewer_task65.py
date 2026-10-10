import pytest
import flet as ft
from custom_gui.selection import SelectionContainer, adjust_bbox
from custom_gui import work_state
from tests.test_marks_to_rects import get_app, make_clean_page


@pytest.fixture
def dummy_page():
    class DummyPage:
        def __init__(self):
            self.controls = []
            self.overlay = []
            self.pending = []
        def add(self, *args):
            pass
        def update(self, *args):
            pass
        def run_thread(self, target, *args, **kwargs):
            self.pending.append((target, args, kwargs))
        window_width = 800
        window_height = 600
        session_id = "test"
    return DummyPage()


def get_prepared_app(dummy_page, tmp_path):
    app, path = get_app(dummy_page, tmp_path, make_clean_page)   # image 400 x 600
    app.ocr_results = []
    app.selection_container.restore([])
    for bbox in [(0, 0, 60, 30), (80, 80, 200, 200), (10, 300, 90, 400)]:
        app.selection_container.add(bbox)
    app.edits = {"2": "二", "3": "三"}
    app.image_states[str(path)]["edits"] = app.edits
    app.editing_region_id = None
    app.active_region_id = "2"
    app._update_selections_ui()
    return app, str(path)


class Ev:
    def __init__(self, gx, gy):
        self.global_x = gx
        self.global_y = gy


def grip_at(app, grip):
    """The grip control for one name, found by its place on the selected frame."""
    order = ["nw", "n", "ne", "e", "se", "s", "sw", "w", "move"]
    gs = [g for g in app.handles_layer.controls if isinstance(g, ft.GestureDetector)]
    return gs[order.index(grip)]


def drag(app, grip, dx_screen, dy_screen):
    g = grip_at(app, grip)
    g.on_pan_start(Ev(100, 100))
    g.on_pan_update(Ev(100 + dx_screen / 2, 100 + dy_screen / 2))
    g.on_pan_update(Ev(100 + dx_screen, 100 + dy_screen))
    g.on_pan_end(Ev(100 + dx_screen, 100 + dy_screen))


def bbox_of(app, rid):
    return [r.bbox for r in app.selection_container.get_all() if r.rect_id == rid][0]


def test_1_adjust_bbox_contract():
    b = (100, 100, 200, 200)
    assert adjust_bbox(b, "move", 10, -20, 400, 600) == (110, 80, 210, 180)
    assert adjust_bbox(b, "move", -500, 900, 400, 600) == (0, 500, 100, 600)       # stays inside the image
    assert adjust_bbox(b, "se", 30, 40, 400, 600) == (100, 100, 230, 240)
    assert adjust_bbox(b, "nw", -30, -40, 400, 600) == (70, 60, 200, 200)
    assert adjust_bbox(b, "e", 30, 40, 400, 600) == (100, 100, 230, 200)          # e ignores dy
    assert adjust_bbox(b, "n", 30, 40, 400, 600) == (100, 140, 200, 200)          # n ignores dx
    assert adjust_bbox(b, "se", 999, 999, 400, 600) == (100, 100, 400, 600)       # clipped to the image
    assert adjust_bbox(b, "nw", 999, 999, 400, 600) == (196, 196, 200, 200)       # never below min_size
    assert adjust_bbox(b, "w", -999, 0, 400, 600) == (0, 100, 200, 200)


def test_2_set_bbox_contract():
    c = SelectionContainer()
    for i in range(3):
        c.add((i, i, i + 1, i + 1))
    assert c.set_bbox("2", (5, 6, 7, 8)) is True
    assert [r.rect_id for r in c.get_all()] == ["1", "2", "3"]
    assert [r.label for r in c.get_all()] == ["Region 1", "Region 2", "Region 3"]
    assert c.get_all()[1].bbox == (5, 6, 7, 8)
    assert c.set_bbox("9", (0, 0, 1, 1)) is False
    assert c.add((0, 0, 1, 1)).rect_id == "4"                                     # numbering untouched


def test_3_grips_on_selected_frame_only(dummy_page, tmp_path):
    app, _ = get_prepared_app(dummy_page, tmp_path)
    gs = [g for g in app.handles_layer.controls if isinstance(g, ft.GestureDetector)]
    assert len(gs) == 9
    assert [g.mouse_cursor for g in gs] == [
        ft.MouseCursor.RESIZE_UP_LEFT_DOWN_RIGHT, ft.MouseCursor.RESIZE_UP_DOWN,
        ft.MouseCursor.RESIZE_UP_RIGHT_DOWN_LEFT, ft.MouseCursor.RESIZE_LEFT_RIGHT,
        ft.MouseCursor.RESIZE_UP_LEFT_DOWN_RIGHT, ft.MouseCursor.RESIZE_UP_DOWN,
        ft.MouseCursor.RESIZE_UP_RIGHT_DOWN_LEFT, ft.MouseCursor.RESIZE_LEFT_RIGHT,
        ft.MouseCursor.MOVE]
    s = app.zoom_scale
    se = grip_at(app, "se")
    assert se.left + se.width / 2 == pytest.approx(200 * s)
    assert se.top + se.height / 2 == pytest.approx(200 * s)
    mv = grip_at(app, "move")
    assert mv.left + mv.width / 2 == pytest.approx(140 * s)


def test_4_no_grips_in_pan_mode_or_hidden(dummy_page, tmp_path):
    app, _ = get_prepared_app(dummy_page, tmp_path)
    app._toggle_mode(None)
    assert app.mode_state.current == "PAN"
    assert app.handles_layer.controls == []
    app._toggle_mode(None)
    assert len(app.handles_layer.controls) == 9
    app.toggle_region_visible("2")
    assert app.handles_layer.controls == []


def test_5_resize_and_save(dummy_page, tmp_path):
    app, path = get_prepared_app(dummy_page, tmp_path)
    s = app.zoom_scale
    drag(app, "se", 40 * s, 20 * s)
    assert bbox_of(app, "2") == pytest.approx((80, 80, 240, 220))
    assert [r.rect_id for r in app.selection_container.get_all()] == ["1", "2", "3"]
    assert app.edits == {"2": "二", "3": "三"}
    st = work_state.load_work_state(path)
    assert st is not None
    assert [r["rect_id"] for r in st["rects"]] == ["1", "2", "3"]
    assert st["rects"][1]["bbox"] == pytest.approx([80, 80, 240, 220])
    assert st["edits"] == {"2": "二", "3": "三"}
    se = grip_at(app, "se")                                     # grips follow the new frame
    assert se.left + se.width / 2 == pytest.approx(240 * s)


def test_6_move_stays_inside(dummy_page, tmp_path):
    app, _ = get_prepared_app(dummy_page, tmp_path)
    s = app.zoom_scale
    drag(app, "move", -1000 * s, 30 * s)
    assert bbox_of(app, "2") == pytest.approx((0, 110, 120, 230))


def test_7_preview_only_until_release(dummy_page, tmp_path):
    app, path = get_prepared_app(dummy_page, tmp_path)
    s = app.zoom_scale
    g = grip_at(app, "e")
    g.on_pan_start(Ev(100, 100))
    g.on_pan_update(Ev(100 + 50 * s, 100))
    assert bbox_of(app, "2") == (80, 80, 200, 200)              # not yet
    preview = app.handles_layer.controls[-1]
    assert preview.width == pytest.approx(170 * s)
    assert work_state.load_work_state(path) is None
    g.on_pan_end(Ev(100 + 50 * s, 100))
    assert bbox_of(app, "2") == pytest.approx((80, 80, 250, 200))


def test_8_no_change_writes_nothing(dummy_page, tmp_path):
    app, path = get_prepared_app(dummy_page, tmp_path)
    drag(app, "nw", 0, 0)
    assert bbox_of(app, "2") == (80, 80, 200, 200)
    assert work_state.load_work_state(path) is None
    assert len(app.handles_layer.controls) == 9


def test_9_no_change_while_editing(dummy_page, tmp_path):
    app, path = get_prepared_app(dummy_page, tmp_path)
    app.editing_region_id = "3"
    drag(app, "se", 40, 40)
    assert bbox_of(app, "2") == (80, 80, 200, 200)
    assert "編集中" in app.latest_region_info
    assert work_state.load_work_state(path) is None


def test_10_layer_order_and_zoom(dummy_page, tmp_path):
    app, _ = get_prepared_app(dummy_page, tmp_path)
    c = app.stack.controls
    assert c.index(app.gesture_detector) < c.index(app.inline_editor_layer) < c.index(app.handles_layer)
    assert c[-1] is app.handles_layer
    app.zoom_scale = app.zoom_scale * 2
    app._update_viewer()
    se = grip_at(app, "se")
    assert se.left + se.width / 2 == pytest.approx(200 * app.zoom_scale)
    assert app.handles_layer.width == pytest.approx(400 * app.zoom_scale)
