from custom_gui.viewer import original_to_display, display_to_original, apply_pan

def test_apply_pan_basic():
    assert apply_pan(0.0, 0.0, 50.0, 30.0) == (50.0, 30.0)

def test_apply_pan_accumulate():
    res1 = apply_pan(0.0, 0.0, 10.0, 10.0)
    res2 = apply_pan(res1[0], res1[1], 10.0, 10.0)
    assert res2 == (20.0, 20.0)

def test_coordinate_conversion_scale_1_0_with_offset():
    assert original_to_display(100.0, 200.0, 1.0, 50.0, 30.0) == (150.0, 230.0)
    assert display_to_original(150.0, 230.0, 1.0, 50.0, 30.0) == (100.0, 200.0)

def test_coordinate_conversion_scale_2_0_with_offset():
    assert original_to_display(100.0, 200.0, 2.0, 50.0, 30.0) == (250.0, 430.0)
    assert display_to_original(250.0, 430.0, 2.0, 50.0, 30.0) == (100.0, 200.0)

from custom_gui.viewer import InteractionMode

def test_mode_state_machine():
    sm = InteractionMode()
    assert sm.current == "SELECT"
    sm.set_mode("PAN")
    assert sm.current == "PAN"
    sm.set_mode("SELECT")
    assert sm.current == "SELECT"
    sm.set_mode("INVALID")
    assert sm.current == "SELECT"
