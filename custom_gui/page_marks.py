import os

MARK_AD = "【広告】"
MARK_COVER = "【表紙】"

def mark_line(image_name: str, mark: str) -> str:
    basename = os.path.basename(image_name.replace('\\', '/'))
    return f"{basename}\t{mark}"

def append_mark_line(txt_path: str, line: str) -> bool:
    needs_newline = False
    if os.path.exists(txt_path):
        with open(txt_path, 'r', encoding='utf-8') as f:
            lines = [l.rstrip('\n') for l in f.readlines()]
        if line in lines:
            return False
            
        if os.path.getsize(txt_path) > 0:
            with open(txt_path, 'rb') as f:
                f.seek(-1, os.SEEK_END)
                if f.read(1) != b'\n':
                    needs_newline = True
            
    with open(txt_path, 'a', encoding='utf-8') as f:
        if needs_newline:
            f.write("\n")
        f.write(line + "\n")
    return True
