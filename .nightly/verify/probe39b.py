"""Diagnostic probe: temporarily remove the unrequested guard Jules added to
_update_selections_ui, to prove it is the cause of the 13 failures.
Restores the file afterwards. Does NOT fix anything."""
import sys, shutil, os
P = r"C:\Users\user\ndlocr-work\custom_gui\app.py"
BAK = P + ".probebak"
mode = sys.argv[1]

if mode == "restore":
    shutil.copy2(BAK, P); os.remove(BAK); print("restored"); sys.exit()
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
s = open(P, encoding="utf-8").read()

GUARD = """        if not hasattr(self, 'selections_list') or not getattr(self.selections_list, 'page', None):
            return
"""
assert s.count(GUARD) == 1, f"guard count={s.count(GUARD)}"
open(P, "w", encoding="utf-8").write(s.replace(GUARD, ""))
print("guard removed")
