import math
import os
import shutil
import tempfile
import cv2
from custom_gui import mark_detector
from custom_gui import ocr_bridge

REGION_OCR_PAD = 16

def crop_region(image_bgr, bbox, pad: int = REGION_OCR_PAD):
    """Return image_bgr[y1-pad:y2+pad, x1-pad:x2+pad], clipped to the image.
    bbox is (x1, y1, x2, y2) in original pixels; floats are allowed
    (round down x1/y1, round up x2/y2)."""
    h, w = image_bgr.shape[:2]
    x1, y1, x2, y2 = bbox
    
    ix1 = math.floor(x1) - pad
    iy1 = math.floor(y1) - pad
    ix2 = math.ceil(x2) + pad
    iy2 = math.ceil(y2) + pad
    
    ix1 = max(0, min(w, ix1))
    iy1 = max(0, min(h, iy1))
    ix2 = max(0, min(w, ix2))
    iy2 = max(0, min(h, iy2))
    
    return image_bgr[iy1:iy2, ix1:ix2]

def region_ocr_text(image_path: str, bbox, pad: int = REGION_OCR_PAD) -> str:
    """Crop the region from the image file, write the crop as PNG into a
    temporary directory, OCR it, and return the line texts joined with
    "\n" in the order the OCR returned them. "" when no line has text.
    The temporary directory is removed before returning, also on error.
    Exceptions from the OCR propagate unchanged."""
    img = mark_detector.load_image(image_path)
    crop = crop_region(img, bbox, pad)
    
    tmp_dir = tempfile.mkdtemp(prefix="region_ocr_")
    try:
        base_name = os.path.basename(image_path)
        name, _ = os.path.splitext(base_name)
        png_path = os.path.join(tmp_dir, f"{name}.png")
        
        cv2.imencode(".png", crop)[1].tofile(png_path)
        
        results = ocr_bridge.run_ocr_and_parse(png_path)
        
        texts = []
        for line in results:
            text = line.get("text", "")
            if text and not text.isspace():
                texts.append(text)
                
        return "\n".join(texts)
    finally:
        shutil.rmtree(tmp_dir)
