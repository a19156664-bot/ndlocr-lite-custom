import sys, shutil, os
P = r"C:\Users\user\ndlocr-work\custom_gui\app.py"
BAK = P + ".injbak"
mode = sys.argv[1]

if mode == "restore":
    shutil.copy2(BAK, P); os.remove(BAK); print("restored"); sys.exit()
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
s = open(P, encoding="utf-8").read()

if mode == "no_nodata_dialog":
    # OCRデータ無しの拒否をステータス欄だけに戻す（今回の不具合そのもの）
    old = """                self.latest_region_info = "Nothing to export"
                self._update_status()
                self._save_dialog = ft.AlertDialog(
                    title=ft.Text("保存できません"),
                    content=ft.Text("OCRデータがございません。"),
                    actions=[ft.TextButton("OK", autofocus=True, on_click=close_dialog)],
                    modal=True
                )
                if self.page:
                    self.page.open(self._save_dialog)
                return
            if rects and self.ocr_state != OcrState.DONE:"""
    new = """                self.latest_region_info = "Nothing to export"
                self._update_status()
                return
            if rects and self.ocr_state != OcrState.DONE:"""
elif mode == "restore_overwrite_guard":
    # 上書き時に書き込まず止まる（Enter が効かない元の状態）
    old = """        self._do_write_and_show_done(scope, csv_path, txt_path)

    def _do_write_and_show_done(self, scope, csv_path, txt_path):"""
    new = """        if os.path.exists(csv_path) or os.path.exists(txt_path):
            return
        self._do_write_and_show_done(scope, csv_path, txt_path)

    def _do_write_and_show_done(self, scope, csv_path, txt_path):"""
elif mode == "switch_keeps_pending":
    # ページを移動しても予約が残る
    old = "        self._pending_export = None\n        \n        # [A] Render before"
    new = "        # [A] Render before"
elif mode == "pending_ignores_page":
    # 別ページに移動していても保存してしまう
    old = """            if state["ocr_state"] == OcrState.DONE and self.image_src == target_path:
                self._start_export("current")"""
    new = """            if state["ocr_state"] == OcrState.DONE:
                self._start_export("current")"""
elif mode == "pending_not_cleared":
    # 予約を消さずに再入する
    old = """        if self._pending_export == target_path:
            self._pending_export = None"""
    new = """        if self._pending_export == target_path:
            pass"""
else:
    raise SystemExit("bad mode")

assert s.count(old) == 1, f"anchor count={s.count(old)}"
open(P, "w", encoding="utf-8", newline="").write(s.replace(old, new))
print("injected", mode)
