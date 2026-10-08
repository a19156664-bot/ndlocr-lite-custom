import numpy as np
import cv2
import pytest
from custom_gui.vertical_ocr import (
    PHOTO_ROW_RATIO,
    MIN_RUN,
    MARGIN,
    ink_mask,
    text_band,
    split_columns,
    vertical_ocr_text,
)

def test_1_text_band_ratios():
    # 1. text_band: a 100x50 mask whose rows 0..39 have ratio 0.9 and rows 40..99 have ratio 0.2 -> (40, 100).
    # mask needs to be 0 and 1, so if ratio is 0.9, we put 90% 1s.
    mask = np.zeros((100, 50), dtype=np.uint8)
    mask[0:40, 0:45] = 1 # ratio 0.9 (45/50)
    mask[40:100, 0:10] = 1 # ratio 0.2 (10/50)
    
    assert text_band(mask) == (40, 100)

def test_2_text_band_longest_and_tie():
    # 2. text_band: two text-like runs of length 10 and 30 separated by dense rows -> the run of length 30. 
    # Tie (two runs of 20) -> the topmost. All rows dense -> (0, 0).
    
    # Case 1: length 10 and 30 separated by dense
    mask1 = np.zeros((100, 50), dtype=np.uint8)
    mask1[:, 0:45] = 1 # all dense initially (ratio 0.9)
    mask1[10:20, :] = 0 # text-like run of 10
    mask1[40:70, :] = 0 # text-like run of 30
    assert text_band(mask1) == (40, 70)
    
    # Case 2: Tie (two runs of 20) -> topmost
    mask2 = np.zeros((100, 50), dtype=np.uint8)
    mask2[:, 0:45] = 1
    mask2[10:30, :] = 0 # first run of 20
    mask2[50:70, :] = 0 # second run of 20
    assert text_band(mask2) == (10, 30)
    
    # Case 3: All rows dense
    mask3 = np.ones((100, 50), dtype=np.uint8)
    assert text_band(mask3) == (0, 0)

def test_3_split_columns_simple():
    # 3. split_columns: height 60, three ink columns at x 10..20, 25..35, 40..50 (full height), nothing else -> [(10,20),(25,35),(40,50)].
    mask = np.zeros((60, 60), dtype=np.uint8)
    mask[:, 10:20] = 1
    mask[:, 25:35] = 1
    mask[:, 40:50] = 1
    
    assert split_columns(mask) == [(10, 20), (25, 35), (40, 50)]

def test_4_split_columns_pitch():
    # 4. split_columns: runs (0,10),(15,25),(30,60) -> pitch 10, the last run is split into (30,40),(40,50),(50,60); 5 parts in total, left to right.
    mask = np.zeros((60, 70), dtype=np.uint8)
    mask[:, 0:10] = 1
    mask[:, 15:25] = 1
    mask[:, 30:60] = 1
    
    assert split_columns(mask) == [(0, 10), (15, 25), (30, 40), (40, 50), (50, 60)]

def test_5_split_columns_min_run():
    # 5. split_columns: a run of width 3 plus (10,20) -> only [(10,20)].
    mask = np.zeros((60, 30), dtype=np.uint8)
    mask[:, 0:3] = 1 # width 3, less than MIN_RUN=5
    mask[:, 10:20] = 1
    
    assert split_columns(mask) == [(10, 20)]

class FakeRecognizer:
    def __init__(self):
        self.calls = []
        
    def read(self, img):
        self.calls.append(img)
        # recover order from crop's position by checking grey level of the bar
        # bar grey levels are 0, 30, 60, 90
        # img is BGR. The bars were black, but the instructions say:
        # "give each bar a different grey level 0, 30, 60, 90 and read it back from the crop"
        
        # So we will look for the darkest pixel in the crop to find the bar color
        # Since crop is BGR and we use grayscale values
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        min_val = np.min(gray)
        
        if min_val <= 5: # ~0
            return "C1" # x=280
        elif 25 <= min_val <= 35: # ~30
            return "C2" # x=200
        elif 55 <= min_val <= 65: # ~60
            return "C3" # x=120
        elif 85 <= min_val <= 95: # ~90
            return "C4" # x=40
        return "UNK"

def test_6_vertical_ocr_text_end_to_end(tmp_path):
    # 6. vertical_ocr_text end to end: a white 400x300 (w x h) BGR PNG with a black "photo" block over rows 0..99 (all columns), 
    # and below it four black vertical bars (each 12 px wide, rows 120..280) at x = 40, 120, 200, 280. 
    # bbox = the whole image, pad 0.
    # give each bar a different grey level 0, 30, 60, 90
    
    img = np.full((300, 400, 3), 255, dtype=np.uint8)
    # black "photo" block over rows 0..99 (all columns)
    img[0:100, :] = 0
    
    # four bars
    img[120:281, 40:52] = [90, 90, 90]   # C1
    img[120:281, 120:132] = [60, 60, 60] # C2
    img[120:281, 200:212] = [30, 30, 30] # C3
    img[120:281, 280:292] = [0, 0, 0]    # C4
    
    img_path = tmp_path / "test.png"
    cv2.imwrite(str(img_path), img)
    
    bbox = [0, 0, 400, 300]
    
    rec = FakeRecognizer()
    result = vertical_ocr_text(str(img_path), bbox, pad=0, recognizer=rec)
    
    # Assert: exactly 4 calls; every crop is taller than wide and its height is <= 180 (photo excluded);
    assert len(rec.calls) == 4
    for call_img in rec.calls:
        h, w = call_img.shape[:2]
        assert h > w
        assert h <= 180
        
    # the crops come from x = 280, 200, 120, 40 in that order
    # the result is "C1\nC2\nC3\nC4"
    assert result == "C1\nC2\nC3\nC4"

def test_7_blank_white_png(tmp_path):
    # 7. A blank white PNG -> "" and the recognizer is never called.
    img = np.full((100, 100, 3), 255, dtype=np.uint8)
    img_path = tmp_path / "blank.png"
    cv2.imwrite(str(img_path), img)
    
    rec = FakeRecognizer()
    result = vertical_ocr_text(str(img_path), [0, 0, 100, 100], pad=0, recognizer=rec)
    
    assert result == ""
    assert len(rec.calls) == 0

def test_8_bar_wider_than_tall(tmp_path):
    # 8. A bar wider than tall (60 x 20) as the only ink -> "" (skipped).
    img = np.full((100, 200, 3), 255, dtype=np.uint8)
    img[40:60, 20:80] = 0 # 20 tall, 60 wide
    
    img_path = tmp_path / "wide.png"
    cv2.imwrite(str(img_path), img)
    
    rec = FakeRecognizer()
    result = vertical_ocr_text(str(img_path), [0, 0, 200, 100], pad=0, recognizer=rec)
    
    assert result == ""
    assert len(rec.calls) == 0

class WhitespaceRecognizer:
    def read(self, img):
        return "  "

def test_9_whitespace_dropped(tmp_path):
    # 9. Recognizer returns "  " for one column -> that column is dropped from the joined text.
    img = np.full((100, 200, 3), 255, dtype=np.uint8)
    img[10:90, 45:55] = 0 # vertical bar
    
    img_path = tmp_path / "whitespace.png"
    cv2.imwrite(str(img_path), img)
    
    rec = WhitespaceRecognizer()
    result = vertical_ocr_text(str(img_path), [0, 0, 200, 100], pad=0, recognizer=rec)
    
    assert result == ""

def test_10_get_recognizer_not_called(tmp_path, monkeypatch):
    # 10. get_recognizer is not called when recognizer is given: monkeypatch custom_gui.vertical_ocr.get_recognizer to raise; vertical_ocr_text with a fake recognizer still works.
    import custom_gui.vertical_ocr
    def fake_get_recognizer():
        raise RuntimeError("get_recognizer should not be called!")
        
    monkeypatch.setattr(custom_gui.vertical_ocr, "get_recognizer", fake_get_recognizer)
    
    img = np.full((100, 200, 3), 255, dtype=np.uint8)
    img[10:90, 45:55] = 0
    img_path = tmp_path / "mock.png"
    cv2.imwrite(str(img_path), img)
    
    class DumbRec:
        def read(self, img):
            return "OK"
            
    result = vertical_ocr_text(str(img_path), [0, 0, 200, 100], pad=0, recognizer=DumbRec())
    assert result == "OK"

def test_11_japanese_path(tmp_path):
    # 11. A file name with Japanese characters (tmp_path / "国際_p0001.png", written with cv2.imencode(".png", img)[1].tofile(path)) works.
    img = np.full((100, 200, 3), 255, dtype=np.uint8)
    img[10:90, 45:55] = 0
    
    jp_path = tmp_path / "国際_p0001.png"
    # cv2.imwrite doesn't support unicode paths well on Windows, memory tip suggests using tofile for Japanese filenames if needed, 
    # but the instruction specifically says "written with cv2.imencode(".png", img)[1].tofile(path)"
    cv2.imencode(".png", img)[1].tofile(str(jp_path))
    
    class DumbRec:
        def read(self, img):
            return "JP"
            
    result = vertical_ocr_text(str(jp_path), [0, 0, 200, 100], pad=0, recognizer=DumbRec())
    assert result == "JP"
