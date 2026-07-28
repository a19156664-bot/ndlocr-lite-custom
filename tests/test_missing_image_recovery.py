import flet as ft
from custom_gui.app import SelectableImageViewer

def test_missing_image_recovery(tmp_path):
    import shutil
    # Start with a non-existent path
    viewer = SelectableImageViewer("non_existent_image.jpg", 800, 600, 800, 600)
    
    # Switch to a real image
    src_img = "resource/digidepo_2531162_0024.jpg"
    real_img = str(tmp_path / "digidepo_2531162_0024.jpg")
    shutil.copy2(src_img, real_img)
    viewer._switch_image(real_img)
    
    # Should not raise exception and should show stack
    assert getattr(viewer, 'stack', None) is not None
    assert viewer.image_container.content == viewer.stack
    
    # Switch back to missing
    viewer._switch_image("non_existent_image.jpg")
    assert isinstance(viewer.image_container.content, ft.Text)
