import numpy as np
import cv2
import pytest
import os
from unittest.mock import patch, MagicMock
from custom_gui.vertical_ocr import (
    remove_photo_tiles,
    estimate_pitch,
    split_columns,
    vertical_ocr_text,
    MIN_RUN
)
from custom_gui.region_ocr import REGION_OCR_PAD

class FakeRecognizer:
    def __init__(self):
        self.reads = []

    def read(self, crop):
        self.reads.append(crop)
        return "fake_text"

def test_A_remove_photo_tiles():
    mask = np.zeros((96, 96), dtype=np.uint8)
    # top-left tile: all 1
    mask[0:48, 0:48] = 1
    # bottom-left tile: exactly 25% ones (which is <= 0.5)
    # 48 * 48 = 2304. 25% is 576.
    mask[48:96, 0:48].flat[:576] = 1

    orig_mask = mask.copy()

    out = remove_photo_tiles(mask)

    # original mask unchanged
    assert np.array_equal(mask, orig_mask)

    # first tile becomes all 0
    assert np.all(out[0:48, 0:48] == 0)

    # second tile is unchanged
    assert np.array_equal(out[48:96, 0:48], orig_mask[48:96, 0:48])

    # every other pixel is unchanged
    assert np.array_equal(out[:, 48:96], orig_mask[:, 48:96])


def test_B_side_photo(tmp_path):
    img = np.full((600, 300, 3), 255, dtype=np.uint8) # white
    # black strip over x 0..95, all rows
    img[:, 0:96] = 0

    # four vertical bars 12 px wide over rows 50..549 at x=120, 160, 200, 240
    # grey levels 90, 60, 30, 0
    xs = [120, 160, 200, 240]
    grays = [90, 60, 30, 0]
    for x, g in zip(xs, grays):
        img[50:550, x:x+12] = [g, g, g] # BGR

    path = str(tmp_path / "test.png")
    cv2.imwrite(path, img)

    fake = FakeRecognizer()
    
    vertical_ocr_text(path, (0, 0, 300, 600), pad=0, recognizer=fake)
    
    assert len(fake.reads) == 4
    
    # Called from right to left (x=240, then 200, then 160, then 120)
    for i, crop in enumerate(fake.reads):
        assert crop.shape[0] >= 500
        # The center of the crop should roughly correspond to the bar we expect
        # It's an image crop. The min value in the crop should be the grey level.
        # But wait! crop is BGR? No, it's just the BGR crop!
        # grey levels: rightmost is x=240 (0), then 200 (30), etc.
        expected_g = grays[3 - i]
        assert np.min(crop) == expected_g


def test_C_merged_columns():
    mask = np.zeros((600, 360), dtype=np.uint8)
    # first column 100..119
    mask[:, 100:120] = 1
    # five 30px columns 123..152, 156..185, 189..218, 222..251, 255..284.
    cols = [(123, 153), (156, 186), (189, 219), (222, 252), (255, 285)]
    for s, e in cols:
        mask[:, s:e] = 1
        
    # five 3px gaps with ink only in rows 0..19
    gaps = [(120, 123), (153, 156), (186, 189), (219, 222), (252, 255)]
    for s, e in gaps:
        mask[0:20, s:e] = 1

    cuts_result = split_columns(mask)
    
    assert len(cuts_result) == 6
    assert cuts_result[0][0] == 100
    assert cuts_result[-1][1] == 285
    
    expected_cuts = [122, 155, 188, 221, 254]
    
    for k in range(5):
        c = cuts_result[k][1]
        assert c == cuts_result[k+1][0]
        # check that cut k is inside gap k (inclusive of bounds as long as it's the gap)
        # the gap is gaps[k][0] to gaps[k][1]-1
        assert gaps[k][0] <= c <= gaps[k][1] - 1


def test_D_estimate_pitch_shortest_strong_period():
    prof = np.zeros(400, dtype=float)
    # pulses of width 26 starting every 32 px (0, 32, 64...)
    # heights alternating 100 and 90
    for i in range(0, 400, 32):
        height = 100 if (i // 32) % 2 == 0 else 90
        prof[i:i+26] = height
        
    runs = [(0, 400)]
    pitch = estimate_pitch(prof, runs)
    assert 31 <= pitch <= 33


def test_E_estimate_pitch_no_periodicity():
    prof = np.full(120, 50.0, dtype=float)
    runs = [(0, 120)]
    pitch = estimate_pitch(prof, runs)
    assert pitch == 120


def test_F_estimate_pitch_no_wide_run():
    # runs narrower than 40
    runs = [(0, 10), (20, 32), (40, 54)]
    prof = np.zeros(60, dtype=float)
    pitch = estimate_pitch(prof, runs)
    assert pitch == 12 # median width: 10, 12, 14 -> 12


def test_G_sliver_dropped():
    mask = np.zeros((600, 150), dtype=np.uint8)
    # full height ink at 10..16 (7px sliver)
    mask[:, 10:17] = 1
    # three 30px columns with empty 3px gaps
    mask[:, 40:70] = 1
    mask[:, 73:103] = 1
    mask[:, 106:136] = 1
    
    cuts = split_columns(mask)
    
    # does not return any column inside 10..16
    for s, e in cuts:
        assert not (s >= 10 and e <= 17)
        
    assert len(cuts) == 3
    assert cuts[0] == (40, 70)
    assert cuts[1] == (73, 103)
    assert cuts[2] == (106, 136)
