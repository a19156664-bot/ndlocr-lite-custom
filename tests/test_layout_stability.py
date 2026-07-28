import pytest
from custom_gui.app import SelectableImageViewer
import os

def test_layout_stability(monkeypatch):
    image_path = os.path.join("resource", "digidepo_2531162_0024.jpg")
    
    # ensure it doesn't crash on OCR
    monkeypatch.setattr("custom_gui.app.run_ocr_and_parse", lambda *args, **kwargs: [])
    
    # Start at 1600x900 window with a 2218x3071 image (we'll manually feed these dimensions)
    viewer = SelectableImageViewer(
        image_src=image_path,
        img_w=2218, img_h=3071,
        win_w=1600, win_h=900
    )
    
    # Ensure starting zoom_scale is correct
    # win_w available = max(100, 1600-320) = 1280
    # win_h available = max(100, 900-100) = 800
    # expected scale: min(1280/2218, 800/3071) = min(0.577, 0.2605...) -> 0.2605
    initial_scale = viewer.zoom_scale
    assert round(initial_scale, 4) == 0.2605
    
    # When _switch_image is called, it reads the image size from the file.
    # To keep img_w and img_h at our simulated 2218x3071, we patch PIL.Image.open
    class FakeImage:
        def __init__(self, *args, **kwargs):
            self.size = (2218, 3071)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr("PIL.Image.open", FakeImage)

    for i in range(1, 11):
        # mock switching page
        viewer._switch_image(image_path)
        if i in [1, 5, 10]:
            assert round(viewer.zoom_scale, 4) == 0.2605, f"Scale shrank at switch {i}! expected 0.2605, got {viewer.zoom_scale:.4f}"
