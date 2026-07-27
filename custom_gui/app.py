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
        
        self.latest_region_info = "None"

        self.ocr_results = []
        self.ocr_error = None
        try:
            if not os.path.exists(image_src):
                self.ocr_error = f"Image file not found: {image_src}"
            else:
                self.ocr_results = run_ocr_and_parse(image_src)
        except Exception as e:
            self.ocr_error = f"OCR failed: {str(e)}"
        
        self.status_text = ft.Text(
            self._get_status_message(),
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT
        )
        self.controls_row.controls.append(self.status_text)
        
        self.highlight_layer = ft.Stack(
            controls=[],
            width=self.img_w * self.scale,
            height=self.img_h * self.scale,
        )
        self.rects_layer = ft.Stack(
            controls=[],
            width=self.img_w * self.scale,
            height=self.img_h * self.scale,
        )
        
        self.gesture_detector = ft.GestureDetector(
            on_pan_start=self._on_pan_start,
            on_pan_update=self._on_pan_update,
            on_pan_end=self._on_pan_end,
            width=self.img_w * self.scale,
            height=self.img_h * self.scale,
            drag_interval=10,
        )
        
        if self.ocr_error:
            self.image_container.content = ft.Text(self.ocr_error, color=ft.Colors.RED, weight=ft.FontWeight.BOLD)
        else:
            self.stack = ft.Stack(
                controls=[
                    self.image,
                    self.highlight_layer,
                    self.rects_layer,
                    self.gesture_detector
                ],
                width=self.img_w * self.scale,
                height=self.img_h * self.scale,
            )
            self.image_container.content = self.stack
        
        self.selections_list = ft.ListView(
            spacing=10,
            padding=10,
            expand=True,
            width=300
        )
        
        self.content = ft.Row([
            ft.Column([
                self.controls_row,
                self.scrollable_image
            ], expand=True),
            ft.Column([
                ft.Text("Selections:", weight=ft.FontWeight.BOLD),
                self.selections_list
            ], expand=False)
        ], expand=True)

    def _get_status_message(self):
        filename = os.path.basename(self.image_src)
        return (f"File: {filename} | Size: {self.img_w}x{self.img_h} | Scale: {self.scale:.3f} | "
                f"Lines: {len(self.ocr_results)} | Last: {self.latest_region_info}")

    def update_layout(self, win_w: float, win_h: float):
        available_w = max(100, win_w - 320)
        available_h = max(100, win_h - 100)
        super().update_layout(available_w, available_h)
        if not self.ocr_error:
            self.highlight_layer.width = self.img_w * self.scale
            self.highlight_layer.height = self.img_h * self.scale
            self.rects_layer.width = self.img_w * self.scale
            self.rects_layer.height = self.img_h * self.scale
            self.gesture_detector.width = self.img_w * self.scale
            self.gesture_detector.height = self.img_h * self.scale
            self.stack.width = self.img_w * self.scale
            self.stack.height = self.img_h * self.scale
        self.status_text.value = self._get_status_message()

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
        if self.page:
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
        
        if self.page:
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
                    ft.IconButton(icon=ft.icons.DELETE, on_click=delete_rect)
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
            
        if self.selection_container.get_all():
            last_rect = self.selection_container.get_all()[-1]
            rx1, ry1, rx2, ry2 = last_rect.bbox
            filtered_for_last = filter_lines_by_region((rx1, ry1, rx2, ry2), self.ocr_results)
            self.latest_region_info = f"bbox({rx1:.1f},{ry1:.1f},{rx2:.1f},{ry2:.1f}), {len(filtered_for_last)} lines"
        else:
            self.latest_region_info = "None"
        
        self.status_text.value = self._get_status_message()
        if self.page:
            self.status_text.update()

        if not self.ocr_error and self.page:
            self.highlight_layer.update()
            self.rects_layer.update()
        if self.page:
            self.selections_list.update()

    def _update_viewer(self):
        super()._update_viewer()
        if not self.ocr_error:
            self.highlight_layer.width = self.img_w * self.scale
            self.highlight_layer.height = self.img_h * self.scale
            self.rects_layer.width = self.img_w * self.scale
            self.rects_layer.height = self.img_h * self.scale
            self.gesture_detector.width = self.img_w * self.scale
            self.gesture_detector.height = self.img_h * self.scale
            self.stack.width = self.img_w * self.scale
            self.stack.height = self.img_h * self.scale
        self.status_text.value = self._get_status_message()
        if self.page:
            self.status_text.update()
        self._update_selections_ui()

def main(page: ft.Page):
    # Use repository bundled image for offline operation
    image_path = os.path.join("resource", "digidepo_2531162_0024.jpg")
    
    viewer = SelectableImageViewer(
        image_src=image_path,
        img_w=2048,
        img_h=1446,
        win_w=page.window_width or 800,
        win_h=page.window_height or 600,
        expand=True
    )
    
    def on_resize(e):
        viewer.update_layout(e.width, e.height)
        page.update()
        
    page.on_resized = on_resize
    page.add(viewer)
    # Initialize with current size if possible
    viewer.update_layout(page.window_width or 800, page.window_height or 600)
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
