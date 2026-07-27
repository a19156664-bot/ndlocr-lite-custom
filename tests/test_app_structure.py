import ast
import os

def test_no_https_in_app():
    app_path = os.path.join(os.path.dirname(__file__), '..', 'custom_gui', 'app.py')
    with open(app_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert 'https://' not in content, "The string 'https://' must not appear in custom_gui/app.py"

def test_update_calls_in_event_handlers():
    app_path = os.path.join(os.path.dirname(__file__), '..', 'custom_gui', 'app.py')
    viewer_path = os.path.join(os.path.dirname(__file__), '..', 'custom_gui', 'viewer.py')
    
    # Check app.py for page.update() inside on_resize
    with open(app_path, 'r', encoding='utf-8') as f:
        app_source = f.read()
    
    app_ast = ast.parse(app_source)
    
    found_on_resize = False
    has_page_update_in_resize = False
    
    for node in ast.walk(app_ast):
        if isinstance(node, ast.FunctionDef) and node.name == 'on_resize':
            found_on_resize = True
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Attribute) and child.func.attr == 'update':
                        if isinstance(child.func.value, ast.Name) and child.func.value.id == 'page':
                            has_page_update_in_resize = True
    
    assert found_on_resize, "on_resize function not found in app.py"
    assert has_page_update_in_resize, "page.update() not called inside on_resize in app.py"
    
    # Check viewer.py for self.update() in zoom handlers
    with open(viewer_path, 'r', encoding='utf-8') as f:
        viewer_source = f.read()
    
    viewer_ast = ast.parse(viewer_source)
    
    methods_to_check = ['zoom_in', 'zoom_out', 'fit']
    found_methods = set()
    valid_methods = set()
    
    for node in ast.walk(viewer_ast):
        if isinstance(node, ast.FunctionDef) and node.name in methods_to_check:
            found_methods.add(node.name)
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Attribute) and child.func.attr == 'update':
                        if isinstance(child.func.value, ast.Name) and child.func.value.id == 'self':
                            valid_methods.add(node.name)
    
    assert found_methods == set(methods_to_check), f"Not all required zoom methods found. Found: {found_methods}"
    assert valid_methods == set(methods_to_check), f"self.update() is missing in some zoom methods. Valid ones: {valid_methods}"

