import os
import json
import pytest
from custom_gui.work_state import save_work_state, load_work_state, work_path_for, clear_work_state
from custom_gui.ocr_cache import cache_path_for
from dataclasses import dataclass
from typing import Tuple

@dataclass
class DummyRect:
    rect_id: str
    bbox: Tuple[float, float, float, float]
    label: str

def test_work_state_round_trip(tmp_path):
    img_path = tmp_path / "test.jpg"
    img_path.write_bytes(b"dummy image content")
    
    rects = [
        DummyRect(rect_id="1", bbox=(10.0, 20.0, 30.0, 40.0), label="Region 1"),
        DummyRect(rect_id="2", bbox=(50.0, 60.0, 70.0, 80.0), label="Region 2")
    ]
    edits = {"1": "Edited Text"}
    mark = "【広告】"
    
    path = save_work_state(str(img_path), rects, edits, mark)
    assert os.path.exists(path)
    
    data = load_work_state(str(img_path))
    assert data is not None
    
    loaded_rects = data["rects"]
    assert len(loaded_rects) == 2
    assert loaded_rects[0]["rect_id"] == "1"
    assert loaded_rects[0]["bbox"] == (10.0, 20.0, 30.0, 40.0)
    assert isinstance(loaded_rects[0]["bbox"], tuple)
    assert loaded_rects[0]["label"] == "Region 1"
    
    assert data["edits"] == {"1": "Edited Text"}
    assert data["mark"] == "【広告】"

def test_work_state_mark_none(tmp_path):
    img_path = tmp_path / "test.jpg"
    img_path.write_bytes(b"dummy image content")
    
    save_work_state(str(img_path), [], {}, None)
    data = load_work_state(str(img_path))
    assert data["mark"] is None

def test_work_state_size_changed(tmp_path):
    img_path = tmp_path / "test.jpg"
    img_path.write_bytes(b"dummy")
    
    save_work_state(str(img_path), [], {}, None)
    
    img_path.write_bytes(b"dummy image content") # size changed
    
    data = load_work_state(str(img_path))
    assert data is None

def test_work_state_mtime_changed(tmp_path):
    img_path = tmp_path / "test.jpg"
    img_path.write_bytes(b"dummy")
    
    save_work_state(str(img_path), [], {}, None)
    
    # Change mtime
    st = os.stat(str(img_path))
    os.utime(str(img_path), (st.st_atime, st.st_mtime + 2.0))
    
    data = load_work_state(str(img_path))
    assert data is None

def test_work_state_garbage_bytes(tmp_path):
    img_path = tmp_path / "test.jpg"
    img_path.write_bytes(b"dummy")
    
    save_work_state(str(img_path), [], {}, None)
    
    cache_path = work_path_for(str(img_path))
    with open(cache_path, 'wb') as f:
        f.write(b"\x00\xff\xfe garbage")
        
    data = load_work_state(str(img_path))
    assert data is None

def test_work_state_wrong_schema(tmp_path):
    img_path = tmp_path / "test.jpg"
    img_path.write_bytes(b"dummy")
    
    cache_path = save_work_state(str(img_path), [], {}, None)
    
    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    data["schema"] = 999
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
        
    loaded = load_work_state(str(img_path))
    assert loaded is None

def test_work_state_missing_label(tmp_path):
    img_path = tmp_path / "test.jpg"
    img_path.write_bytes(b"dummy")
    
    cache_path = save_work_state(str(img_path), [], {}, None)
    
    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    data["rects"] = [{"rect_id": "1", "bbox": [0,0,10,10]}] # missing label
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
        
    loaded = load_work_state(str(img_path))
    assert loaded is None

def test_work_state_paths():
    img = "/tmp/test.jpg"
    work = work_path_for(img)
    ocr = cache_path_for(img)
    assert work != ocr
    assert work.endswith(".work.json")
    assert ocr.endswith(".json") and not ocr.endswith(".work.json")
    
    work_pdf = work_path_for(img, 0)
    assert work_pdf.endswith("_p0001.work.json")

def test_clear_work_state(tmp_path):
    img_path = tmp_path / "test.jpg"
    img_path.write_bytes(b"dummy")
    
    save_work_state(str(img_path), [], {}, None)
    
    assert clear_work_state(str(img_path)) is True
    assert clear_work_state(str(img_path)) is False
