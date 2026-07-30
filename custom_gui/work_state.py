import os
import json
import tempfile
from typing import Optional, List, Dict, Any, Tuple

CACHE_DIR_NAME = ".ndlocr_cache"
WORK_SCHEMA_VERSION = 1

def work_dir_for(source_path: str) -> str:
    source_dir = os.path.dirname(os.path.abspath(source_path))
    return os.path.join(source_dir, CACHE_DIR_NAME)

def work_path_for(source_path: str, page_index=None) -> str:
    cache_dir = work_dir_for(source_path)
    stem = os.path.splitext(os.path.basename(source_path))[0]
    if page_index is None:
        filename = f"{stem}.work.json"
    else:
        filename = f"{stem}_p{page_index + 1:04}.work.json"
    return os.path.join(cache_dir, filename)

def save_work_state(source_path: str, rects: Any, edits: Dict[str, str], mark: Optional[str], page_index=None) -> str:
    cache_dir = work_dir_for(source_path)
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_path = work_path_for(source_path, page_index)
    
    try:
        st = os.stat(source_path)
        source_size = st.st_size
        source_mtime = st.st_mtime
    except OSError:
        source_size = 0
        source_mtime = 0.0

    rects_list = []
    for r in rects:
        # Assuming r has rect_id, bbox, label
        rects_list.append({
            "rect_id": r.rect_id,
            "bbox": list(r.bbox),
            "label": r.label
        })

    data = {
        "schema": WORK_SCHEMA_VERSION,
        "source_name": os.path.basename(source_path),
        "source_size": source_size,
        "source_mtime": source_mtime,
        "page_index": page_index,
        "rects": rects_list,
        "edits": edits,
        "mark": mark
    }

    fd, temp_path = tempfile.mkstemp(dir=cache_dir, prefix=".tmp_work_", suffix=".json")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(temp_path, cache_path)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
#        raise
        
    return cache_path

def load_work_state(source_path: str, page_index=None) -> Optional[dict]:
    cache_path = work_path_for(source_path, page_index)
    
    if not os.path.exists(cache_path):
        return None
        
    try:
        st = os.stat(source_path)
        source_size = st.st_size
        source_mtime = st.st_mtime
    except OSError:
        return None
        
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
        
    if not isinstance(data, dict):
        return None
        
    if data.get("schema") != WORK_SCHEMA_VERSION:
        return None
        
    if data.get("source_size") != source_size:
        return None
        
    cache_mtime = data.get("source_mtime")
    if cache_mtime is None or abs(cache_mtime - source_mtime) > 1e-6:
        return None
        
    rects = data.get("rects")
    if not isinstance(rects, list):
        return None
        
    for entry in rects:
        if not isinstance(entry, dict):
            return None
        if "rect_id" not in entry or "bbox" not in entry or "label" not in entry:
            return None
        bbox = entry["bbox"]
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            return None
        for v in bbox:
            if not isinstance(v, (int, float)):
                return None
        entry["bbox"] = tuple(bbox)
        
    edits = data.get("edits")
    if not isinstance(edits, dict):
        return None
        
    return {
        "rects": rects,
        "edits": edits,
        "mark": data.get("mark")
    }

def clear_work_state(source_path: str, page_index=None) -> bool:
    cache_path = work_path_for(source_path, page_index)
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
            return True
        except OSError:
            return False
    return False
