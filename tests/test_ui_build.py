import json
import pytest
import flet as ft
from unittest.mock import patch
from custom_gui.app import SelectableImageViewer
from flet.core.control import EmbedJsonEncoder

@patch("custom_gui.app.run_ocr_and_parse")
def test_ui_build_and_update(mock_run_ocr_and_parse):
    """
    This test verifies that the Flet control tree can be successfully
    updated and serialized without triggering Circular reference errors.
    This explicitly caught the shadowing defect where self.image was assigned
    to a Control on a ft.Container.
    """
    # Setup mock OCR to return empty immediately
    mock_run_ocr_and_parse.return_value = []

    # Initialize viewer with bundled test image
    viewer = SelectableImageViewer(
        image_src="resource/digidepo_2531162_0024.jpg",
        img_w=2048,
        img_h=1446,
        win_w=800,
        win_h=600,
        expand=True
    )

    # Helper function to walk the tree, link parents (as Flet does internally when added to page),
    # and call before_update() plus simulate serialization.
    def process_control(control):
        if not hasattr(control, "before_update"):
            return
        
        # Trigger before_update to set __attrs (where Flet evaluates properties)
        control.before_update()
        
        # Simulate serialization to catch circular reference
        attrs = control._Control__attrs.copy()
        
        try:
            # We serialize via flet's internal EmbedJsonEncoder as Flet does in _convert_attr_json
            json.dumps(attrs, cls=EmbedJsonEncoder, separators=(",", ":"))
        except ValueError as e:
            if "Circular reference" in str(e):
                pytest.fail(f"Circular reference detected in {control.__class__.__name__}: {e}")
            raise
        except TypeError:
            pass

        # Recursively process children, mocking the parent linkage that Page handles
        if hasattr(control, "content") and control.content:
            control.content._Control__parent = control
            process_control(control.content)
            
        if hasattr(control, "controls") and control.controls:
            for child in control.controls:
                child._Control__parent = control
                process_control(child)

    # Process the viewer (the root Container)
    process_control(viewer)
