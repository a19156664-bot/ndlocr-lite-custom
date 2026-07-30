"""DIAGNOSTIC PROBE - not a merge candidate.

Builds the app.py that Task 39c was supposed to produce (Task 39b's file minus
exactly the two guard lines) so that Jules's rewritten tests can be evaluated
at all. Restores the delivered file afterwards.
"""
import sys, shutil, os, subprocess
W = r"C:\Users\user\ndlocr-work"
P = os.path.join(W, "custom_gui", "app.py")
BAK = P + ".39cbak"
mode = sys.argv[1]

if mode == "restore":
    shutil.copy2(BAK, P); os.remove(BAK); print("restored delivered app.py"); sys.exit()

if not os.path.exists(BAK):
    shutil.copy2(P, BAK)

src = subprocess.run(
    ["git", "-C", W, "show", "integration/task-39b:custom_gui/app.py"],
    capture_output=True, check=True).stdout.decode("utf-8")

GUARD = """        if not hasattr(self, 'selections_list') or not getattr(self.selections_list, 'page', None):
            return
"""
assert src.count(GUARD) == 1, f"guard count={src.count(GUARD)}"
src = src.replace(GUARD, "")

assert "with self.selections_lock:" in src.split("def _update_selections_ui")[1][:400], \
    "RLock missing from _update_selections_ui"

with open(P, "w", encoding="utf-8", newline="") as f:
    f.write(src)
print("probe app.py written (39b minus the 2 guard lines, RLock intact)")
