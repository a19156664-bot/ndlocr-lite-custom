import sys, shutil, os
P = r"C:\Users\user\ndlocr-work\custom_gui\app.py"
BAK = P + ".injbak"
mode = sys.argv[1]

if mode == "restore":
    shutil.copy2(BAK, P); os.remove(BAK); print("restored"); sys.exit()
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
s = open(P, encoding="utf-8").read()

if mode == "no_persist_on_delete":
    old = """                        self.editing_region_id = None
                    self._update_selections_ui()
                    self._persist_work_state()"""
    new = """                        self.editing_region_id = None
                    self._update_selections_ui()"""
elif mode == "no_persist_on_draw":
    old = """            self._update_inline_editor()
            self._persist_work_state()"""
    new = """            self._update_inline_editor()"""
elif mode == "no_persist_on_mark":
    old = """        self.image_states[self.image_src]["mark"] = mark_str
        self._persist_work_state()"""
    new = """        self.image_states[self.image_src]["mark"] = mark_str"""
elif mode == "no_restore_on_switch":
    old = "            container, edits, mark = self._load_persisted_state(path)"
    new = "            container, edits, mark = SelectionContainer(), {}, None"
elif mode == "swallow_everything":
    old = "        except (OSError, TypeError, ValueError):"
    new = "        except Exception:"
elif mode == "next_id_reset":
    P2 = r"C:\Users\user\ndlocr-work\custom_gui\selection.py"
    BAK2 = P2 + ".injbak"
    if not os.path.exists(BAK2):
        shutil.copy2(P2, BAK2)
    s2 = open(P2, encoding="utf-8").read()
    old2 = "        self._next_id = max_id + 1"
    new2 = "        self._next_id = 1"
    assert s2.count(old2) == 1
    open(P2, "w", encoding="utf-8").write(s2.replace(old2, new2))
    print("injected", mode); sys.exit()
elif mode == "restore_selection":
    P2 = r"C:\Users\user\ndlocr-work\custom_gui\selection.py"
    BAK2 = P2 + ".injbak"
    shutil.copy2(BAK2, P2); os.remove(BAK2); print("restored selection.py"); sys.exit()
else:
    raise SystemExit("bad mode")

assert s.count(old) == 1, f"anchor count={s.count(old)}"
open(P, "w", encoding="utf-8").write(s.replace(old, new))
print("injected", mode)
