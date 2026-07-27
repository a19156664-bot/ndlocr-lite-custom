import pytest
from custom_gui.text_assembler import assemble_text

def test_assemble_text_three_lines():
    """(a) 3行の入力に対し、"1行目\\n2行目\\n3行目" の形式で連結されること"""
    lines = [
        {"text": "1行目", "bbox": (10, 10, 50, 20)},
        {"text": "2行目", "bbox": (10, 30, 50, 40)},
        {"text": "3行目", "bbox": (10, 50, 50, 60)}
    ]
    result = assemble_text(lines)
    assert result == "1行目\n2行目\n3行目"

def test_assemble_text_empty_list():
    """(b) 空リストに対して空文字列 "" が返ること"""
    result = assemble_text([])
    assert result == ""

def test_assemble_text_preserve_order():
    """(c) 入力の順序が入れ替わらないこと（意図的に逆順の座標を持つ入力で検証）"""
    lines = [
        {"text": "bottom line", "bbox": (10, 100, 50, 110)},
        {"text": "middle line", "bbox": (10, 50, 50, 60)},
        {"text": "top line", "bbox": (10, 10, 50, 20)}
    ]
    result = assemble_text(lines)
    # 座標の上下に関わらず、リストの要素順に連結されること
    assert result == "bottom line\nmiddle line\ntop line"
