import pytest
from custom_gui.app import SelectableImageViewer, OcrState
from custom_gui.image_sequence import ImageSequence
from custom_gui.selection import SelectionContainer

class MockViewer(SelectableImageViewer):
    def __init__(self, sequence_paths):
        self.image_states = {}
        for p in sequence_paths:
            self.image_states[p] = {
                "selections": SelectionContainer(),
                "ocr_state": OcrState.IDLE,
                "ocr_results": [],
                "edits": {}
            }
        self.sequence = ImageSequence(sequence_paths)
        
    def add_rect(self, path, rect):
        self.image_states[path]["selections"].add(rect)
        
    def set_ocr_state(self, path, state):
        self.image_states[path]["ocr_state"] = state
        
    def set_ocr_results(self, path, results):
        self.image_states[path]["ocr_results"] = results
        
    def set_edit(self, path, rect_id, text):
        self.image_states[path]["edits"][rect_id] = text

def test_export_all_images():
    paths = ["a.jpg", "b.jpg", "c.jpg"]
    viewer = MockViewer(paths)
    
    # a.jpg: 2 rects, DONE
    viewer.add_rect("a.jpg", {"x": 10, "y": 10, "width": 100, "height": 100})
    viewer.add_rect("a.jpg", {"x": 20, "y": 20, "width": 100, "height": 100})
    viewer.set_ocr_state("a.jpg", OcrState.DONE)
    viewer.set_edit("a.jpg", "1", "Edited a.jpg rect 1")
    
    # b.jpg: 0 rects, DONE
    viewer.set_ocr_state("b.jpg", OcrState.DONE)
    
    # c.jpg: 1 rects, DONE
    viewer.add_rect("c.jpg", {"x": 10, "y": 10, "width": 100, "height": 100})
    viewer.set_ocr_state("c.jpg", OcrState.DONE)
    viewer.set_edit("c.jpg", "1", "Edited c.jpg rect 1")
    
    pages, skipped, regions_count = viewer._collect_all_export_pages()
    
    # (a) Three images with 2 / 0 / 1 rects, all DONE
    assert len(pages) == 2
    assert [p["image_name"] for p in pages] == ["a.jpg", "c.jpg"]
    assert skipped == 0
    assert regions_count == 3
    
    # (c) Edit strings are present
    assert pages[0]["edited_texts"].get("1") == "Edited a.jpg rect 1"
    assert pages[1]["edited_texts"].get("1") == "Edited c.jpg rect 1"

def test_export_skip_running():
    paths = ["a.jpg", "b.jpg", "c.jpg"]
    viewer = MockViewer(paths)
    
    # a.jpg: 2 rects, DONE
    viewer.add_rect("a.jpg", {"x": 10, "y": 10, "width": 100, "height": 100})
    viewer.add_rect("a.jpg", {"x": 20, "y": 20, "width": 100, "height": 100})
    viewer.set_ocr_state("a.jpg", OcrState.DONE)
    
    # b.jpg: 2 rects, RUNNING
    viewer.add_rect("b.jpg", {"x": 10, "y": 10, "width": 100, "height": 100})
    viewer.add_rect("b.jpg", {"x": 20, "y": 20, "width": 100, "height": 100})
    viewer.set_ocr_state("b.jpg", OcrState.RUNNING)
    
    # c.jpg: 1 rects, DONE
    viewer.add_rect("c.jpg", {"x": 10, "y": 10, "width": 100, "height": 100})
    viewer.set_ocr_state("c.jpg", OcrState.DONE)
    
    pages, skipped, regions_count = viewer._collect_all_export_pages()
    
    # (b) b.jpg contributes NO rows, skipped equals 1
    assert len(pages) == 2
    assert [p["image_name"] for p in pages] == ["a.jpg", "c.jpg"]
    assert skipped == 1
    assert regions_count == 3

def test_export_no_rects():
    paths = ["a.jpg", "b.jpg", "c.jpg"]
    viewer = MockViewer(paths)
    
    # all DONE, no rects
    viewer.set_ocr_state("a.jpg", OcrState.DONE)
    viewer.set_ocr_state("b.jpg", OcrState.DONE)
    viewer.set_ocr_state("c.jpg", OcrState.DONE)
    
    pages, skipped, regions_count = viewer._collect_all_export_pages()
    
    # (d) ZERO rows
    assert len(pages) == 0
    assert skipped == 0
    assert regions_count == 0

def test_export_sequence_order():
    paths = ["a.jpg", "b.jpg", "c.jpg"]
    
    # Build dictionary in different order
    viewer = MockViewer([])
    viewer.image_states = {}
    viewer.image_states["c.jpg"] = {"selections": SelectionContainer(), "ocr_state": OcrState.DONE, "ocr_results": [], "edits": {}}
    viewer.image_states["b.jpg"] = {"selections": SelectionContainer(), "ocr_state": OcrState.DONE, "ocr_results": [], "edits": {}}
    viewer.image_states["a.jpg"] = {"selections": SelectionContainer(), "ocr_state": OcrState.DONE, "ocr_results": [], "edits": {}}
    
    # Sequence order
    viewer.sequence = ImageSequence(paths)
    
    viewer.add_rect("a.jpg", {"x": 10, "y": 10, "width": 100, "height": 100})
    viewer.add_rect("b.jpg", {"x": 10, "y": 10, "width": 100, "height": 100})
    viewer.add_rect("c.jpg", {"x": 10, "y": 10, "width": 100, "height": 100})
    
    pages, skipped, regions_count = viewer._collect_all_export_pages()
    
    # (e) output follows sequence order, not dict insertion order
    assert len(pages) == 3
    assert [p["image_name"] for p in pages] == ["a.jpg", "b.jpg", "c.jpg"]
