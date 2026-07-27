import flet as ft
from custom_gui.viewer import ImageViewer, original_to_display
from custom_gui.selection import SelectionContainer, calculate_normalized_bbox
from custom_gui.ocr_bridge import run_ocr_and_parse
from custom_gui.region_filter import filter_lines_by_region
from custom_gui.text_assembler import assemble_text
import os

class SelectableImageViewer(ImageViewer):
    def __init__(self, image_src: str, img_w: float, img_h: float, win_w: float, win_h: float, **kwargs):
        super().__init__(image_src, img_w, img_h, win_w, win_h, **kwargs)
        
        self.selection_container = SelectionContainer()
        self.drag_start_point = None
        self.drag_current_point = None
        self.active_rect = None
        self.drag_current_point = None
        
        # Run OCR once and store results
        self.ocr_results = []
        if os.path.exists(image_src):
            self.ocr_results = run_ocr_and_parse(image_src)
        
        # We overlay rectangles on top of the image container using a Stack
        self.highlight_layer = ft.Stack(
            controls=[],
            width=self.win_w,
            height=self.win_h,
        )
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
                self.highlight_layer,
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
        self.drag_current_point = None
        self.active_rect = ft.Container(
            border=ft.border.all(2, ft.Colors.RED),
            bgcolor=ft.Colors.with_opacity(0.2, ft.Colors.RED),
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
        
        self.drag_current_point = (e.local_x, e.local_y)
        
        self.active_rect.update()

    def _on_pan_end(self, e: ft.DragEndEvent):
        if not self.drag_start_point or not self.active_rect:
            return
            
        start_x, start_y = self.drag_start_point
        end_x, end_y = self.drag_current_point if self.drag_current_point else (start_x, start_y)
        
        if self.active_rect in self.rects_layer.controls:
            self.rects_layer.controls.remove(self.active_rect)
        self.active_rect = None
        self.drag_start_point = None
        self.drag_current_point = None
        
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
        self.highlight_layer.controls.clear()
        self.selections_list.controls.clear()
        
        for rect in self.selection_container.get_all():
            x1, y1, x2, y2 = rect.bbox
            dx1, dy1 = original_to_display(x1, y1, self.scale, self.offset_x, self.offset_y)
            dx2, dy2 = original_to_display(x2, y2, self.scale, self.offset_x, self.offset_y)
            
            w = dx2 - dx1
            h = dy2 - dy1
            
            drawn_rect = ft.Container(
                border=ft.border.all(2, ft.Colors.BLUE),
                bgcolor=ft.Colors.TRANSPARENT,
                left=dx1,
                top=dy1,
                width=w,
                height=h,
                content=ft.Text(rect.label, color=ft.Colors.BLUE, weight=ft.FontWeight.BOLD)
            )
            self.rects_layer.controls.append(drawn_rect)
            
            # 抽出対象の行をフィルタリングしてハイライト & テキスト生成
            filtered_lines = filter_lines_by_region((x1, y1, x2, y2), self.ocr_results)
            extracted_text = assemble_text(filtered_lines)
            
            # ハイライト層に抽出行の矩形を描画
            for line in filtered_lines:
                lx1, ly1, lx2, ly2 = line["bbox"]
                ldx1, ldy1 = original_to_display(lx1, ly1, self.scale, self.offset_x, self.offset_y)
                ldx2, ldy2 = original_to_display(lx2, ly2, self.scale, self.offset_x, self.offset_y)
                
                # Selection Rectと区別するため黄色系の半透明塗りつぶし (borderなし)
                highlight = ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.4, ft.Colors.YELLOW),
                    left=ldx1,
                    top=ldy1,
                    width=ldx2 - ldx1,
                    height=ldy2 - ldy1
                )
                self.highlight_layer.controls.append(highlight)
            
            # Update list (結果パネル)
            def delete_rect(e, rid=rect.rect_id):
                self.selection_container.delete_by_id(rid)
                self._update_selections_ui()
                
            item_content = ft.Column([
                ft.Row([
                    ft.Text(f"{rect.label}:", weight=ft.FontWeight.BOLD),
                    ft.IconButton(icon=ft.Icons.DELETE, on_click=delete_rect)
                ]),
                ft.Text(extracted_text, selectable=True)
            ])
            
            item = ft.Container(
                content=item_content,
                padding=10,
                border=ft.border.all(1, ft.Colors.OUTLINE),
                border_radius=5
            )
            
            self.selections_list.controls.append(item)
            
        self.highlight_layer.update()
        self.rects_layer.update()
        self.selections_list.update()

    def resize_viewer(self, win_w: float, win_h: float):
        super().resize_viewer(win_w, win_h)
        self.highlight_layer.width = self.win_w
        self.highlight_layer.height = self.win_h
        self.rects_layer.width = self.win_w
        self.rects_layer.height = self.win_h
        self.gesture_detector.width = self.win_w
        self.gesture_detector.height = self.win_h
        self.stack.width = self.win_w
        self.stack.height = self.win_h
        self.selections_list.height = self.win_h
        self._update_selections_ui()

    def _update_viewer(self):
        super()._update_viewer()
        self._update_selections_ui()

def main(page: ft.Page):
    # Use repository bundled image for offline operation
    image_path = os.path.join("resource", "digidepo_2531162_0024.jpg")
    
    # Calculate initial window size excluding the selections list panel width (300)
    initial_win_w = page.width - 300 if page.width > 300 else 800
    initial_win_h = page.height if page.height > 0 else 600
    
    viewer = SelectableImageViewer(
        image_src=image_path,
        img_w=2048,
        img_h=1446,
        win_w=initial_win_w,
        win_h=initial_win_h
    )
    
    def on_resized(e):
        new_win_w = page.width - 300 if page.width > 300 else 800
        new_win_h = page.height if page.height > 0 else 600
        viewer.resize_viewer(new_win_w, new_win_h)
        page.update()
        
    page.on_resized = on_resized
    
    page.add(viewer)

if __name__ == "__main__":
    ft.app(target=main)
