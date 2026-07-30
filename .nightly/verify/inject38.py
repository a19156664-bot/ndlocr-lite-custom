import sys, shutil, os
P = r"C:\Users\user\ndlocr-work\custom_gui\app.py"
BAK = P + ".injbak"
mode = sys.argv[1]

if mode == "restore":
    shutil.copy2(BAK, P); os.remove(BAK); print("restored"); sys.exit()
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
s = open(P, encoding="utf-8").read()

if mode == "next_no_advance":
    # 「次へ」を押してもページが進まない
    old = """            def on_next(e):
                close_dialog(e)
                self._on_next_click(None)"""
    new = """            def on_next(e):
                close_dialog(e)"""
elif mode == "last_page_offers_next":
    # 最終ページでも「次へ」を出してしまう
    old = '            if scope == "current" and self.btn_next and not self.btn_next.disabled:'
    new = '            if scope == "current":'
elif mode == "ctrls_before_guard":
    # 編集中ガードより前に Ctrl+S を置いてしまう
    old = """        if viewer.editing_region_id is not None or viewer.inline_editing_region_id is not None:"""
    new = """        if e.key == "S" and e.ctrl:
            viewer._start_export("current")
            return
        if viewer.editing_region_id is not None or viewer.inline_editing_region_id is not None:"""
else:
    raise SystemExit("bad mode")

assert s.count(old) == 1, f"anchor count={s.count(old)}"
open(P, "w", encoding="utf-8").write(s.replace(old, new))
print("injected", mode)
