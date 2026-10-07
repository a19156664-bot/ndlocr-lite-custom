import json
import os
import socket
import threading
import time

import pytest
from custom_gui import batch_region_ocr, work_state, mark_detector
from custom_gui.selection import SelectionContainer, SelectionRect

class FakeMarkRegion:
    def __init__(self, bbox):
        self.bbox = bbox

@pytest.fixture
def repo_layout(tmp_path):
    base = tmp_path
    work_dir = base / "work"
    out_dir = work_dir / "output" / "01_raw_ocr"
    cache_dir = work_dir / "cache_images" / "141号"
    
    out_dir.mkdir(parents=True)
    cache_dir.mkdir(parents=True)
    
    pdf_path = work_dir / "国際寫眞新聞_141号.pdf"
    pdf_path.write_bytes(b"dummy pdf")
    
    # 4 pages
    raw_json_path = out_dir / "国際寫眞新聞_141号.json"
    
    page1_lines = [{"boundingBox": [[100,50],[300,50],[300,400],[100,400]], "text": "L1", "isVertical": "true", "confidence": 0.9}]
    page2_lines = [{"boundingBox": [[100,50],[300,50],[300,400],[100,400]], "text": "L2", "isVertical": "true", "confidence": 0.9}]
    page3_lines = []
    page4_lines = [{"boundingBox": [[100,50],[300,50],[300,400],[100,400]], "text": "L4", "isVertical": "true", "confidence": 0.9}]
    
    contents = {"contents": [page1_lines, page2_lines, page3_lines, page4_lines]}
    raw_json_path.write_text(json.dumps(contents), encoding="utf-8")
    
    # fake pngs
    from PIL import Image
    for i in range(1, 5):
        png_path = cache_dir / f"国際寫眞新聞_141号_p{i:04d}.png"
        img = Image.new("RGB", (100, 100), color="white")
        img.save(png_path)
        
    # dummy src/ocr.py
    src_dir = base / "src"
    src_dir.mkdir()
    (src_dir / "ocr.py").write_text("dummy")
    
    return base

@pytest.fixture
def patch_viewer_guard(monkeypatch):
    monkeypatch.setattr(batch_region_ocr, "viewer_is_open", lambda port: False)

def get_parsed_state(pdf_path, page_index):
    data = work_state.load_work_state(pdf_path, page_index)
    container = SelectionContainer()
    edits = {}
    mark = None
    if data:
        rects = []
        for r in data.get("rects", []):
            rects.append(SelectionRect(rect_id=r["rect_id"], bbox=tuple(r["bbox"]), label=r["label"]))
        container.restore(rects)
        edits = data.get("edits", {})
        mark = data.get("mark")
    return container, edits, mark


def test_case_1(repo_layout, monkeypatch, patch_viewer_guard):
    """
    1. Saved page untouched: before running, save a state for page 2 with
       work_state.save_work_state; remember the file bytes. The fake
       detect_marks returns ONE region (10,20,30,40) "box" for EVERY call (so
       that, if the skip were missing, page 2 would be OCR'd). Run main()
       over all pages. After main(): page 2's bytes are identical, and
       region_ocr_text was never called with page 2's PNG path (compare the
       full path), while it WAS called with page 1's PNG path.
    """
    pdf_path = str(repo_layout / "work" / "国際寫眞新聞_141号.pdf")
    
    work_state.save_work_state(pdf_path, [], {}, None, page_index=1)
    
    state_path_p2 = work_state.work_path_for(pdf_path, 1)
    orig_bytes_p2 = open(state_path_p2, "rb").read()
    
    def fake_detect_marks(*args, **kwargs):
        return [FakeMarkRegion((10, 20, 30, 40))]
        
    calls = []
    def fake_region_ocr_text(path, bbox):
        calls.append((path, bbox))
        return "fake text"
        
    monkeypatch.setattr(batch_region_ocr.mark_detector, "detect_marks", fake_detect_marks)
    monkeypatch.setattr(batch_region_ocr.region_ocr, "region_ocr_text", fake_region_ocr_text)
    
    res = batch_region_ocr.main(["--issue", "141", "--base", str(repo_layout)])
    assert res == 0
    
    new_bytes_p2 = open(state_path_p2, "rb").read()
    assert orig_bytes_p2 == new_bytes_p2
    
    p2_png = str(repo_layout / "work" / "cache_images" / "141号" / "国際寫眞新聞_141号_p0002.png")
    p1_png = str(repo_layout / "work" / "cache_images" / "141号" / "国際寫眞新聞_141号_p0001.png")
    
    assert not any(c[0] == p2_png for c in calls)
    assert any(c[0] == p1_png for c in calls)
    
def test_case_2(repo_layout, monkeypatch, patch_viewer_guard):
    """
    2. New page with marks (page 1, lines spanning x 100..300, y 50..400;
       detect_marks returns two regions (500,600,700,800) "box" and
       (10,20,90,880) "line"; region_ocr_text returns "A\nB" then "C"):
       load_work_state(PDF, 0) has rects with ids ["1","2","3"], rect "1"
       bbox == (85.0, 35.0, 315.0, 415.0), rect "2" bbox == (500,600,700,800),
       rect "3" bbox == (10,20,90,880); edits == {"2": "A\nB", "3": "C"};
       mark is None.
    """
    pdf_path = str(repo_layout / "work" / "国際寫眞新聞_141号.pdf")
    
    def fake_detect_marks(img, color):
        return [FakeMarkRegion((500, 600, 700, 800)), FakeMarkRegion((10, 20, 90, 880))]
        
    call_idx = 0
    def fake_region_ocr_text(path, bbox):
        nonlocal call_idx
        res = "A\nB" if call_idx == 0 else "C"
        call_idx += 1
        return res
        
    monkeypatch.setattr(batch_region_ocr.mark_detector, "detect_marks", fake_detect_marks)
    monkeypatch.setattr(batch_region_ocr.region_ocr, "region_ocr_text", fake_region_ocr_text)
    
    res = batch_region_ocr.main(["--issue", "141", "--base", str(repo_layout), "--pages", "1"])
    assert res == 0
    
    container, edits, mark = get_parsed_state(pdf_path, 0)
    
    rects = container.get_all()
    assert [r.rect_id for r in rects] == ["1", "2", "3"]
    assert rects[0].bbox == (85.0, 35.0, 315.0, 415.0)
    assert rects[1].bbox == (500, 600, 700, 800)
    assert rects[2].bbox == (10, 20, 90, 880)
    
    assert edits == {"2": "A\nB", "3": "C"}
    assert mark is None

def test_case_3(repo_layout, monkeypatch, patch_viewer_guard):
    """
    3. Empty OCR text: like 2 but region_ocr_text returns "" for the second
       region: edits has key "2" only.
    """
    pdf_path = str(repo_layout / "work" / "国際寫眞新聞_141号.pdf")
    
    def fake_detect_marks(img, color):
        return [FakeMarkRegion((500, 600, 700, 800)), FakeMarkRegion((10, 20, 90, 880))]
        
    call_idx = 0
    def fake_region_ocr_text(path, bbox):
        nonlocal call_idx
        res = "A\nB" if call_idx == 0 else ""
        call_idx += 1
        return res
        
    monkeypatch.setattr(batch_region_ocr.mark_detector, "detect_marks", fake_detect_marks)
    monkeypatch.setattr(batch_region_ocr.region_ocr, "region_ocr_text", fake_region_ocr_text)
    
    res = batch_region_ocr.main(["--issue", "141", "--base", str(repo_layout), "--pages", "1"])
    assert res == 0
    
    container, edits, mark = get_parsed_state(pdf_path, 0)
    assert list(edits.keys()) == ["2"]

def test_case_4(repo_layout, monkeypatch, patch_viewer_guard):
    """
    4. OCR error: region_ocr_text raises RuntimeError for the first region:
       edits has key "3" only, main() returns 0.
    """
    pdf_path = str(repo_layout / "work" / "国際寫眞新聞_141号.pdf")
    
    def fake_detect_marks(img, color):
        return [FakeMarkRegion((500, 600, 700, 800)), FakeMarkRegion((10, 20, 90, 880))]
        
    call_idx = 0
    def fake_region_ocr_text(path, bbox):
        nonlocal call_idx
        if call_idx == 0:
            call_idx += 1
            raise RuntimeError("Fake OCR error")
        call_idx += 1
        return "C"
        
    monkeypatch.setattr(batch_region_ocr.mark_detector, "detect_marks", fake_detect_marks)
    monkeypatch.setattr(batch_region_ocr.region_ocr, "region_ocr_text", fake_region_ocr_text)
    
    res = batch_region_ocr.main(["--issue", "141", "--base", str(repo_layout), "--pages", "1"])
    assert res == 0
    
    container, edits, mark = get_parsed_state(pdf_path, 0)
    assert list(edits.keys()) == ["3"]

def test_case_5(repo_layout, monkeypatch, patch_viewer_guard):
    """
    5. No marks (page 3): detect_marks returns []: no state file exists for
       page 3 after main().
    """
    pdf_path = str(repo_layout / "work" / "国際寫眞新聞_141号.pdf")
    
    def fake_detect_marks(img, color):
        return []
        
    monkeypatch.setattr(batch_region_ocr.mark_detector, "detect_marks", fake_detect_marks)
    
    res = batch_region_ocr.main(["--issue", "141", "--base", str(repo_layout), "--pages", "3"])
    assert res == 0
    
    state_path = work_state.work_path_for(pdf_path, 2)
    assert not os.path.exists(state_path)

def test_case_6(repo_layout, monkeypatch):
    """
    6. Viewer open: open a real listening socket on 127.0.0.1 port 0, pass
       its port as --viewer-port: main() returns 2, no state file was
       created for any page, and region_ocr_text was never called.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
        
        pdf_path = str(repo_layout / "work" / "国際寫眞新聞_141号.pdf")
        
        calls = []
        def fake_region_ocr_text(*args, **kwargs):
            calls.append(True)
            return "A"
            
        monkeypatch.setattr(batch_region_ocr.region_ocr, "region_ocr_text", fake_region_ocr_text)
        
        res = batch_region_ocr.main(["--issue", "141", "--base", str(repo_layout), "--viewer-port", str(port)])
        assert res == 2
        
        for i in range(4):
            state_path = work_state.work_path_for(pdf_path, i)
            assert not os.path.exists(state_path)
            
        assert len(calls) == 0

def test_case_7(repo_layout, monkeypatch, patch_viewer_guard):
    """
    7. --pages: with --pages 3-4 only pages 3 and 4 are looked at
       (detect_marks is never called with page 1's PNG).
    """
    calls = []
    def fake_detect_marks(img, color):
        calls.append(img)
        return []
        
    monkeypatch.setattr(batch_region_ocr.mark_detector, "detect_marks", fake_detect_marks)
    
    # We also mock ensure_page_rendered to get the paths since detect_marks takes image arrays, not paths
    rendered_paths = []
    orig_ensure = batch_region_ocr.pdf_loader.ensure_page_rendered
    def fake_ensure(png_path, *args, **kwargs):
        rendered_paths.append(png_path)
        return orig_ensure(png_path, *args, **kwargs)
        
    monkeypatch.setattr(batch_region_ocr.pdf_loader, "ensure_page_rendered", fake_ensure)
    
    res = batch_region_ocr.main(["--issue", "141", "--base", str(repo_layout), "--pages", "3-4"])
    assert res == 0
    
    p1_png = str(repo_layout / "work" / "cache_images" / "141号" / "国際寫眞新聞_141号_p0001.png")
    assert not any(p == p1_png for p in rendered_paths)
    
def test_case_8(repo_layout, monkeypatch, patch_viewer_guard):
    """
    8. Saved meanwhile: the fake region_ocr_text, on its first call for
       page 4, writes page 4's state with work_state.save_work_state
       (simulating the viewer). After main(): page 4's file is exactly what
       the fake wrote (bytes), i.e. the tool did not overwrite it.
    """
    pdf_path = str(repo_layout / "work" / "国際寫眞新聞_141号.pdf")
    
    def fake_detect_marks(*args, **kwargs):
        return [FakeMarkRegion((10, 20, 30, 40))]
        
    fake_wrote_bytes = None
    
    def fake_region_ocr_text(path, bbox):
        nonlocal fake_wrote_bytes
        # Write state for page 4 (index 3)
        work_state.save_work_state(pdf_path, [], {"fake": "fake"}, None, page_index=3)
        state_path = work_state.work_path_for(pdf_path, 3)
        fake_wrote_bytes = open(state_path, "rb").read()
        return "text"
        
    monkeypatch.setattr(batch_region_ocr.mark_detector, "detect_marks", fake_detect_marks)
    monkeypatch.setattr(batch_region_ocr.region_ocr, "region_ocr_text", fake_region_ocr_text)
    
    res = batch_region_ocr.main(["--issue", "141", "--base", str(repo_layout), "--pages", "4"])
    assert res == 0
    
    state_path = work_state.work_path_for(pdf_path, 3)
    current_bytes = open(state_path, "rb").read()
    
    assert current_bytes == fake_wrote_bytes
    
def test_case_9(repo_layout, monkeypatch, patch_viewer_guard):
    """
    9. Region 1 rule: a page whose RAW JSON line list is empty but with one
       mark: ids are ["1"] for the mark (no Region 1), and edits key is "1".
    """
    pdf_path = str(repo_layout / "work" / "国際寫眞新聞_141号.pdf")
    
    def fake_detect_marks(*args, **kwargs):
        return [FakeMarkRegion((10, 20, 30, 40))]
        
    def fake_region_ocr_text(*args, **kwargs):
        return "text"
        
    monkeypatch.setattr(batch_region_ocr.mark_detector, "detect_marks", fake_detect_marks)
    monkeypatch.setattr(batch_region_ocr.region_ocr, "region_ocr_text", fake_region_ocr_text)
    
    # Page 3 (index 2) has an empty list of lines
    res = batch_region_ocr.main(["--issue", "141", "--base", str(repo_layout), "--pages", "3"])
    assert res == 0
    
    container, edits, mark = get_parsed_state(pdf_path, 2)
    
    rects = container.get_all()
    assert [r.rect_id for r in rects] == ["1"]
    assert rects[0].bbox == (10, 20, 30, 40)
    
    assert edits == {"1": "text"}
