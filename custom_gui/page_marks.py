import os

MARK_AD = "【広告】"
MARK_COVER = "【表紙】"

def mark_line(image_name: str, mark: str) -> str:
    basename = os.path.basename(image_name.replace('\\', '/'))
    return f"{basename}\t{mark}"

def append_mark_line(txt_path: str, line: str) -> bool:
    if os.path.exists(txt_path):
        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = [l.rstrip('\n') for l in f.readlines()]
        if line in lines:
            return False
            
    with open(txt_path, 'a', encoding='utf-8') as f:
        f.write(line + "\n")
    return True
