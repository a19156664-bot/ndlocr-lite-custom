import sys, shutil, os
W = r"C:\Users\user\ndlocr-work"
mode = sys.argv[1]

TARGETS = {
    "newline": os.path.join(W, "custom_gui", "page_marks.py"),
    "keyerror": os.path.join(W, "custom_gui", "app.py"),
}

if mode == "restore":
    for p in TARGETS.values():
        b = p + ".injbak"
        if os.path.exists(b):
            shutil.copy2(b, p); os.remove(b)
    print("restored")
    sys.exit()

P = TARGETS[mode]
b = P + ".injbak"
if not os.path.exists(b):
    shutil.copy2(P, b)
s = open(P, encoding="utf-8").read()

if mode == "newline":
    old = """        if os.path.getsize(txt_path) > 0:
            with open(txt_path, 'rb') as f:
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b'\\n':
                    needs_newline = True
"""
    new = ""
elif mode == "keyerror":
    old = "        self.mark = state.get(\"mark\")"
    new = "        self.mark = state[\"mark\"]"

assert s.count(old) == 1, f"anchor count={s.count(old)}"
open(P, "w", encoding="utf-8").write(s.replace(old, new))
print("injected", mode)
