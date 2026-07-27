import flet as ft
from custom_gui.viewer import ImageViewer, original_to_display
from custom_gui.selection import SelectionContainer, calculate_normalized_bbox

class SelectableImageViewer(ImageViewer):
    def __init__(self, image_src: str, img_w: float, img_h: float, win_w: float, win_h: float, **kwargs):
        super().__init__(image_src, img_w, img_h, win_w, win_h, **kwargs)
        
        self.selection_container = SelectionContainer()
        self.drag_start_point = None
        self.active_rect = None
        
        # We overlay rectangles on top of the image container using a Stack
        self.rects_layer = ft.Stack(
            controls=[],
            width=self.win_w,
            height=self.win_h,
        )
        
        # Intercept mouse drag events
        self.gesture_detector = ft.GestureDetector(
            on_pan_start=self._on_pan_start,
            on_pan_update=self._on_pan_update,
            on_pan_end=self._on_pan_end,
            width=self.win_w,
            height=self.win_h,
            drag_interval=10,
        )
        
        # Replace image container content with a Stack
        self.stack = ft.Stack(
            controls=[
                self.image,
                self.rects_layer,
                self.gesture_detector
            ],
            width=self.win_w,
            height=self.win_h,
        )
        
        self.image_container.content = self.stack
        
        # List view for showing selections
        self.selections_list = ft.ListView(
            spacing=10,
            padding=10,
            height=self.win_h,
            width=300
        )
        
        # Override overall layout
        self.content = ft.Row([
            ft.Column([
                self.controls_row,
                self.image_container
            ]),
            ft.Column([
                ft.Text("Selections:", weight=ft.FontWeight.BOLD),
                self.selections_list
            ])
        ])

    def _on_pan_start(self, e: ft.DragStartEvent):
        # Local coordinates within the stack
        self.drag_start_point = (e.local_x, e.local_y)
        self.active_rect = ft.Container(
            border=ft.border.all(2, ft.colors.RED),
            bgcolor=ft.colors.with_opacity(0.2, ft.colors.RED),
            left=e.local_x,
            top=e.local_y,
            width=0,
            height=0
        )
        self.rects_layer.controls.append(self.active_rect)
        self.rects_layer.update()

    def _on_pan_update(self, e: ft.DragUpdateEvent):
        if not self.drag_start_point or not self.active_rect:
            return
            
        start_x, start_y = self.drag_start_point
        end_x = e.local_x
        end_y = e.local_y
        
        x = min(start_x, end_x)
        y = min(start_y, end_y)
        w = abs(start_x - end_x)
        h = abs(start_y - end_y)
        
        self.active_rect.left = x
        self.active_rect.top = y
        self.active_rect.width = w
        self.active_rect.height = h
        
        self.active_rect.update()

    def _on_pan_end(self, e: ft.DragEndEvent):
        if not self.drag_start_point or not self.active_rect:
            return
            
        start_x, start_y = self.drag_start_point
        
        # In Flet, DragEndEvent doesn't easily give local_x, local_y, but we can compute from DragUpdate
        # or we just grab the final position from active_rect
        end_x = self.active_rect.left + self.active_rect.width if self.active_rect.left == start_x else self.active_rect.left
        end_y = self.active_rect.top + self.active_rect.height if self.active_rect.top == start_y else self.active_rect.top
        
        if self.active_rect in self.rects_layer.controls:
            self.rects_layer.controls.remove(self.active_rect)
        self.active_rect = None
        self.drag_start_point = None
        
        bbox = calculate_normalized_bbox(
            start_x, start_y, end_x, end_y,
            self.scale, self.offset_x, self.offset_y,
            self.img_w, self.img_h
        )
        
        # Don't add if area is 0
        if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
            self.selection_container.add(bbox)
        
        self._update_selections_ui()

    def _update_selections_ui(self):
        # Update drawn rectangles
        self.rects_layer.controls.clear()
        self.selections_list.controls.clear()
        
        for rect in self.selection_container.get_all():
            x1, y1, x2, y2 = rect.bbox
            dx1, dy1 = original_to_display(x1, y1, self.scale, self.offset_x, self.offset_y)
            dx2, dy2 = original_to_display(x2, y2, self.scale, self.offset_x, self.offset_y)
            
            w = dx2 - dx1
            h = dy2 - dy1
            
            drawn_rect = ft.Container(
                border=ft.border.all(2, ft.colors.BLUE),
                bgcolor=ft.colors.with_opacity(0.2, ft.colors.BLUE),
                left=dx1,
                top=dy1,
                width=w,
                height=h,
                content=ft.Text(rect.label, color=ft.colors.BLUE, weight=ft.FontWeight.BOLD)
            )
            self.rects_layer.controls.append(drawn_rect)
            
            # Update list
            def delete_rect(e, rid=rect.rect_id):
                self.selection_container.delete_by_id(rid)
                self._update_selections_ui()
                
            item = ft.Row([
                ft.Text(f"{rect.label}: ({x1:.1f}, {y1:.1f}) - ({x2:.1f}, {y2:.1f})"),
                ft.IconButton(icon=ft.icons.DELETE, on_click=delete_rect)
            ])
            self.selections_list.controls.append(item)
            
        self.rects_layer.update()
        self.selections_list.update()

    def _update_viewer(self):
        super()._update_viewer()
        self._update_selections_ui()

def main(page: ft.Page):
    # Dummy image path and dimensions for testing
    viewer = SelectableImageViewer(
        image_src="https://picsum.photos/800/600",
        img_w=800,
        img_h=600,
        win_w=600,
        win_h=500
    )
    page.add(viewer)

if __name__ == "__main__":
    ft.app(target=main)
