from dataclasses import dataclass
from typing import Tuple, List, Optional
from custom_gui.viewer import display_to_original


@dataclass
class SelectionRect:
    rect_id: str
    bbox: Tuple[float, float, float, float]
    label: str


class SelectionContainer:
    def __init__(self):
        self._rects: List[SelectionRect] = []
        self._next_id: int = 1

    def add(self, bbox: Tuple[float, float, float, float], label: Optional[str] = None) -> SelectionRect:
        rect_id = str(self._next_id)
        if label is None:
            label = f"Region {rect_id}"
        
        rect = SelectionRect(rect_id=rect_id, bbox=bbox, label=label)
        self._rects.append(rect)
        self._next_id += 1
        return rect

    def get_all(self) -> List[SelectionRect]:
        return list(self._rects)

    def delete_by_id(self, rect_id: str) -> bool:
        for i, rect in enumerate(self._rects):
            if rect.rect_id == rect_id:
                del self._rects[i]
                return True
        return False


def calculate_normalized_bbox(
    start_x: float, start_y: float,
    end_x: float, end_y: float,
    scale: float,
    offset_x: float, offset_y: float,
    img_w: float, img_h: float
) -> Tuple[float, float, float, float]:
    """
    Given display coordinates for drag start and end, calculate the normalized
    and clipped bounding box in original image coordinates.
    """
    orig_start_x, orig_start_y = display_to_original(start_x, start_y, scale, offset_x, offset_y)
    orig_end_x, orig_end_y = display_to_original(end_x, end_y, scale, offset_x, offset_y)
    
    # Normalize
    x1 = min(orig_start_x, orig_end_x)
    x2 = max(orig_start_x, orig_end_x)
    y1 = min(orig_start_y, orig_end_y)
    y2 = max(orig_start_y, orig_end_y)
    
    # Clip to image bounds
    x1 = max(0.0, min(x1, img_w))
    x2 = max(0.0, min(x2, img_w))
    y1 = max(0.0, min(y1, img_h))
    y2 = max(0.0, min(y2, img_h))
    
    return (x1, y1, x2, y2)
