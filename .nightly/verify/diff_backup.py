import os, sys, json, glob, difflib
sys.stdout.reconfigure(encoding="utf-8")
B = r"C:\Users\user\ndlocr-lite-custom\work\backup\20261008_201637_置き換え前"
C = r"C:\Users\user\ndlocr-lite-custom\work\.ndlocr_cache"
changed_files, diffs = 0, []
for b in sorted(glob.glob(os.path.join(B, "*.work.json"))):
    name = os.path.basename(b)
    old = json.load(open(b, encoding="utf-8")); new = json.load(open(os.path.join(C, name), encoding="utf-8"))
    if old == new: continue
    changed_files += 1
    assert old["rects"] == new["rects"] and old["mark"] == new["mark"], name
    for k in set(old["edits"]) | set(new["edits"]):
        a, c = old["edits"].get(k, ""), new["edits"].get(k, "")
        if a != c:
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, c, autojunk=False).get_opcodes():
                if tag != "equal":
                    diffs.append((name[-14:-10], k, a[i1:i2], c[j1:j2]))
print("変わったファイル:", changed_files, " 字の違いのかたまり:", len(diffs))
for d in diffs: print("  ", d)