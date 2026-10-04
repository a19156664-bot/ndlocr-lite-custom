BREAK_MARK = "\U0001F534"

def add_break_marks(text) -> str:
    """None or "" -> "". Replace "\r\n" with "\n", then put BREAK_MARK in front of every "\n"."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n")
    return text.replace("\n", BREAK_MARK + "\n")

def strip_break_marks(text) -> str:
    """None or "" -> "". Remove EVERY BREAK_MARK. Nothing else changes."""
    if not text:
        return ""
    return text.replace(BREAK_MARK, "")
