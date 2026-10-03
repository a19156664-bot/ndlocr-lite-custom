import os
import cv2
import numpy as np
import pytest
from custom_gui.region_ocr import crop_region, region_ocr_text

def test_crop_region_normal():
    # 400x600 image (h=600, w=400)
    image = np.full((600, 400, 3), 128, dtype=np.uint8)
    image[184, 84] = [10, 20, 30] # y=184, x=84
    
    # bbox (100, 200, 150, 300) -> w=50, h=100
    # pad 16 -> w=50+32=82, h=100+32=132
    # expected crop region:
    # x1: 100 - 16 = 84
    # y1: 200 - 16 = 184
    # x2: 150 + 16 = 166
    # y2: 300 + 16 = 316
    crop = crop_region(image, (100, 200, 150, 300), pad=16)
    
    assert crop.shape == (132, 82, 3) # h, w, c
    assert np.array_equal(crop[0, 0], [10, 20, 30])
    
def test_crop_region_corner():
    image = np.full((100, 100, 3), 128, dtype=np.uint8)
    
    # bbox (5, 5, 40, 40)
    # pad 16
    # expected:
    # x1: max(0, 5 - 16) = 0
    # y1: max(0, 5 - 16) = 0
    # x2: min(100, 40 + 16) = 56
    # y2: min(100, 40 + 16) = 56
    crop = crop_region(image, (5, 5, 40, 40), pad=16)
    
    assert crop.shape == (56, 56, 3)

def test_crop_region_float():
    image = np.full((600, 400, 3), 128, dtype=np.uint8)
    
    # bbox (100.4, 200.6, 149.2, 299.1), pad 0
    # floor x1: 100
    # floor y1: 200
    # ceil x2: 150
    # ceil y2: 300
    crop = crop_region(image, (100.4, 200.6, 149.2, 299.1), pad=0)
    
    # h = 300-200 = 100, w = 150-100 = 50
    assert crop.shape == (100, 50, 3)

def test_region_ocr_text_success(tmp_path, monkeypatch):
    img_path = str(tmp_path / "国際寫眞新聞_test.png")
    image = np.full((100, 100, 3), 128, dtype=np.uint8)
    # Save the original image to disk
    cv2.imencode(".png", image)[1].tofile(img_path)
    
    bbox = (20, 20, 50, 50)
    pad = 16
    expected_crop = crop_region(image, bbox, pad)
    
    received_path = []
    
    def fake_run_ocr_and_parse(path):
        received_path.append(path)
        
        # Load the cropped image from the path received
        img_array = np.fromfile(path, dtype=np.uint8)
        loaded_crop = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        assert loaded_crop.shape == expected_crop.shape
        assert np.array_equal(loaded_crop, expected_crop)
        
        return [{"text": "先生が"}, {"text": " "}, {"text": "轉んだ"}]
        
    monkeypatch.setattr("custom_gui.ocr_bridge.run_ocr_and_parse", fake_run_ocr_and_parse)
    
    result = region_ocr_text(img_path, bbox, pad)
    
    assert result == "先生が\n轉んだ"
    assert len(received_path) == 1
    assert not os.path.exists(received_path[0])

def test_region_ocr_text_empty(tmp_path, monkeypatch):
    img_path = str(tmp_path / "img.png")
    image = np.full((100, 100, 3), 128, dtype=np.uint8)
    cv2.imencode(".png", image)[1].tofile(img_path)
    
    received_path = []
    def fake_run_ocr_and_parse(path):
        received_path.append(path)
        return []
        
    monkeypatch.setattr("custom_gui.ocr_bridge.run_ocr_and_parse", fake_run_ocr_and_parse)
    
    result = region_ocr_text(img_path, (0, 0, 10, 10), 0)
    
    assert result == ""
    assert len(received_path) == 1
    assert not os.path.exists(received_path[0])

def test_region_ocr_text_exception_propagates_and_cleans_up(tmp_path, monkeypatch):
    img_path = str(tmp_path / "img.png")
    image = np.full((100, 100, 3), 128, dtype=np.uint8)
    cv2.imencode(".png", image)[1].tofile(img_path)
    
    received_path = []
    def fake_run_ocr_and_parse(path):
        received_path.append(path)
        raise RuntimeError("boom")
        
    monkeypatch.setattr("custom_gui.ocr_bridge.run_ocr_and_parse", fake_run_ocr_and_parse)
    
    with pytest.raises(RuntimeError, match="boom"):
        region_ocr_text(img_path, (0, 0, 10, 10), 0)
        
    assert len(received_path) == 1
    assert not os.path.exists(received_path[0])
