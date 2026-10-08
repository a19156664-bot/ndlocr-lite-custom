import os
import sys
import threading
import numpy as np
import cv2
import yaml
from yaml import safe_load

import custom_gui.mark_detector as mark_detector
from custom_gui.region_ocr import crop_region, REGION_OCR_PAD

PHOTO_ROW_RATIO = 0.35
MIN_RUN = 5
MARGIN = 3

_recognizer_lock = threading.Lock()
_recognizer_instance = None

def ink_mask(image_bgr) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 0, 1, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return mask

def text_band(mask) -> tuple[int, int]:
    if mask.size == 0:
        return (0, 0)
    
    # mask is expected to be 0 or 1, so mean gives the ratio of 1s (ink)
    ratios = mask.mean(axis=1)
    
    text_like = ratios <= PHOTO_ROW_RATIO
    
    if not np.any(text_like):
        return (0, 0)
    
    # Find contiguous runs of text-like rows
    # Pad with False to easily find edges
    padded = np.concatenate(([False], text_like, [False]))
    edges = np.diff(padded.astype(int))
    
    starts = np.where(edges == 1)[0]
    ends = np.where(edges == -1)[0]
    
    lengths = ends - starts
    
    if len(lengths) == 0:
        return (0, 0)
    
    # Find the longest run
    max_len = -1
    best_start = 0
    best_end = 0
    
    # We iterate forward. If lengths are equal, we only update if strictly greater,
    # which preserves the topmost (first) run on ties.
    for s, e, l in zip(starts, ends, lengths):
        if l > max_len:
            max_len = l
            best_start = s
            best_end = e
            
    return (int(best_start), int(best_end))

def split_columns(mask) -> list[tuple[int, int]]:
    H = mask.shape[0]
    if H == 0:
        return []
        
    on = mask.sum(axis=0) > max(2, H * 0.01)
    
    # Find runs of consecutive True
    padded = np.concatenate(([False], on, [False]))
    edges = np.diff(padded.astype(int))
    starts = np.where(edges == 1)[0]
    ends = np.where(edges == -1)[0]
    
    runs = []
    widths = []
    
    for x1, x2 in zip(starts, ends):
        w = x2 - x1
        if w >= MIN_RUN:
            runs.append((x1, x2))
            widths.append(float(w))
            
    if not runs:
        return []
        
    widths = np.array(widths)
    q = np.percentile(widths, 25)
    
    pitch_candidates = widths[widths <= 1.5 * q]
    if len(pitch_candidates) == 0:
        pitch = widths.mean() # fallback if nothing satisfies condition, though shouldn't happen with valid q
    else:
        pitch = np.median(pitch_candidates)
    
    if pitch == 0:
        pitch = 1.0 # avoid division by zero
        
    parts = []
    for x1, x2 in runs:
        width = x2 - x1
        n = max(1, int(round(width / pitch)))
        step = width / n
        
        for i in range(n):
            p1 = int(round(x1 + i * step))
            p2 = int(round(x1 + (i + 1) * step))
            parts.append((p1, p2))
            
    return parts

def get_recognizer():
    global _recognizer_instance
    with _recognizer_lock:
        if _recognizer_instance is None:
            # Import PARSEQ lazily
            repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            src_dir = os.path.join(repo_dir, "src")
            if src_dir not in sys.path:
                sys.path.insert(0, src_dir)
                
            from parseq import PARSEQ
            
            model_path = os.path.join(src_dir, "model", "parseq-ndl-24x768-100-tiny-153epoch-tegaki3-r8data-202604.onnx")
            classes_path = os.path.join(src_dir, "config", "NDLmoji.yaml")
            
            with open(classes_path, "r", encoding="utf-8") as f:
                charlist = list(safe_load(f)["model"]["charset_train"])
                
            _recognizer_instance = PARSEQ(model_path=model_path, charlist=charlist, device="cpu")
            
    return _recognizer_instance

def vertical_ocr_text(image_path: str, bbox, pad: int = REGION_OCR_PAD, recognizer=None) -> str:
    crop = crop_region(mark_detector.load_image(image_path), bbox, pad)
    if crop is None or crop.size == 0:
        return ""
        
    mask = ink_mask(crop)
    y1, y2 = text_band(mask)
    
    if y2 <= y1:
        return ""
        
    band = mask[y1:y2]
    img = crop[y1:y2]
    
    cols = split_columns(band)
    
    kept_texts = []
    
    rec = recognizer if recognizer is not None else get_recognizer()
    
    for x1, x2 in reversed(cols): # RIGHT to LEFT
        # ys = rows of band[:, x1:x2] that contain ink
        col_mask = band[:, x1:x2]
        ink_rows = np.where(col_mask.sum(axis=1) > 0)[0]
        
        if len(ink_rows) == 0:
            continue
            
        a = max(0, ink_rows[0] - MARGIN)
        b = min(band.shape[0], ink_rows[-1] + 1 + MARGIN)
        
        c = img[a:b, max(0, x1 - MARGIN):min(band.shape[1], x2 + MARGIN)]
        
        if c.shape[0] <= c.shape[1]:
            continue
            
        t = rec.read(c)
        
        if t and t.strip():
            kept_texts.append(t)
            
    return "\n".join(kept_texts)
