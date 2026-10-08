from custom_gui.app import OcrState

REGION1_MARGIN = 15.0

def page_ocr_enabled(environ) -> bool:
    """False only when environ.get("NDLOCR_PAGE_OCR", "") stripped and
    lower-cased is exactly "off". True otherwise (missing, "on", "",
    anything else)."""
    return environ.get("NDLOCR_PAGE_OCR", "").strip().lower() != "off"

def build_page_state(parsed, container, edits, mark, page_ocr: bool) -> dict:
    """The image_states entry for one page."""
    if page_ocr:
        if len(container.get_all()) == 0 and parsed:
            all_xs = [l["bbox"][0] for l in parsed] + [l["bbox"][2] for l in parsed]
            all_ys = [l["bbox"][1] for l in parsed] + [l["bbox"][3] for l in parsed]
            if all_xs and all_ys:
                min_x = max(0.0, min(all_xs) - REGION1_MARGIN)
                max_x = max(all_xs) + REGION1_MARGIN
                min_y = max(0.0, min(all_ys) - REGION1_MARGIN)
                max_y = max(all_ys) + REGION1_MARGIN
                container.add((min_x, min_y, max_x, max_y))
        
        return {
            "selections": container,
            "ocr_state": OcrState.DONE,
            "ocr_results": parsed,
            "ocr_error": None,
            "edits": edits,
            "mark": mark
        }
    else:
        container.ensure_next_id_at_least(2)
        return {
            "selections": container,
            "ocr_state": OcrState.DONE,
            "ocr_results": [],
            "ocr_error": None,
            "edits": edits,
            "mark": mark
        }
