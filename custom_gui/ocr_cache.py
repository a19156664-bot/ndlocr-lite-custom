import os
import json
import tempfile

CACHE_DIR_NAME = ".ndlocr_cache"
SCHEMA_VERSION = 1

def cache_dir_for(source_path: str) -> str:
    """
    Returns the directory that holds the cache for this source file.
    Does NOT create it.
    """
    source_dir = os.path.dirname(os.path.abspath(source_path))
    return os.path.join(source_dir, CACHE_DIR_NAME)

def cache_path_for(source_path: str, page_index=None) -> str:
    """
    Returns the specific cache file path for this source file and page index.
    """
    cache_dir = cache_dir_for(source_path)
    stem = os.path.splitext(os.path.basename(source_path))[0]
    if page_index is None:
        filename = f"{stem}.json"
    else:
        filename = f"{stem}_p{page_index + 1:04}.json"
    return os.path.join(cache_dir, filename)

def save_cache(source_path: str, results: list, page_index=None) -> str:
    """
    Creates the cache directory if needed and writes the cache file.
    Returns the path written.
    """
    cache_dir = cache_dir_for(source_path)
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_path = cache_path_for(source_path, page_index)
    
    try:
        st = os.stat(source_path)
        source_size = st.st_size
        source_mtime = st.st_mtime
    except OSError:
        source_size = 0
        source_mtime = 0.0

    data = {
        "schema": SCHEMA_VERSION,
        "source_name": os.path.basename(source_path),
        "source_size": source_size,
        "source_mtime": source_mtime,
        "page_index": page_index,
        "results": results
    }

    # Write to a temporary file in the same directory and os.replace() it
    fd, temp_path = tempfile.mkstemp(dir=cache_dir, prefix=".tmp_cache_", suffix=".json")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(temp_path, cache_path)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise
        
    return cache_path

from typing import Optional

def load_cache(source_path: str, page_index=None) -> Optional[list]:
    """
    Returns the results list, or None if invalid or stale.
    """
    cache_path = cache_path_for(source_path, page_index)
    
    if not os.path.exists(cache_path):
        return None
        
    try:
        st = os.stat(source_path)
        source_size = st.st_size
        source_mtime = st.st_mtime
    except OSError:
        # Source file doesn't exist
        return None
        
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        # Corrupt JSON
        return None
        
    if not isinstance(data, dict):
        return None
        
    if data.get("schema") != SCHEMA_VERSION:
        return None
        
    if data.get("source_size") != source_size:
        return None
        
    cache_mtime = data.get("source_mtime")
    if cache_mtime is None or abs(cache_mtime - source_mtime) > 1e-6:
        return None
        
    results = data.get("results")
    if not isinstance(results, list):
        return None
        
    # Convert bbox to tuple for each entry
    parsed_results = []
    for entry in results:
        if not isinstance(entry, dict):
            return None
        
        # Clone entry to avoid modifying the loaded dict if needed,
        # but here we can just update it
        new_entry = dict(entry)
        bbox = new_entry.get("bbox")
        if isinstance(bbox, list):
            new_entry["bbox"] = tuple(bbox)
        elif not isinstance(bbox, tuple):
            # Not a list or tuple, something is wrong
            return None
            
        parsed_results.append(new_entry)
        
    return parsed_results

def is_cached(source_path: str, page_index=None) -> bool:
    """
    True only if load_cache would return a list.
    """
    return load_cache(source_path, page_index) is not None
