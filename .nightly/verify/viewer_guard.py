# -*- coding: utf-8 -*-
"""ビューアの見張り（10-09 夜）。apply_fixes.py・reread_vertical.py の --viewer-other-issue-ok で使う。

ビューアは launch_viewer.py <号> で、その号の頁だけを開く。開いているビューアが「すべて別の号」なら、
書こうとしている号の保存とはぶつからない。号の分からないビューア（引数なし等）が 1 つでもあれば「同じ号かもしれない」とみなす。
"""
import subprocess


def viewer_issues():
    """走っている launch_viewer.py の号（分からなければ "?"）の集まり。"""
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ForEach-Object { $_.CommandLine }"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = set()
    for line in r.stdout.splitlines():
        if "launch_viewer.py" in line:
            rest = line.split("launch_viewer.py", 1)[1].split()
            out.add(rest[0] if rest and rest[0].isdigit() else "?")
    return out


def only_other_issues(num):
    """開いているビューアがすべて別の号なら True。"""
    issues = viewer_issues()
    return bool(issues) and str(num) not in issues and "?" not in issues
