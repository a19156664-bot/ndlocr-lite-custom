import os

def web_image_src(image_path: str, assets_dir: str) -> str:
    """URL path of image_path inside assets_dir, for ft.Image.src in the
    web viewer: "/" + the relative path with "/" separators.
    Raises ValueError if image_path is not inside assets_dir."""
    abs_image = os.path.abspath(image_path)
    abs_assets = os.path.abspath(assets_dir)
    rel_path = os.path.relpath(abs_image, abs_assets)
    
    if rel_path == "." or rel_path == ".." or rel_path.startswith(".." + os.sep):
        raise ValueError("image_path is not inside assets_dir")
        
    return "/" + rel_path.replace(os.sep, "/")

def show_web_image(image_control, image_path: str, assets_dir: str) -> None:
    """Show image_path in image_control through the URL:
    image_control.src = web_image_src(image_path, assets_dir)
    image_control.src_base64 = None"""
    image_control.src = web_image_src(image_path, assets_dir)
    image_control.src_base64 = None
