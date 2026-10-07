import os
import ast
import pytest
import flet as ft
from custom_gui.web_image import web_image_src, show_web_image

def test_web_image_src(tmp_path):
    d = str(tmp_path)
    
    # 1. web_image_src(os.path.join(d, "国際寫眞新聞_141号_p0005.png"), d) == "/国際寫眞新聞_141号_p0005.png"
    p1 = os.path.join(d, "国際寫眞新聞_141号_p0005.png")
    assert web_image_src(p1, d) == "/国際寫眞新聞_141号_p0005.png"
    
    # 2. web_image_src(os.path.join(d, "sub", "x.png"), d) == "/sub/x.png"
    p2 = os.path.join(d, "sub", "x.png")
    assert web_image_src(p2, d) == "/sub/x.png"
    
    # 3. web_image_src(os.path.join(d, "..", "y.png"), d) raises ValueError
    p3 = os.path.join(d, "..", "y.png")
    with pytest.raises(ValueError):
        web_image_src(p3, d)
        
    # web_image_src(d, d) raises ValueError
    with pytest.raises(ValueError):
        web_image_src(d, d)

def test_show_web_image(tmp_path):
    d = str(tmp_path)
    # 4. img = ft.Image(src_base64="AAAA"); show_web_image(img, os.path.join(d, "a.png"), d):
    # img.src == "/a.png" and img.src_base64 in (None, "")
    img = ft.Image(src_base64="AAAA")
    p4 = os.path.join(d, "a.png")
    show_web_image(img, p4, d)
    assert img.src == "/a.png"
    assert img.src_base64 in (None, "")

def test_launch_viewer_ast():
    with open("launch_viewer.py", "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
        
    # 5. base64 and encode_base64 do not appear anywhere
    # no assignment target is an attribute named `src_base64`.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "base64", "Import of base64 found"
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "base64", "ImportFrom of base64 found"
            for alias in node.names:
                assert alias.name != "base64", "ImportFrom of base64 found"
        elif isinstance(node, ast.FunctionDef):
            assert node.name != "encode_base64", "FunctionDef encode_base64 found"
        elif isinstance(node, ast.Name):
            assert node.id not in ("base64", "encode_base64"), f"Name {node.id} found"
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id != "encode_base64", "Call to encode_base64 found"
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr != "encode_base64", "Call to attribute encode_base64 found"
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    assert target.attr != "src_base64", "Assignment to src_base64 found"

    # 6. show_web_image is called exactly 2 times
    show_web_image_calls = []
    
    # helper to find calls inside a specific node
    def find_calls_in_node(root_node, func_name):
        calls = []
        for n in ast.walk(root_node):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == func_name:
                calls.append(n)
        return calls

    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "BrowserImageViewer":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "_switch_image":
                    calls = find_calls_in_node(item, "show_web_image")
                    assert len(calls) == 1, "show_web_image not called exactly once in _switch_image"
                    call = calls[0]
                    # verify third argument is Name CACHE_DIR
                    assert isinstance(call.args[2], ast.Name)
                    assert call.args[2].id == "CACHE_DIR"
                    show_web_image_calls.extend(calls)
                    
                    # 7. check line numbers
                    ensure_rendered_calls = find_calls_in_node(item, "ensure_page_rendered")
                    if ensure_rendered_calls: # it is conditionally called
                         assert ensure_rendered_calls[0].lineno < call.lineno, "ensure_page_rendered not before show_web_image"
                    
                    super_switch_calls = []
                    for n in ast.walk(item):
                         if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "_switch_image":
                             if isinstance(n.func.value, ast.Call) and isinstance(n.func.value.func, ast.Name) and n.func.value.func.id == "super":
                                 super_switch_calls.append(n)
                    assert len(super_switch_calls) == 1
                    assert super_switch_calls[0].lineno < call.lineno, "super()._switch_image not before show_web_image"

        elif isinstance(node, ast.FunctionDef) and node.name == "main":
            calls = find_calls_in_node(node, "show_web_image")
            assert len(calls) == 1, "show_web_image not called exactly once in main"
            call = calls[0]
            assert isinstance(call.args[2], ast.Name)
            assert call.args[2].id == "CACHE_DIR"
            show_web_image_calls.extend(calls)
            
    assert len(show_web_image_calls) == 2, "show_web_image not called exactly 2 times globally"

    # 8. the ft.app call has keywords port=8555, view=ft.AppView.WEB_BROWSER and assets_dir=Name("CACHE_DIR")
    ft_app_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "ft" and node.func.attr == "app":
                ft_app_calls.append(node)
                
    assert len(ft_app_calls) == 1, "ft.app not called exactly once"
    app_call = ft_app_calls[0]
    
    kw_keys = [kw.arg for kw in app_call.keywords]
    assert "port" in kw_keys
    assert "view" in kw_keys
    assert "assets_dir" in kw_keys
    
    for kw in app_call.keywords:
        if kw.arg == "port":
            assert isinstance(kw.value, ast.Constant)
            assert kw.value.value == 8555
        elif kw.arg == "view":
            assert isinstance(kw.value, ast.Attribute)
            assert isinstance(kw.value.value, ast.Attribute)
            assert kw.value.value.value.id == "ft"
            assert kw.value.value.attr == "AppView"
            assert kw.value.attr == "WEB_BROWSER"
        elif kw.arg == "assets_dir":
            assert isinstance(kw.value, ast.Name)
            assert kw.value.id == "CACHE_DIR"
