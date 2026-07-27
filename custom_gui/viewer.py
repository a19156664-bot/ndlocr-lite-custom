import flet as ft
from typing import Tuple

def original_to_display(x: float, y: float, scale: float, offset_x: float = 0.0, offset_y: float = 0.0) -> Tuple[float, float]:
    """
    Convert original image coordinates to display coordinates.
    """
    return (x * scale + offset_x, y * scale + offset_y)

def display_to_original(x: float, y: float, scale: float, offset_x: float = 0.0, offset_y: float = 0.0) -> Tuple[float, float]:
    """
    Convert display coordinates to original image coordinates.
    """
    if scale == 0:
        return (0.0, 0.0)
    return ((x - offset_x) / scale, (y - offset_y) / scale)

def calculate_fit_scale(img_w: float, img_h: float, win_w: float, win_h: float) -> float:
    """
    Calculate the scale to fit the image into the window.
    """
    if img_w <= 0 or img_h <= 0:
        return 1.0
    return min(win_w / img_w, win_h / img_h)

class ImageViewer(ft.Container):
    def __init__(self, image_src: str, img_w: float, img_h: float, win_w: float, win_h: float, **kwargs):
        super().__init__(**kwargs)
        self.image_src = image_src
        self.img_w = img_w
        self.img_h = img_h
        self.win_w = win_w
        self.win_h = win_h
        
        self.scale = calculate_fit_scale(img_w, img_h, win_w, win_h)
        self.offset_x = 0.0
        self.offset_y = 0.0
        
        self.image = ft.Image(
            src=self.image_src,
            width=self.img_w * self.scale,
            height=self.img_h * self.scale,
            fit=ft.ImageFit.CONTAIN
        )
        
        self.zoom_in_btn = ft.ElevatedButton("Zoom In", on_click=self.zoom_in)
        self.zoom_out_btn = ft.ElevatedButton("Zoom Out", on_click=self.zoom_out)
        self.fit_btn = ft.ElevatedButton("Fit", on_click=self.fit)
        
        self.controls_row = ft.Row([self.zoom_in_btn, self.zoom_out_btn, self.fit_btn])
        
        self.image_container = ft.Container(
            content=self.image,
            width=self.img_w * self.scale,
            height=self.img_h * self.scale,
            alignment=ft.alignment.top_left,
        )
        
        self.scrollable_image = ft.Column(
            [ft.Row([self.image_container], scroll=ft.ScrollMode.AUTO, expand=True)],
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )

        self.content = ft.Column([
            self.controls_row,
            self.scrollable_image
        ], expand=True)
        
    def zoom_in(self, e):
        self.scale *= 1.2
        self._update_viewer()
        self.update()
        
    def zoom_out(self, e):
        self.scale /= 1.2
        self._update_viewer()
        self.update()
        
    def fit(self, e):
        self.scale = calculate_fit_scale(self.img_w, self.img_h, self.win_w, self.win_h)
        self._update_viewer()
        self.update()
        
    def _update_viewer(self):
        self.image.width = self.img_w * self.scale
        self.image.height = self.img_h * self.scale
        self.image_container.width = self.img_w * self.scale
        self.image_container.height = self.img_h * self.scale
        self.image.update()
        self.image_container.update()

    def update_layout(self, win_w: float, win_h: float):
        self.win_w = win_w
        self.win_h = win_h
        self.scale = calculate_fit_scale(self.img_w, self.img_h, self.win_w, self.win_h)
        self._update_viewer()

