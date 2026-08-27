from dataclasses import dataclass
from typing import Tuple, List
import cv2
import numpy as np
import os

CYAN_LOWER = (80, 120, 180)      # HSV lower bound, OpenCV convention (H is 0-179)
CYAN_UPPER = (105, 255, 255)     # HSV upper bound

@dataclass
class MarkRegion:
    bbox: Tuple[int, int, int, int]   # (x1, y1, x2, y2) in ORIGINAL image pixels
    kind: str                         # "box" or "line"

def detect_marks(
    image_bgr,                  # numpy.ndarray, BGR, as returned by load_image
    min_area: int = 500,
    thin_max: int = 20,
    line_margin: int = 20,
) -> List[MarkRegion]:
    height, width = image_bgr.shape[:2]
    
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, CYAN_LOWER, CYAN_UPPER)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    regions = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w * h < min_area:
            continue
            
        if min(w, h) <= thin_max:
            kind = "line"
        else:
            kind = "box"
            
        x1, y1, x2, y2 = x, y, x + w, y + h
        
        if kind == "line":
            if w <= h:
                x1 -= line_margin
                x2 += line_margin
            else:
                y1 -= line_margin
                y2 += line_margin
                
        x1 = max(0, min(x1, width))
        y1 = max(0, min(y1, height))
        x2 = max(0, min(x2, width))
        y2 = max(0, min(y2, height))
        
        regions.append(MarkRegion(bbox=(x1, y1, x2, y2), kind=kind))
        
    regions.sort(key=lambda r: (r.bbox[1], r.bbox[0]))
    return regions

def load_image(path: str):
    """Read an image file into a BGR numpy array."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
        
    data = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    
    if image is None:
        raise ValueError(f"Could not decode image from {path}")
        
    return image
