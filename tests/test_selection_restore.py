import pytest
from custom_gui.selection import SelectionContainer, SelectionRect

def test_restore_ids_collision():
    container = SelectionContainer()
    rects = [
        SelectionRect(rect_id="1", bbox=(0,0,10,10), label="A"),
        SelectionRect(rect_id="2", bbox=(0,0,10,10), label="B"),
        SelectionRect(rect_id="3", bbox=(0,0,10,10), label="C")
    ]
    container.restore(rects)
    
    new_rect = container.add(bbox=(0,0,10,10))
    assert new_rect.rect_id == "4"
    assert new_rect.rect_id not in ["1", "2", "3"]

def test_restore_ids_gap():
    container = SelectionContainer()
    rects = [
        SelectionRect(rect_id="5", bbox=(0,0,10,10), label="A"),
        SelectionRect(rect_id="9", bbox=(0,0,10,10), label="B")
    ]
    container.restore(rects)
    
    new_rect = container.add(bbox=(0,0,10,10))
    assert new_rect.rect_id == "10"

def test_restore_empty():
    container = SelectionContainer()
    container.restore([])
    
    new_rect = container.add(bbox=(0,0,10,10))
    assert new_rect.rect_id == "1"

def test_restore_non_numeric():
    container = SelectionContainer()
    rects = [
        SelectionRect(rect_id="abc", bbox=(0,0,10,10), label="A"),
        SelectionRect(rect_id="1", bbox=(0,0,10,10), label="B")
    ]
    container.restore(rects) # should not raise
    
    new_rect = container.add(bbox=(0,0,10,10))
    assert new_rect.rect_id == "2"

    container2 = SelectionContainer()
    container2.restore([SelectionRect(rect_id="abc", bbox=(0,0,10,10), label="A")])
    new_rect2 = container2.add(bbox=(0,0,10,10))
    assert new_rect2.rect_id == "1"
