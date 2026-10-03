import os

MARK_COLOR_ENV = "NDLOCR_MARK_COLOR"

def current_mark_color() -> str:
    """'lime' when the env var says lime (case-insensitive, surrounding
    spaces ignored); otherwise 'cyan' (unset, empty, or any other value)."""
    val = os.environ.get(MARK_COLOR_ENV, "").strip().lower()
    if val == "lime":
        return "lime"
    return "cyan"

def page_mark_enabled() -> bool:
    """True when current_mark_color() == 'cyan'; False for 'lime'.
    (With lime material, the orange detector only hits printed ink.)"""
    return current_mark_color() == "cyan"
