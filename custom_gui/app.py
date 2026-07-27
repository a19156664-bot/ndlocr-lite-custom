import flet as ft
from custom_gui.viewer import ImageViewer, original_to_display, apply_pan, InteractionMode, calculate_label_position
from custom_gui.selection import SelectionContainer, calculate_normalized_bbox
from custom_gui.ocr_bridge import run_ocr_and_parse
from custom_gui.region_filter import filter_lines_by_region
from custom_gui.text_assembler import assemble_text
from custom_gui.exporter import build_export_rows, rows_to_csv_text, rows_to_txt_text
import os
from enum import Enum, auto

class OcrState(Enum):
    IDLE = auto()
    RUNNING = auto()
    DONE = auto()
    ERROR = auto()

def get_ocr_status_text(state: OcrState, line_count: int = 0) -> str:
    if state == OcrState.IDLE:
        return "OCR pending..."
    elif state == OcrState.RUNNING:
        return "OCR processing..."
    elif state == OcrState.ERROR:
        return "OCR failed"
    elif state == OcrState.DONE:
        return f"Lines: {line_count}"
    return ""

class SelectableImageViewer(ImageViewer):
    def __init__(self, image_src: str, img_w: float, img_h: float, win_w: float, win_h: float, **kwargs):
        super().__init__(image_src, img_w, img_h, win_w, win_h, **kwargs)
        
        self.selection_container = SelectionContainer()
        self.drag_start_point = None
        self.drag_current_point = None
        self.active_rect = None
        self.drag_current_point = None
        
        self.mode_state = InteractionMode()
        
        self.ocr_results = []
        self.ocr_state = OcrState.IDLE if os.path.exists(image_src) else OcrState.ERROR
            
        self.mode_toggle = ft.SegmentedButton(
            segments=[
                ft.Segment(value="SELECT", icon=ft.Icon(ft.Icons.HIGHLIGHT_ALT), label=ft.Text("Select")),
                ft.Segment(value="PAN", icon=ft.Icon(ft.Icons.PAN_TOOL), label=ft.Text("Pan"))
            ],
            selected={self.mode_state.current},
            on_change=self._on_mode_change
        )
        self.controls_row.controls.append(self.mode_toggle)
        
        self.export_button = ft.IconButton(
            icon=ft.Icons.SAVE,
            tooltip="Export Results",
            on_click=self._on_export_click
        )
        self.controls_row.controls.append(self.export_button)
        
        self.file_picker = ft.FilePicker(on_result=self._on_file_picker_result)
        # The file_picker will be added to page.overlay when start_ocr or main runs,
        # but to be safe, we'll try to add it when the component is mounted (using did_mount) 
        # or we can rely on main() to add it. Let's add an explicit page attachment.
        
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
        
        # List view for showing selections
        self.selections_list = ft.ListView(
            spacing=10,
            padding=10,
            expand=True,
            width=300
        )
        
        # Override overall layout
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
        
        self.latest_region_info = "None"
        self.ocr_error = None
        if not os.path.exists(self.image_src):
            self.ocr_error = f"Error: Image not found at {self.image_src}"
        elif not self.ocr_results:
             # Could be that OCR failed but image exists. Let's not falsely show it here if run_ocr_and_parse is quiet.
             pass

        self.status_text = ft.Text(self._get_status_message(), size=12, color=ft.Colors.BLACK54)
        self.progress_ring = ft.ProgressRing(width=16, height=16, visible=False)
        self.status_row = ft.Row([self.progress_ring, self.status_text], spacing=5)
        
        if self.ocr_error:
            self.image_container.content = ft.Text(self.ocr_error, color=ft.Colors.RED, weight=ft.FontWeight.BOLD)
        else:
            self.stack = ft.Stack(
                controls=[
                    self.image_control,
                    self.highlight_layer,
                    self.rects_layer,
                    self.gesture_detector
                ],
                width=self.img_w * self.zoom_scale,
                height=self.img_h * self.zoom_scale,
            )
            self.image_container.content = self.stack
        
        # Override overall layout again with status
        self.content = ft.Column([
            ft.Row([
                ft.Column([
                    self.controls_row,
                    self.scrollable_image
                ], expand=True),
                ft.Column([
                    ft.Text("Selections:", weight=ft.FontWeight.BOLD),
                    self.selections_list
                ], expand=False)
            ], expand=True),
            ft.Container(
                content=self.status_row,
                bgcolor=ft.Colors.GREY_200,
                padding=5,
                alignment=ft.alignment.center_left,
            )
        ], expand=True)



    def did_mount(self):
        super().did_mount()
        if self.page:
            if self.file_picker not in self.page.overlay:
                self.page.overlay.append(self.file_picker)
                self.page.update()

    def start_ocr(self, page: ft.Page):
        if self.ocr_state == OcrState.ERROR:
            return
            
        self.ocr_state = OcrState.RUNNING
        self.progress_ring.visible = True
        if hasattr(self, 'status_text'):
            self.status_text.value = self._get_status_message()
            
        if self.page:
            self.status_row.update()
            
        def _run_ocr():
            try:
                results = run_ocr_and_parse(self.image_src)
                self._on_ocr_complete(results, None)
            except Exception as e:
                self._on_ocr_complete(None, str(e))
                
        page.run_thread(_run_ocr)
        
    def _on_ocr_complete(self, results, error):
        self.progress_ring.visible = False
        if error:
            self.ocr_state = OcrState.ERROR
            self.ocr_error = error
        else:
            self.ocr_state = OcrState.DONE
            self.ocr_results = results
            
        if hasattr(self, 'status_text'):
            self.status_text.value = self._get_status_message()
            
        if self.page:
            self.status_row.update()
            
        # Reprocess selections if any were drawn before OCR finished
        self._update_selections_ui()


    def _on_mode_change(self, e):
        if e.control.selected:
            self.mode_state.set_mode(list(e.control.selected)[0])
        else:
            # Prevent deselecting everything - fallback to current mode
            e.control.selected = {self.mode_state.current}
        if hasattr(self, 'status_text'):
            self.status_text.value = self._get_status_message()
        if self.page:
            self.update()

    def _on_export_click(self, e):
        rects = self.selection_container.get_all()
        if not rects:
            self.latest_region_info = "Nothing to export"
            self._update_status()
            return
            
        if self.ocr_state != OcrState.DONE:
            self.latest_region_info = "OCR not finished - cannot export yet"
            self._update_status()
            return
            
        default_filename = f"{os.path.splitext(os.path.basename(self.image_src))[0]}.csv"
        
        if self.page:
            self.file_picker.save_file(
                dialog_title="Export OCR Results",
                file_name=default_filename,
                allowed_extensions=["csv", "txt"]
            )

    def _on_file_picker_result(self, e: ft.FilePickerResultEvent):
        if not e.path:
            # User canceled
            return
            
        try:
            path_csv = e.path
            if not path_csv.lower().endswith(".csv"):
                # If they didn't add extension or added .txt, base it correctly
                base, ext = os.path.splitext(path_csv)
                if ext.lower() == ".txt":
                    path_csv = f"{base}.csv"
                    path_txt = e.path
                else:
                    path_csv = f"{path_csv}.csv"
                    path_txt = f"{base}.txt"
            else:
                path_txt = f"{os.path.splitext(path_csv)[0]}.txt"

            rects = self.selection_container.get_all()
            rows = build_export_rows(self.image_src, rects, self.ocr_results)
            
            csv_text = rows_to_csv_text(rows)
            txt_text = rows_to_txt_text(rows)
            
            # Write CSV with BOM
            with open(path_csv, "w", encoding="utf-8-sig", newline="") as f:
                f.write(csv_text)
                
            # Write TXT
            with open(path_txt, "w", encoding="utf-8") as f:
                f.write(txt_text)
                
            self.latest_region_info = f"Exported {len(rects)} regions to {os.path.basename(path_csv)} / {os.path.basename(path_txt)}"
        except Exception as ex:
            self.latest_region_info = f"Export failed: {str(ex)}"
            
        self._update_status()

    def _update_status(self):
        if hasattr(self, 'status_text'):
            self.status_text.value = self._get_status_message()
            if self.page:
                self.status_text.update()

    def _get_status_message(self):
        filename = os.path.basename(self.image_src)
        ocr_status = get_ocr_status_text(self.ocr_state, len(self.ocr_results))
        return (f"File: {filename} | Size: {self.img_w}x{self.img_h} | Scale: {self.zoom_scale:.3f} | Mode: {self.mode_state.current} | "
                f"{ocr_status} | Last: {self.latest_region_info}")

    def update_layout(self, win_w: float, win_h: float):
        available_w = max(100, win_w - 320)
        available_h = max(100, win_h - 100)
        super().update_layout(available_w, available_h)
        if not getattr(self, 'ocr_error', None):
            self.highlight_layer.width = self.img_w * self.zoom_scale
            self.highlight_layer.height = self.img_h * self.zoom_scale
            self.rects_layer.width = self.img_w * self.zoom_scale
            self.rects_layer.height = self.img_h * self.zoom_scale
            self.gesture_detector.width = self.img_w * self.zoom_scale
            self.gesture_detector.height = self.img_h * self.zoom_scale
            self.stack.width = self.img_w * self.zoom_scale
            self.stack.height = self.img_h * self.zoom_scale
        if hasattr(self, 'status_text'):
            self.status_text.value = self._get_status_message()

    def _on_pan_start(self, e: ft.DragStartEvent):
        # Local coordinates within the stack
        self.drag_start_point = (e.local_x, e.local_y)
        self.drag_current_point = None
        
        if self.mode_state.current == "SELECT":
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
        if not self.drag_start_point:
            return
            
        start_x, start_y = self.drag_start_point
        end_x = e.local_x
        end_y = e.local_y
        
        if self.mode_state.current == "SELECT":
            if not self.active_rect:
                return
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
                
        elif self.mode_state.current == "PAN":
            last_x, last_y = self.drag_current_point if self.drag_current_point else self.drag_start_point
            dx = end_x - last_x
            dy = end_y - last_y
            
            self.offset_x, self.offset_y = apply_pan(self.offset_x, self.offset_y, dx, dy)
            self.image_control.left = self.offset_x
            self.image_control.top = self.offset_y
            self.drag_current_point = (end_x, end_y)
            
            self._update_viewer()
            self._update_selections_ui()

    def _on_pan_end(self, e: ft.DragEndEvent):
        if not self.drag_start_point:
            return
            
        start_x, start_y = self.drag_start_point
        end_x, end_y = self.drag_current_point if self.drag_current_point else (start_x, start_y)
        
        if self.mode_state.current == "SELECT":
            if self.active_rect in self.rects_layer.controls:
                self.rects_layer.controls.remove(self.active_rect)
            self.active_rect = None
            
            bbox = calculate_normalized_bbox(
                start_x, start_y, end_x, end_y,
                self.zoom_scale, self.offset_x, self.offset_y,
                self.img_w, self.img_h
            )
            
            # Don't add if area is 0
            if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
                self.selection_container.add(bbox)
            
            self._update_selections_ui()
            
        self.drag_start_point = None
        self.drag_current_point = None

    def _update_selections_ui(self):
        # Update drawn rectangles
        self.rects_layer.controls.clear()
        self.highlight_layer.controls.clear()
        self.selections_list.controls.clear()
        
        for rect in self.selection_container.get_all():
            x1, y1, x2, y2 = rect.bbox
            dx1, dy1 = original_to_display(x1, y1, self.zoom_scale, self.offset_x, self.offset_y)
            dx2, dy2 = original_to_display(x2, y2, self.zoom_scale, self.offset_x, self.offset_y)
            
            w = dx2 - dx1
            h = dy2 - dy1
            
            drawn_rect = ft.Container(
                border=ft.border.all(2, ft.Colors.BLUE),
                bgcolor=ft.Colors.TRANSPARENT,
                left=dx1,
                top=dy1,
                width=w,
                height=h
            )
            self.rects_layer.controls.append(drawn_rect)
            
            label_height = 20.0  # Estimated height of the label
            label_left, label_top = calculate_label_position(dx1, dy1, label_height)
            
            label_container = ft.Container(
                content=ft.Text(rect.label, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD, size=14),
                bgcolor=ft.Colors.with_opacity(0.7, ft.Colors.BLUE),
                padding=ft.padding.symmetric(horizontal=4, vertical=2),
                border_radius=2,
                left=label_left,
                top=label_top,
            )
            self.rects_layer.controls.append(label_container)
            
            # 抽出対象の行をフィルタリングしてハイライト & テキスト生成
            filtered_lines = filter_lines_by_region((x1, y1, x2, y2), self.ocr_results)
            extracted_text = assemble_text(filtered_lines)
            
            # ハイライト層に抽出行の矩形を描画
            for line in filtered_lines:
                lx1, ly1, lx2, ly2 = line["bbox"]
                ldx1, ldy1 = original_to_display(lx1, ly1, self.zoom_scale, self.offset_x, self.offset_y)
                ldx2, ldy2 = original_to_display(lx2, ly2, self.zoom_scale, self.offset_x, self.offset_y)
                
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
            
        if self.page:
            self.highlight_layer.update()
            self.rects_layer.update()
            self.selections_list.update()


    def _update_viewer(self):
        super()._update_viewer()
        if not getattr(self, 'ocr_error', None):
            self.highlight_layer.width = self.img_w * self.zoom_scale
            self.highlight_layer.height = self.img_h * self.zoom_scale
            self.rects_layer.width = self.img_w * self.zoom_scale
            self.rects_layer.height = self.img_h * self.zoom_scale
            self.gesture_detector.width = self.img_w * self.zoom_scale
            self.gesture_detector.height = self.img_h * self.zoom_scale
            self.stack.width = self.img_w * self.zoom_scale
            self.stack.height = self.img_h * self.zoom_scale
        if hasattr(self, 'status_text'):
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
        win_w=page.width if page.width else 800,
        win_h=page.height if page.height else 600,
        expand=True
    )
    
    def on_resize(e):
        viewer.update_layout(page.width, page.height)
        page.update()
        
    page.on_resized = on_resize
    page.add(viewer)
    viewer.update_layout(page.width if page.width else 800, page.height if page.height else 600)
    page.update()
    
    # Start OCR in background thread after UI is drawn
    viewer.start_ocr(page)

if __name__ == "__main__":
    ft.app(target=main)
