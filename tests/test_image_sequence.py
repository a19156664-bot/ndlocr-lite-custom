import os
import pytest
from custom_gui.image_sequence import list_images_in_folder, ImageSequence
from custom_gui.selection import SelectionContainer
from custom_gui.app import OcrState

def test_list_images_in_folder(tmp_path):
    # A folder containing 0002.jpg, 0001.png, 0003.JPG, notes.txt and a sub-folder
    (tmp_path / "0002.jpg").touch()
    (tmp_path / "0001.png").touch()
    (tmp_path / "0003.JPG").touch()
    (tmp_path / "notes.txt").touch()
    sub_dir = tmp_path / "sub_folder"
    sub_dir.mkdir()
    (sub_dir / "0004.jpg").touch()

    paths = list_images_in_folder(str(tmp_path))
    
    assert len(paths) == 3
    basenames = [os.path.basename(p) for p in paths]
    assert basenames == ["0001.png", "0002.jpg", "0003.JPG"]

def test_empty_folder_returns_empty_list(tmp_path):
    paths = list_images_in_folder(str(tmp_path))
    assert paths == []

def test_image_sequence_navigation():
    seq = ImageSequence(["0001.png", "0002.jpg", "0003.JPG"])
    
    assert seq.index == 0
    assert seq.current() == "0001.png"
    assert seq.count == 3
    
    # next twice reaches index 2
    assert seq.next() == "0002.jpg"
    assert seq.index == 1
    assert seq.next() == "0003.JPG"
    assert seq.index == 2
    
    # a third next leaves index at 2
    assert seq.has_next() is False
    assert seq.next() == "0003.JPG"
    assert seq.index == 2

    # prev from index 0
    seq.goto(0)
    assert seq.index == 0
    assert seq.has_prev() is False
    assert seq.prev() == "0001.png"
    assert seq.index == 0

    # goto
    assert seq.goto(1) == "0002.jpg"
    assert seq.current() == "0002.jpg"
    assert seq.goto(99) == "0003.JPG"
    assert seq.index == 2

def test_empty_image_sequence():
    seq = ImageSequence([])
    
    assert seq.current() is None
    assert seq.count == 0
    assert seq.has_next() is False
    assert seq.has_prev() is False
    assert seq.next() is None
    assert seq.prev() is None
    assert seq.goto(0) is None
    assert seq.index == -1

def test_per_image_state_store():
    # Keep this state in a small, GUI-free structure so it is testable, for example a dict keyed by image path holding a SelectionContainer, the OCR line list and the OcrState.
    state_store = {}
    
    path_a = "A.jpg"
    path_b = "B.jpg"
    
    # Initialize A
    state_store[path_a] = {
        "selections": SelectionContainer(),
        "ocr_state": OcrState.DONE,
        "ocr_results": [{"bbox": [0,0,10,10], "text": "Hello"}]
    }
    
    # Add rect to A
    state_store[path_a]["selections"].add((1,2,3,4))
    
    # Switch to B (initialize B)
    state_store[path_b] = {
        "selections": SelectionContainer(),
        "ocr_state": OcrState.IDLE,
        "ocr_results": []
    }
    
    # Assert A's state is intact
    assert len(state_store[path_a]["selections"].get_all()) == 1
    assert state_store[path_a]["ocr_state"] == OcrState.DONE
    
    # Assert B is unaffected
    assert len(state_store[path_b]["selections"].get_all()) == 0
    assert state_store[path_b]["ocr_state"] == OcrState.IDLE
