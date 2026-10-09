import pytest
import flet as ft
from custom_gui.selection import SelectionContainer
from custom_gui.exporter import build_export_rows
from custom_gui.form_export import build_keywords
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
    app, path = get_app(dummy_page, tmp_path, make_clean_page)
    app.ocr_results = []
    app.selection_container.restore([])
    for bbox in [(0, 0, 60, 30), (80, 80, 200, 200), (10, 300, 90, 400)]:
        app.selection_container.add(bbox)
    # ids "1","2","3"; drop "1" so the rows are Region 2, 3, 4 as in the viewer
    app.selection_container.delete_by_id("1")
    app.selection_container.add((5, 500, 50, 550))
    app.edits = {"2": "二", "3": "三", "4": "四"}
    app.image_states[str(path)]["edits"] = app.edits
    app.editing_region_id = None
    app._update_selections_ui()
    return app, str(path)


def ids(app):
    return [r.rect_id for r in app.selection_container.get_all()]


def move_buttons(row):
    move_row = row.content.controls[2]
    return move_row.controls[0], move_row.controls[1]


def click(btn):
    class E:
        control = btn
    btn.on_click(E())


def test_1_move_by_contract():
    c = SelectionContainer()
    for i in range(3):
        c.add((i, i, i + 1, i + 1))
    before_next = c.add((9, 9, 10, 10)).rect_id   # "4"
    c.delete_by_id("4")
    assert [r.rect_id for r in c.get_all()] == ["1", "2", "3"]

    assert c.move_by("2", -1) is True
    assert [r.rect_id for r in c.get_all()] == ["2", "1", "3"]
    assert [r.label for r in c.get_all()] == ["Region 2", "Region 1", "Region 3"]

    assert c.move_by("2", -1) is False          # already first
    assert c.move_by("3", 1) is False           # already last
    assert c.move_by("9", 1) is False           # unknown id
    assert c.move_by("1", 2) is False           # only -1 / +1
    assert c.move_by("1", 0) is False
    assert [r.rect_id for r in c.get_all()] == ["2", "1", "3"]

    assert c.move_by("1", 1) is True
    assert [r.rect_id for r in c.get_all()] == ["2", "3", "1"]
    assert c.add((0, 0, 1, 1)).rect_id == str(int(before_next) + 1)   # numbering untouched


def test_2_buttons_place_and_size(dummy_page, tmp_path):
    app, _ = get_prepared_app(dummy_page, tmp_path)
    for row in app.selections_list.controls:
        col = row.content
        assert len(col.controls) == 3
        assert len(col.controls[0].controls) == 2               # title row unchanged
        assert [b.tooltip for b in col.controls[0].controls[1].controls] == \
            ["Edit", "右から変換", "この枠だけOCR", "画像の枠を隠す", "縦で読む", "Revert to OCR", "Delete"]
        move_row = col.controls[2]
        assert isinstance(move_row, ft.Row)
        assert len(move_row.controls) == 2
        up, down = move_row.controls
        assert (up.icon, up.tooltip) == (ft.Icons.ARROW_UPWARD, "上へ")
        assert (down.icon, down.tooltip) == (ft.Icons.ARROW_DOWNWARD, "下へ")
        for b in (up, down):
            assert b.icon_size == 18 and b.width == 32 and b.height == 32
        assert move_row.alignment == ft.MainAxisAlignment.END


def test_3_down_moves_row_and_keeps_text(dummy_page, tmp_path):
    app, _ = get_prepared_app(dummy_page, tmp_path)
    assert ids(app) == ["2", "3", "4"]
    _, down = move_buttons(app.selections_list.controls[0])
    click(down)
    assert ids(app) == ["3", "2", "4"]
    assert [r.label for r in app.selection_container.get_all()] == ["Region 3", "Region 2", "Region 4"]
    assert app.edits == {"2": "二", "3": "三", "4": "四"}
    row1 = app.selections_list.controls[1]
    assert row1.content.controls[0].controls[0].value.startswith("Region 2 (edited)")
    assert row1.content.controls[1].value == "二"
    assert app.active_region_id == "2"


def test_4_up_moves_row(dummy_page, tmp_path):
    app, _ = get_prepared_app(dummy_page, tmp_path)
    up, _ = move_buttons(app.selections_list.controls[2])
    click(up)
    assert ids(app) == ["2", "4", "3"]
    assert app.active_region_id == "4"


def test_5_move_is_saved(dummy_page, tmp_path):
    app, path = get_prepared_app(dummy_page, tmp_path)
    _, down = move_buttons(app.selections_list.controls[0])
    click(down)
    st = work_state.load_work_state(path)
    assert st is not None
    assert [r["rect_id"] for r in st["rects"]] == ["3", "2", "4"]
    assert st["edits"] == {"2": "二", "3": "三", "4": "四"}


def test_6_ends_do_nothing(dummy_page, tmp_path):
    app, path = get_prepared_app(dummy_page, tmp_path)
    up, _ = move_buttons(app.selections_list.controls[0])
    click(up)
    _, down = move_buttons(app.selections_list.controls[2])
    click(down)
    assert ids(app) == ["2", "3", "4"]
    assert work_state.load_work_state(path) is None     # nothing was written


def test_7_no_move_while_editing(dummy_page, tmp_path):
    app, _ = get_prepared_app(dummy_page, tmp_path)
    app.editing_region_id = "3"
    _, down = move_buttons(app.selections_list.controls[0])
    click(down)
    assert ids(app) == ["2", "3", "4"]
    assert "編集中" in app.latest_region_info


def test_8_export_follows_list_order(dummy_page, tmp_path):
    app, _ = get_prepared_app(dummy_page, tmp_path)
    _, down = move_buttons(app.selections_list.controls[0])
    click(down)
    rows = build_export_rows("doc_p0001.png", app.selection_container.get_all(), [], edited_texts=app.edits)
    assert [r["region_id"] for r in rows] == ["3", "2", "4"]
    assert build_keywords(rows, 6)[0] == "【表紙】｜三｜二｜四"
