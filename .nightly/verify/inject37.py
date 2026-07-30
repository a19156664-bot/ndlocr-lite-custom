import sys, shutil, os
P = r"C:\Users\user\ndlocr-work\custom_gui\app.py"
BAK = P + ".injbak"
mode = sys.argv[1]

if mode == "restore":
    shutil.copy2(BAK, P); os.remove(BAK); print("restored"); sys.exit()

if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
s = open(P, encoding="utf-8").read()

if mode == "no_toggle_sync":
    # ツールバー表示の同期を落とす
    old = "        self.mode_toggle.selected = {self.mode_state.current}\n"
    new = ""
elif mode == "grabbing_in_select":
    # SELECT でも GRABBING にしてしまう
    old = """        if self.mode_state.current == "SELECT":
            self.gesture_detector.mouse_cursor = ft.MouseCursor.PRECISE
        elif self.mode_state.current == "PAN":
            if self._is_dragging:"""
    new = """        if self.mode_state.current == "SELECT" and not self._is_dragging:
            self.gesture_detector.mouse_cursor = ft.MouseCursor.PRECISE
        else:
            if self._is_dragging:"""
elif mode == "toggle_clears":
    # 右クリックで矩形を消してしまう
    old = "        self._refresh_cursor()\n        if hasattr(self, 'status_text'):\n            self.status_text.value = self._get_status_message()\n        if self.page:\n            if getattr(self.mode_toggle, 'page', None):"
    new = "        self.selection_container.clear()\n        self._refresh_cursor()\n        if hasattr(self, 'status_text'):\n            self.status_text.value = self._get_status_message()\n        if self.page:\n            if getattr(self.mode_toggle, 'page', None):"
else:
    raise SystemExit("bad mode")

assert s.count(old) == 1, f"anchor count={s.count(old)}"
open(P, "w", encoding="utf-8").write(s.replace(old, new))
print("injected", mode)
