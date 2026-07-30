import sys, shutil, os
P = r"C:\Users\user\ndlocr-t35b\custom_gui\app.py"
BAK = P + ".injbak"
mode = sys.argv[1]

if mode == "restore":
    shutil.copy2(BAK, P)
    os.remove(BAK)
    print("restored")
    sys.exit()

if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
s = open(P, encoding="utf-8").read()

if mode == "skip_confirm":
    old = """        if os.path.exists(csv_path) or os.path.exists(txt_path):
            self._show_overwrite_dialog(scope, csv_path, txt_path)
        else:
            self._do_write_and_show_done(scope, csv_path, txt_path)"""
    new = """        self._do_write_and_show_done(scope, csv_path, txt_path)"""
elif mode == "dead_overwrite":
    old = """        def on_overwrite(e):
            if self.page:
                self.page.close(self._save_dialog)
            self._save_dialog = None
            self._do_write_and_show_done(scope, csv_path, txt_path)"""
    new = """        def on_overwrite(e):
            pass"""
else:
    raise SystemExit("bad mode")

assert s.count(old) == 1, f"anchor count={s.count(old)}"
open(P, "w", encoding="utf-8").write(s.replace(old, new))
print("injected", mode)
