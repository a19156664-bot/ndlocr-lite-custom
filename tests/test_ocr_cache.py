import os
import json
from PIL import Image
import time
import pytest

from custom_gui.ocr_cache import (
    CACHE_DIR_NAME,
    SCHEMA_VERSION,
    cache_dir_for,
    cache_path_for,
    save_cache,
    load_cache,
    is_cached
)

@pytest.fixture
def test_image(tmp_path):
    img_path = tmp_path / "test_img.jpg"
    img = Image.new('RGB', (100, 100))
    img.save(str(img_path))
    return str(img_path)

def test_cache_dir_and_path(test_image):
    # (b) the file lands exactly at <folder>/.ndlocr_cache/<stem>.json.
    expected_dir = os.path.join(os.path.dirname(test_image), CACHE_DIR_NAME)
    assert cache_dir_for(test_image) == expected_dir
    
    stem = os.path.splitext(os.path.basename(test_image))[0]
    expected_path = os.path.join(expected_dir, f"{stem}.json")
    assert cache_path_for(test_image) == expected_path
    
def test_page_index_cache_path(test_image):
    # (c) page_index=0 lands at <stem>_p0001.json... page_index=11 gives _p0012.json.
    # distinct from page_index=None
    cache_dir = cache_dir_for(test_image)
    stem = os.path.splitext(os.path.basename(test_image))[0]
    
    path_none = cache_path_for(test_image, page_index=None)
    path_0 = cache_path_for(test_image, page_index=0)
    path_11 = cache_path_for(test_image, page_index=11)
    
    assert path_none == os.path.join(cache_dir, f"{stem}.json")
    assert path_0 == os.path.join(cache_dir, f"{stem}_p0001.json")
    assert path_11 == os.path.join(cache_dir, f"{stem}_p0012.json")

def test_round_trip(test_image):
    # (a) round trip: save_cache then load_cache returns equal results, bbox is TUPLE
    # (h) mtime survives JSON round trip, is_cached is True immediately after
    results = [
        {"text": "hello", "bbox": (10, 20, 30, 40), "confidence": 0.9, "is_vertical": False, "source_image": "test_img.jpg"}
    ]
    
    save_cache(test_image, results)
    
    assert is_cached(test_image) is True
    
    loaded = load_cache(test_image)
    assert loaded is not None
    assert len(loaded) == 1
    
    loaded_entry = loaded[0]
    assert loaded_entry["text"] == "hello"
    assert loaded_entry["bbox"] == (10, 20, 30, 40)
    assert isinstance(loaded_entry["bbox"], tuple)
    assert loaded_entry["confidence"] == 0.9
    assert loaded_entry["is_vertical"] is False

def test_page_index_round_trip(test_image):
    # (c) page_index files round trip and can coexist
    results_none = [{"text": "none", "bbox": (0, 0, 10, 10), "confidence": 0.8, "is_vertical": False, "source_image": "test_img.jpg"}]
    results_0 = [{"text": "page0", "bbox": (0, 0, 10, 10), "confidence": 0.8, "is_vertical": False, "source_image": "test_img.jpg"}]
    results_11 = [{"text": "page11", "bbox": (0, 0, 10, 10), "confidence": 0.8, "is_vertical": False, "source_image": "test_img.jpg"}]
    
    save_cache(test_image, results_none, page_index=None)
    save_cache(test_image, results_0, page_index=0)
    save_cache(test_image, results_11, page_index=11)
    
    assert load_cache(test_image, page_index=None)[0]["text"] == "none"
    assert load_cache(test_image, page_index=0)[0]["text"] == "page0"
    assert load_cache(test_image, page_index=11)[0]["text"] == "page11"

def test_staleness(test_image):
    # (d) STALENESS: save, modify source image size AND mtime -> load_cache returns None
    results = [{"text": "hello", "bbox": (10, 20, 30, 40), "confidence": 0.9, "is_vertical": False, "source_image": "test_img.jpg"}]
    save_cache(test_image, results)
    
    assert is_cached(test_image) is True
    
    # Modify image to change size and mtime
    time.sleep(0.01) # ensure mtime changes
    img = Image.new('RGB', (200, 200)) # different size
    img.save(test_image)
    
    assert load_cache(test_image) is None
    assert is_cached(test_image) is False

def test_corrupt_json(test_image):
    # (e) corrupt JSON -> load_cache returns None, no exception
    results = [{"text": "hello", "bbox": (10, 20, 30, 40), "confidence": 0.9, "is_vertical": False, "source_image": "test_img.jpg"}]
    save_cache(test_image, results)
    
    cache_path = cache_path_for(test_image)
    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write("{this is not json")
        
    assert load_cache(test_image) is None

def test_wrong_schema(test_image):
    # (f) cache file whose "schema" is 999 -> None, no exception
    results = [{"text": "hello", "bbox": (10, 20, 30, 40), "confidence": 0.9, "is_vertical": False, "source_image": "test_img.jpg"}]
    save_cache(test_image, results)
    
    cache_path = cache_path_for(test_image)
    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    data["schema"] = 999
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
        
    assert load_cache(test_image) is None

def test_missing_source(test_image):
    # (g) missing source file -> None, no exception
    results = [{"text": "hello", "bbox": (10, 20, 30, 40), "confidence": 0.9, "is_vertical": False, "source_image": "test_img.jpg"}]
    save_cache(test_image, results)
    
    os.remove(test_image)
    
    assert load_cache(test_image) is None
