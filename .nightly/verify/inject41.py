import sys, shutil, os
P = r"C:\Users\user\ndlocr-work\custom_gui\app.py"
BAK = P + ".injbak"
mode = sys.argv[1]

if mode == "restore":
    shutil.copy2(BAK, P); os.remove(BAK); print("restored"); sys.exit()
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
s = open(P, encoding="utf-8").read()

if mode == "grab_back":
    # Windows で無効な GRAB / GRABBING を復活させる
    old = """            if self._is_dragging:
                self.gesture_detector.mouse_cursor = ft.MouseCursor.ALL_SCROLL
            else:
                self.gesture_detector.mouse_cursor = ft.MouseCursor.CLICK"""
    new = """            if self._is_dragging:
                self.gesture_detector.mouse_cursor = ft.MouseCursor.GRABBING
            else:
                self.gesture_detector.mouse_cursor = ft.MouseCursor.GRAB"""
elif mode == "select_becomes_pan_cursor":
    # SELECT のドラッグでも Pan のカーソルにしてしまう
    old = """        if self.mode_state.current == "SELECT":
            self.gesture_detector.mouse_cursor = ft.MouseCursor.PRECISE"""
    new = """        if self.mode_state.current == "SELECT":
            if self._is_dragging:
                self.gesture_detector.mouse_cursor = ft.MouseCursor.ALL_SCROLL
            else:
                self.gesture_detector.mouse_cursor = ft.MouseCursor.PRECISE"""
elif mode == "no_refresh_on_drag_end":
    # ドラッグ終了時にカーソルを戻さない
    old = """        self._is_dragging = False
        self._refresh_cursor()"""
    new = """        self._is_dragging = False"""
else:
    raise SystemExit("bad mode")

assert s.count(old) == 1, f"anchor count={s.count(old)}"
open(P, "w", encoding="utf-8", newline="").write(s.replace(old, new))
print("injected", mode)
