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
                        if isinstance(node.value, ast.Attribute):
                            if isinstance(node.value.value, ast.Name) and node.value.value.id == 'ft':
                                module_name = node.value.attr
                                if module_name in ['colors', 'Colors', 'icons', 'Icons']:
                                    attr_name = node.attr
                                    flet_module = getattr(ft, module_name)
                                    if not hasattr(flet_module, attr_name):
                                        errors.append(f"{filepath}: ft.{module_name}.{attr_name} does not exist.")

    if errors:
        raise AssertionError("\n".join(errors))

if __name__ == '__main__':
    test_flet_constants_exist()
    print("Test passed!")
