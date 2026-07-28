import flet as ft
from custom_gui.image_sequence import ImageSequence, list_images_in_folder
from custom_gui.viewer import ImageViewer, original_to_display, apply_pan, InteractionMode, calculate_label_position
from custom_gui.selection import SelectionContainer, calculate_normalized_bbox
from custom_gui.ocr_bridge import run_ocr_and_parse
from custom_gui.region_filter import filter_lines_by_region
from custom_gui.text_assembler import assemble_text
from custom_gui.exporter import build_export_rows, build_export_rows_multi, rows_to_csv_text, rows_to_txt_text
from custom_gui.rtl import convert_right_to_left
import os
import tempfile
from custom_gui.pdf_loader import build_source_list, ensure_page_rendered, plan_pdf_pages
from enum import Enum, auto

from custom_gui.ocr_scheduler import OcrScheduler

class OcrState(Enum):
    IDLE = auto()
    WAITING = auto()
    RUNNING = auto()
    DONE = auto()
    ERROR = auto()

def get_ocr_status_text(state: OcrState, line_count: int = 0) -> str:
    if state == OcrState.IDLE:
        return "OCR not started"
    elif state == OcrState.WAITING:
        return "OCR waiting"
    elif state == OcrState.RUNNING:
        return "OCR running"
    elif state == OcrState.ERROR:
        return "OCR failed"
    elif state == OcrState.DONE:
        return f"Lines: {line_count}"
    return ""

class SelectableImageViewer(ImageViewer):
    def __init__(self, image_src: str, img_w: float, img_h: float, win_w: float, win_h: float, **kwargs):
        self.frame_w = win_w
        self.frame_h = win_h
        available_w = max(100, win_w - 320)
        available_h = max(100, win_h - 100)
        super().__init__(image_src, img_w, img_h, available_w, available_h, **kwargs)
        
        self.ocr_scheduler = OcrScheduler()
        
        # New state variables for per-image state
        self.image_states = {}
        self.image_states[image_src] = {
            "selections": SelectionContainer(),
            "ocr_state": OcrState.IDLE if os.path.exists(image_src) else OcrState.ERROR,
            "ocr_results": [],
            "ocr_error": None if os.path.exists(image_src) else f"Error: Image not found at {image_src}",
            "edits": {}
        }
        
        self.selection_container = self.image_states[image_src]["selections"]
        self.edits = self.image_states[image_src]["edits"]
        self.ocr_state = self.image_states[image_src]["ocr_state"]
        self.ocr_results = self.image_states[image_src]["ocr_results"]
        self.ocr_error = self.image_states[image_src]["ocr_error"]
        
        self.sequence = ImageSequence([image_src])
        
        self.drag_start_point = None
        self.drag_current_point = None
        self.active_rect = None
        self.active_region_id = None
        self.editing_region_id = None
        
        self.pdf_cache_dir = tempfile.mkdtemp(prefix="ndlocr_pdf_")
        self.pdf_page_map = {}
        
        self.mode_state = InteractionMode()
            
        self.mode_toggle = ft.SegmentedButton(
            segments=[
                ft.Segment(value="SELECT", icon=ft.Icon(ft.Icons.HIGHLIGHT_ALT), label=ft.Text("Select")),
                ft.Segment(value="PAN", icon=ft.Icon(ft.Icons.PAN_TOOL), label=ft.Text("Pan"))
            ],
            selected={self.mode_state.current},
            on_change=self._on_mode_change
        )
        self.controls_row.controls.append(self.mode_toggle)
        
        self.btn_open_folder = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN,
            tooltip="Open Folder",
            on_click=self._on_open_folder_click
        )
        
        self.btn_open_pdf = ft.IconButton(
            icon=ft.Icons.PICTURE_AS_PDF,
            tooltip="PDFを開く",
            on_click=self._on_open_pdf_click
        )
        
        self.btn_prev = ft.IconButton(
            icon=ft.Icons.NAVIGATE_BEFORE,
            tooltip="Previous Image",
            on_click=self._on_prev_click,
            disabled=not self.sequence.has_prev()
        )
        
        self.btn_next = ft.IconButton(
            icon=ft.Icons.NAVIGATE_NEXT,
            tooltip="Next Image (Ctrl+N)",
            on_click=self._on_next_click,
            disabled=not self.sequence.has_next()
        )

        self.controls_row.controls.insert(0, self.btn_next)
        self.controls_row.controls.insert(0, self.btn_prev)
        self.controls_row.controls.insert(0, self.btn_open_pdf)
        self.controls_row.controls.insert(0, self.btn_open_folder)

        self.export_button = ft.PopupMenuButton(
            icon=ft.Icons.SAVE,
            tooltip="Export Results",
            items=[
                ft.PopupMenuItem(text="Current image only", on_click=lambda e: self._start_export("current")),
                ft.PopupMenuItem(text="All images", on_click=lambda e: self._start_export("all")),
            ]
        )
        self.controls_row.controls.append(self.export_button)
        
        self._export_scope = "current"
        self._file_picker_mode = "save"
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
            if not hasattr(self, 'stack'):
                self.stack = ft.Stack(controls=[self.image_control, self.highlight_layer, self.rects_layer, self.gesture_detector])
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

    def start_ocr(self, page: ft.Page, target_path: str = None):
        if target_path is None:
            target_path = self.image_src
        
        state = self.image_states.get(target_path)
        if not state:
            return
            
        if state["ocr_state"] in (OcrState.ERROR, OcrState.DONE):
            return
            
        start_now = self.ocr_scheduler.request_ocr(target_path)
        
        if not start_now:
            if state["ocr_state"] != OcrState.RUNNING:
                state["ocr_state"] = OcrState.WAITING
                if self.image_src == target_path:
                    self.ocr_state = OcrState.WAITING
                    self.progress_ring.visible = True
                    if hasattr(self, 'status_text'):
                        self.status_text.value = self._get_status_message()
                    if self.page:
                        self.status_row.update()
            return
            
        state["ocr_state"] = OcrState.RUNNING
        if self.image_src == target_path:
            self.ocr_state = OcrState.RUNNING
            self.progress_ring.visible = True
            if hasattr(self, 'status_text'):
                self.status_text.value = self._get_status_message()
            if self.page:
                self.status_row.update()
            
        def _run_ocr():
            try:
                results = run_ocr_and_parse(target_path)
                self._on_ocr_complete(results, None, target_path=target_path)
            except Exception as e:
                self._on_ocr_complete(None, str(e), target_path=target_path)
                
        page.run_thread(_run_ocr)
        
    def _on_ocr_complete(self, results, error, target_path=None):
        if target_path is None:
            target_path = self.image_src
        state = self.image_states.get(target_path)
        if not state:
            return
            
        if error:
            state["ocr_state"] = OcrState.ERROR
            state["ocr_error"] = error
        else:
            state["ocr_state"] = OcrState.DONE
            state["ocr_results"] = results
            
        if self.image_src == target_path:
            self.ocr_state = state["ocr_state"]
            self.ocr_error = state["ocr_error"]
            self.ocr_results = state["ocr_results"]
            
            self.progress_ring.visible = False
            if hasattr(self, 'status_text'):
                self.status_text.value = self._get_status_message()
            if self.page:
                self.status_row.update()
            self._update_selections_ui()
            
        current_page = self.image_src
        current_state = self.image_states.get(current_page)
        needs_ocr = current_state is not None and current_state["ocr_state"] in (OcrState.IDLE, OcrState.WAITING)
        
        next_page = self.ocr_scheduler.on_ocr_complete(target_path, current_page, needs_ocr)
        
        # Ensure the next scheduled page is triggered.
        
        if next_page and self.page:
            # Check again if it wasn't already processed
            next_state = self.image_states.get(next_page)
            if next_state and next_state["ocr_state"] in (OcrState.IDLE, OcrState.WAITING):
                self.start_ocr(self.page, next_page)


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


    def _on_open_pdf_click(self, e):
        self._file_picker_mode = "pdf"
        if self.page:
            self.file_picker.pick_files(
                dialog_title="Open PDF",
                allowed_extensions=["pdf"],
                allow_multiple=True
            )
            
    def _on_open_folder_click(self, e):
        self._file_picker_mode = "folder"
        if self.page:
            self.file_picker.get_directory_path(dialog_title="Open Folder")
            
    def _on_prev_click(self, e):
        if self.sequence.has_prev():
            self._switch_image(self.sequence.prev())
            
    def _on_next_click(self, e):
        if self.sequence.has_next():
            self._switch_image(self.sequence.next())
            
    def _switch_image(self, path: str):
        if not path:
            return
            
        # [A] Render before deciding whether the file exists.
        render_error = None
        if path in self.pdf_page_map:
            try:
                pdf_path, page_index = self.pdf_page_map[path]
                ensure_page_rendered(path, pdf_path, page_index)
            except Exception as e:
                render_error = f"Failed to render page: {str(e)}"
                
        if path not in self.image_states:
            if render_error:
                ocr_state = OcrState.ERROR
                ocr_error = render_error
            else:
                ocr_state = OcrState.IDLE if os.path.exists(path) else OcrState.ERROR
                ocr_error = None if os.path.exists(path) else f"Error: Image not found at {path}"
                
            self.image_states[path] = {
                "selections": SelectionContainer(),
                "ocr_state": ocr_state,
                "ocr_results": [],
                "ocr_error": ocr_error,
                "edits": {}
            }
            
        state = self.image_states[path]
        
        self.image_src = path
        self.selection_container = state["selections"]
        self.ocr_state = state["ocr_state"]
        self.ocr_results = state["ocr_results"]
        self.ocr_error = state["ocr_error"]
        self.edits = state["edits"]
        self.active_region_id = None
        self.editing_region_id = None
        
        # If the render error happened on a subsequent visit, update it
        if render_error and not self.ocr_error:
            self.ocr_error = render_error
            state["ocr_state"] = OcrState.ERROR
            state["ocr_error"] = self.ocr_error
                
        try:
            from PIL import Image
            with Image.open(path) as img:
                self.img_w, self.img_h = img.size
        except Exception as e:
            self.img_w, self.img_h = 800, 600
            if not self.ocr_error:
                self.ocr_error = f"Failed to open {os.path.basename(path)}: {str(e)}"
                state["ocr_state"] = OcrState.ERROR
                state["ocr_error"] = self.ocr_error
            
        self.image_control.src = path
        self.image_control.width = self.img_w
        self.image_control.height = self.img_h
        
        from custom_gui.viewer import calculate_fit_scale
        available_w = max(100, self.frame_w - 320)
        available_h = max(100, self.frame_h - 100)
        self.zoom_scale = calculate_fit_scale(self.img_w, self.img_h, available_w, available_h)
        
        self.offset_x = 0.0
        self.offset_y = 0.0
        
        if self.ocr_error:
            self.image_container.content = ft.Text(self.ocr_error, color=ft.Colors.RED, weight=ft.FontWeight.BOLD)
        else:
            if not hasattr(self, 'stack'):
                self.stack = ft.Stack(controls=[self.image_control, self.highlight_layer, self.rects_layer, self.gesture_detector])
            self.image_container.content = self.stack
            
        self.btn_prev.disabled = not self.sequence.has_prev()
        self.btn_next.disabled = not self.sequence.has_next()
        
        if self.page:
            self.btn_prev.update()
            self.btn_next.update()
            self.image_container.update()
            
        self.update_layout(self.frame_w, self.frame_h)
        self._update_viewer()
        self._update_selections_ui()
        
        self.progress_ring.visible = (self.ocr_state in (OcrState.RUNNING, OcrState.WAITING))
        if self.page:
            self.status_row.update()
        
        if self.ocr_state in (OcrState.IDLE, OcrState.WAITING) and self.page:
            self.start_ocr(self.page)

    def _collect_all_export_pages(self):
        pages = []
        skipped = 0
        regions_count = 0
        if hasattr(self.sequence, '_paths'):
            paths = self.sequence._paths
        else:
            paths = []
        
        for img_path in paths:
            state = self.image_states.get(img_path)
            if not state:
                continue
            rects = state.get("selections").get_all()
            if not rects:
                continue
            if state.get("ocr_state") != OcrState.DONE:
                skipped += 1
                continue
            
            pages.append({
                "image_name": img_path,
                "rects": rects,
                "ocr_results": state.get("ocr_results", []),
                "edited_texts": state.get("edits", {})
            })
            regions_count += len(rects)
            
        return pages, skipped, regions_count

    def _start_export(self, scope):
        self._export_scope = scope
        if scope == "current":
            rects = self.selection_container.get_all()
            if not rects:
                self.latest_region_info = "Nothing to export"
                self._update_status()
                return
            if self.ocr_state != OcrState.DONE:
                self.latest_region_info = "OCR not finished - cannot export yet"
                self._update_status()
                return
        elif scope == "all":
            pages, skipped, regions_count = self._collect_all_export_pages()
            if not pages and skipped == 0:
                self.latest_region_info = "Nothing to export"
                self._update_status()
                return
            if not pages and skipped > 0:
                self.latest_region_info = f"Nothing to export ({skipped} skipped: OCR not finished)"
                self._update_status()
                return
            
        default_filename = f"{os.path.splitext(os.path.basename(self.image_src))[0]}.csv"
        
        self._file_picker_mode = "save"
        if self.page:
            self.file_picker.save_file(
                dialog_title="Export OCR Results",
                file_name=default_filename,
                allowed_extensions=["csv", "txt"]
            )

    def _on_file_picker_result(self, e: ft.FilePickerResultEvent):
        if not e.path and not e.files:
            return
            
        if self._file_picker_mode == "folder":
            paths, registry = build_source_list(e.path, self.pdf_cache_dir)
            if not paths:
                self.latest_region_info = f"No images found in {os.path.basename(e.path)}"
                self._update_status()
            else:
                self.pdf_page_map.update(registry)
                self.sequence = ImageSequence(paths)
                self.latest_region_info = f"Opened folder {os.path.basename(e.path)} ({len(paths)} images/pages)"
                self._switch_image(self.sequence.current())
            return
            
        if self._file_picker_mode == "pdf":
            paths = []
            files = e.files if e.files else []
            # Files are not ordered in guaranteed way by flet in all platforms, but let's sort by name
            files.sort(key=lambda f: f.name.lower())
            
            for f in files:
                pdf_pages = plan_pdf_pages(f.path, self.pdf_cache_dir)
                for png_path, pdf_path, page_index in pdf_pages:
                    paths.append(png_path)
                    self.pdf_page_map[png_path] = (pdf_path, page_index)
            
            if not paths:
                self.latest_region_info = "No valid PDF pages found"
                self._update_status()
            else:
                self.sequence = ImageSequence(paths)
                self.latest_region_info = f"Opened PDF(s) ({len(paths)} pages)"
                self._switch_image(self.sequence.current())
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

            if self._export_scope == "current":
                rects = self.selection_container.get_all()
                rows = build_export_rows(self.image_src, rects, self.ocr_results, edited_texts=self.edits)
                num_regions = len(rects)
                success_msg = f"Exported {num_regions} regions to {os.path.basename(path_csv)} / {os.path.basename(path_txt)}"
            else:
                pages, skipped, regions_count = self._collect_all_export_pages()
                rows = build_export_rows_multi(pages)
                num_images = len(pages)
                if skipped > 0:
                    success_msg = f"Exported {regions_count} regions from {num_images} images ({skipped} skipped: OCR not finished)"
                else:
                    success_msg = f"Exported {regions_count} regions from {num_images} images"
            
            csv_text = rows_to_csv_text(rows)
            txt_text = rows_to_txt_text(rows)
            
            # Write CSV with BOM
            with open(path_csv, "w", encoding="utf-8-sig", newline="") as f:
                f.write(csv_text)
                
            # Write TXT
            with open(path_txt, "w", encoding="utf-8") as f:
                f.write(txt_text)
                
            self.latest_region_info = success_msg
        except Exception as ex:
            self.latest_region_info = f"Export failed: {str(ex)}"
            
        self._update_status()

    def _update_status(self):
        if hasattr(self, 'status_text'):
            self.status_text.value = self._get_status_message()
            if self.page:
                self.status_text.update()

    def _get_status_message(self):
        filename = os.path.basename(self.image_src) if self.image_src else "None"
        ocr_status = get_ocr_status_text(self.ocr_state, len(self.ocr_results))
        idx = self.sequence.index + 1 if self.sequence.count > 0 else 0
        seq_str = f"[{idx}/{self.sequence.count}]"
        return (f"{seq_str} File: {filename} | Size: {self.img_w}x{self.img_h} | Scale: {self.zoom_scale:.3f} | Mode: {self.mode_state.current} | "
                f"{ocr_status} | Last: {self.latest_region_info}")

    def update_layout(self, win_w: float, win_h: float):
        self.frame_w = win_w
        self.frame_h = win_h
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
        
        all_rects = self.selection_container.get_all()
        
        # Ensure active_region_id actually exists, if not reset it to the latest
        if self.active_region_id not in [r.rect_id for r in all_rects]:
            self.active_region_id = all_rects[-1].rect_id if all_rects else None
            
        for rect in all_rects:
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
                if rid in self.edits:
                    del self.edits[rid]
                if self.active_region_id == rid:
                    self.active_region_id = None
                if self.editing_region_id == rid:
                    self.editing_region_id = None
                self._update_selections_ui()
                
            def edit_rect(e, rid=rect.rect_id):
                self.active_region_id = rid
                self.editing_region_id = rid
                self._update_selections_ui()
                
            def commit_edit(e, rid=rect.rect_id, text_field=None):
                self.edits[rid] = text_field.value
                self.editing_region_id = None
                self._update_selections_ui()
                
            def cancel_edit(e, rid=rect.rect_id):
                self.editing_region_id = None
                self._update_selections_ui()
                
            def restore_rect(e, rid=rect.rect_id):
                if rid in self.edits:
                    del self.edits[rid]
                self._update_selections_ui()
                
            def make_active(e, rid=rect.rect_id):
                if self.active_region_id != rid:
                    self.active_region_id = rid
                    self._update_selections_ui()

            has_edit = rect.rect_id in self.edits
            display_text = self.edits[rect.rect_id] if has_edit else extracted_text
            label_suffix = " (edited)" if has_edit else ""

            def rtl_rect(e, rid=rect.rect_id, current_text=display_text, orig_text=extracted_text):
                if not current_text:
                    return
                converted = convert_right_to_left(current_text)
                if converted == orig_text:
                    if rid in self.edits:
                        del self.edits[rid]
                else:
                    self.edits[rid] = converted
                self._update_selections_ui()

            is_active = (self.active_region_id == rect.rect_id)
            is_editing = (self.editing_region_id == rect.rect_id)

            if is_editing:
                tf = ft.TextField(
                    value=display_text,
                    multiline=True,
                    autofocus=True
                )
                content_area = ft.Column([
                    tf,
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.SAVE, tooltip="Save (Commit)", on_click=lambda e, rid=rect.rect_id, tf=tf: commit_edit(e, rid, tf)),
                        ft.IconButton(icon=ft.Icons.CANCEL, tooltip="Cancel", on_click=cancel_edit)
                    ])
                ])
            else:
                content_area = ft.Text(display_text, selectable=True)
                
            buttons = [
                ft.IconButton(icon=ft.Icons.EDIT, tooltip="Edit", on_click=edit_rect),
                ft.IconButton(icon=ft.Icons.SWAP_HORIZ, tooltip="右から変換", on_click=rtl_rect)
            ]
            if has_edit:
                buttons.append(ft.IconButton(icon=ft.Icons.RESTORE, tooltip="Revert to OCR", on_click=restore_rect))
            buttons.append(ft.IconButton(icon=ft.Icons.DELETE, tooltip="Delete", on_click=delete_rect))

            item_content = ft.Column([
                ft.Row([
                    ft.Text(f"{rect.label}{label_suffix}:", weight=ft.FontWeight.BOLD),
                    ft.Row(buttons, spacing=0)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                content_area
            ])
            
            border_color = ft.Colors.GREEN if is_active else ft.Colors.OUTLINE
            border_width = 2 if is_active else 1
            item = ft.Container(
                content=item_content,
                padding=10,
                border=ft.border.all(border_width, border_color),
                border_radius=5,
                on_click=make_active
            )
            
            self.selections_list.controls.append(item)
            
        def _safe_update(control):
            if control is not None and control.page:
                control.update()

        if self.page:
            _safe_update(self.highlight_layer)
            _safe_update(self.rects_layer)
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
    from PIL import Image
    image_path = os.path.join("resource", "digidepo_2531162_0024.jpg")
    
    try:
        with Image.open(image_path) as img:
            img_w, img_h = img.size
    except Exception:
        img_w, img_h = 2048, 1446
    
    viewer = SelectableImageViewer(
        image_src=image_path,
        img_w=img_w,
        img_h=img_h,
        win_w=page.width if page.width else 800,
        win_h=page.height if page.height else 600,
        expand=True
    )
    
    def on_resize(e):
        viewer.update_layout(page.width, page.height)
        page.update()
        
    def on_keyboard(e: ft.KeyboardEvent):
        if viewer.editing_region_id is not None:
            # Suppress global shortcuts while editing text
            return
            
        if e.key == "N" and e.ctrl:
            if viewer.btn_next and not viewer.btn_next.disabled:
                viewer._on_next_click(None)
        elif e.key == "F2":
            if viewer.active_region_id:
                viewer.editing_region_id = viewer.active_region_id
                viewer._update_selections_ui()
                
    page.on_resized = on_resize
    page.on_keyboard_event = on_keyboard
    page.add(viewer)
    viewer.update_layout(page.width if page.width else 800, page.height if page.height else 600)
    page.update()
    
    viewer.start_ocr(page)

if __name__ == "__main__":
    ft.app(target=main)
