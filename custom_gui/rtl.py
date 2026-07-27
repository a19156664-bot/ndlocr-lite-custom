"""
Right-to-left conversion for pre-war Japanese text.
The unit of conversion is one line. Line order is preserved.
The conversion is its own inverse.
"""

MIRRORED_CHARS = {
    "（": "）", "）": "（",  # fullwidth parenthesis
    "(": ")", ")": "(",      # ASCII parenthesis
    "「": "」", "」": "「",  # U+300C / U+300D
    "『": "』", "』": "『",  # U+300E / U+300F
    "【": "】", "】": "【",  # U+3010 / U+3011
    "［": "］", "］": "［",  # fullwidth square
    "[": "]", "]": "[",      # ASCII square
    "｛": "｝", "｝": "｛",  # fullwidth brace
    "{": "}", "}": "{",      # ASCII brace
    "〔": "〕", "〕": "〔",  # U+3014 / U+3015
    "〈": "〉", "〉": "〈",  # U+3008 / U+3009
    "《": "》", "》": "《",  # U+300A / U+300B
    "<": ">", ">": "<",      # ASCII angle
    "＜": "＞", "＞": "＜",  # fullwidth angle
}

def reverse_line(line: str) -> str:
    """
    Reverse the characters of a single line and mirror bracket characters.
    """
    return "".join(MIRRORED_CHARS.get(c, c) for c in reversed(line))

def convert_right_to_left(text: str) -> str:
    """
    Convert text line-by-line from right-to-left to left-to-right (and vice versa).
    Splits on newline, applies reverse_line to each line independently,
    keeps the line order exactly the same, and rejoins with newline.
    This operation is its own inverse.
    """
    lines = text.split("\n")
    reversed_lines = [reverse_line(line) for line in lines]
    return "\n".join(reversed_lines)
