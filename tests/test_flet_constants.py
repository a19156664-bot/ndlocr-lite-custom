import ast
import os
import flet as ft

def test_flet_constants_exist():
    errors = []
    custom_gui_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'custom_gui')
    for root, _, files in os.walk(custom_gui_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=filepath)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Attribute):
                        # Check ft.Colors / ft.Icons
                        if isinstance(node.value, ast.Attribute):
                            if isinstance(node.value.value, ast.Name) and node.value.value.id == 'ft':
                                module_name = node.value.attr
                                if module_name in ['colors', 'Colors', 'icons', 'Icons']:
                                    attr_name = node.attr
                                    flet_module = getattr(ft, module_name)
                                    if not hasattr(flet_module, attr_name):
                                        errors.append(f"{filepath}: ft.{module_name}.{attr_name} does not exist.")
                        
                        # Check page.attr
                        if isinstance(node.value, ast.Name) and node.value.id == 'page':
                            attr_name = node.attr
                            if not hasattr(ft.Page, attr_name):
                                errors.append(f"{filepath}: page.{attr_name} does not exist on ft.Page.")
                        
                        # Check self.page.attr
                        elif isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name) and node.value.value.id == 'self' and node.value.attr == 'page':
                            attr_name = node.attr
                            if not hasattr(ft.Page, attr_name):
                                errors.append(f"{filepath}: self.page.{attr_name} does not exist on ft.Page.")

    if errors:
        raise AssertionError("\n".join(errors))

if __name__ == '__main__':
    test_flet_constants_exist()
    print("Test passed!")

def test_no_reserved_property_shadowing(tmp_path):
    """
    Checks that no custom classes that inherit from a Flet Control
    assign an instance attribute with the same name as a Flet property,
    if the value they assign is a Control (which would cause serialization bugs).
    """
    import inspect
    from unittest.mock import patch
    import sys
    import shutil
    
    src_img = "resource/digidepo_2531162_0024.jpg"
    test_img = str(tmp_path / "digidepo_2531162_0024.jpg")
    shutil.copy2(src_img, test_img)
    
    # We must patch OCR to prevent it from running when instantiating viewers
    with patch("custom_gui.app.run_ocr_and_parse") as mock_ocr:
        mock_ocr.return_value = []
        
        from custom_gui.viewer import ImageViewer
        from custom_gui.app import SelectableImageViewer
        
        # Instantiate to get the runtime instance attributes populated
        viewer1 = ImageViewer(test_img, 100, 100, 100, 100)
        viewer2 = SelectableImageViewer(test_img, 100, 100, 100, 100)
        
        errors = []
        
        for instance in [viewer1, viewer2]:
            cls = instance.__class__
            # Find all base classes that are from Flet
            flet_bases = [b for b in inspect.getmro(cls) if b.__module__.startswith("flet.")]
            
            for base in flet_bases:
                # Find all properties on the Flet base class
                for attr_name in dir(base):
                    if isinstance(getattr(base, attr_name, None), property):
                        # If the instance also has this attribute and it was assigned something
                        # It might be shadowed.
                        if hasattr(instance, attr_name):
                            val = getattr(instance, attr_name)
                            # Exception: 'content' and 'controls' and 'data' and such are explicitly
                            # intended to hold controls or user data by Flet.
                            # The bug happens when a reserved string/int/enum decoration property
                            # (like `image` or `scale`) is shadowed with a Control object.
                            # So we specifically check if it's holding a Control when it shouldn't.
                            if isinstance(val, ft.Control):
                                # Check if Flet actually expects a Control here.
                                # 'content' is meant to be a control.
                                if attr_name in ['content', 'controls']:
                                    continue
                                errors.append(
                                    f"{cls.__name__}.{attr_name} shadows a property on {base.__name__} "
                                    f"and holds a Control (type: {type(val).__name__}). This causes circular reference crashes."
                                )
                                
        if errors:
            raise AssertionError("\n".join(errors))
