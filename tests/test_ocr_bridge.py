import os
import pytest
from custom_gui.ocr_bridge import run_ocr_and_parse

def test_run_ocr_and_parse_success():
    """
    Test run_ocr_and_parse with a valid image file.
    Verifies that the results conform to the specified schema and rules.
    """
    image_path = os.path.join("resource", "digidepo_2531162_0024.jpg")
    
    # Ensure the image exists to avoid failing the test on missing resource
    assert os.path.exists(image_path), f"Test image not found: {image_path}"
    
    results = run_ocr_and_parse(image_path)
    
    # (a) 1行以上が取得できること (At least 1 result line is retrieved)
    assert len(results) > 0, "Expected at least 1 result from OCR"
    
    filename = os.path.basename(image_path)
    
    for row in results:
        # (b) 全行の source_image が入力画像のファイル名と一致すること
        assert row["source_image"] == filename, "source_image does not match input filename"
        
        # (c) 全行の bbox が4要素の数値であり、x1 < x2 かつ y1 < y2 を満たすこと
        bbox = row["bbox"]
        assert isinstance(bbox, tuple) and len(bbox) == 4, "bbox must be a 4-element tuple"
        x1, y1, x2, y2 = bbox
        assert isinstance(x1, (int, float))
        assert isinstance(y1, (int, float))
        assert isinstance(x2, (int, float))
        assert isinstance(y2, (int, float))
        assert x1 < x2, f"x1 ({x1}) must be less than x2 ({x2})"
        assert y1 < y2, f"y1 ({y1}) must be less than y2 ({y2})"
        
        # (d) is_vertical が bool 型であること（文字列でないこと）
        assert isinstance(row["is_vertical"], bool), "is_vertical must be a boolean"
        
        # Additional checks based on requirements
        assert "text" in row and isinstance(row["text"], str)
        assert "confidence" in row and isinstance(row["confidence"], float)
