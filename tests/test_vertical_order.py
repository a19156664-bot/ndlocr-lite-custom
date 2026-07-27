import pytest
import os
from custom_gui.ocr_bridge import run_ocr_and_parse
from custom_gui.region_filter import filter_lines_by_region
from custom_gui.text_assembler import assemble_text

@pytest.fixture(scope="module")
def ocr_results():
    """Run OCR once for the module to save time."""
    image_path = os.path.join("resource", "tategaki2026-04-24-094138.png")
    assert os.path.exists(image_path), f"Test image not found: {image_path}"
    
    # Run OCR and parse results
    return run_ocr_and_parse(image_path)

def test_vertical_order_preservation(ocr_results):
    """
    (d) run_ocr_and_parse の結果に対し、画像全体を覆う矩形でフィルタをかけると、
    戻り値の text の並びが run_ocr_and_parse の戻り値の並びと完全に一致すること
    （＝フィルタと組み立てが読み順を壊さないことの証明）
    """
    assert len(ocr_results) > 0, "OCR should return at least one line."
    
    # original text concatenated
    original_concatenated = "\n".join(line["text"] for line in ocr_results)
    
    # large rectangle covering the whole image
    rect = (0.0, 0.0, 10000.0, 10000.0)
    
    filtered = filter_lines_by_region(rect, ocr_results)
    assembled = assemble_text(filtered)
    
    assert assembled == original_concatenated, "Assembled text does not match the original OCR sequence!"
