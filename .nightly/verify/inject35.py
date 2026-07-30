import sys, shutil, os
P = r"C:\Users\user\ndlocr-t35\custom_gui\app.py"
BAK = P + ".bak"

mode = sys.argv[1]

if mode == "restore":
    shutil.copy2(BAK, P)
    print("restored")
    sys.exit()

if not os.path.exists(BAK):
    shutil.copy2(P, BAK)

s = open(P, encoding="utf-8").read()

if mode == "f":
    old = 'ft.Text(f"{rect.label}{label_suffix} [\u6539\u884c {n_breaks}]:", weight=ft.FontWeight.BOLD)'
    new = 'ft.Text(f"{rect.label}{label_suffix}:", weight=ft.FontWeight.BOLD)'
elif mode == "d":
    old = """        if os.path.exists(csv_path) or os.path.exists(txt_path):
            self._show_overwrite_dialog(scope, csv_path, txt_path)
        else:
            self._do_write_and_show_done(scope, csv_path, txt_path)"""
    new = """        self._do_write_and_show_done(scope, csv_path, txt_path)"""
elif mode == "b":
    old = "        csv_path, txt_path = export_targets(self.image_src, scope, pdf_source)"
    new = ("        csv_path, txt_path = export_targets(self.image_src, scope, pdf_source)\n"
           "        self.file_picker.save_file(dialog_title='x')")
else:
    raise SystemExit("bad mode")

assert s.count(old) == 1, f"anchor count = {s.count(old)}"
open(P, "w", encoding="utf-8").write(s.replace(old, new))
print("injected", mode)
