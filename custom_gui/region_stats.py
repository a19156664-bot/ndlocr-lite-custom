def count_line_breaks(text) -> int:
    if not text:
        return 0
    text = text.replace('\r\n', '\n')
    text = text.rstrip('\n')
    return text.count('\n')
