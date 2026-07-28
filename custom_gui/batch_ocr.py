import os
import tempfile
import subprocess
import sys
import time
import shutil
from dataclasses import dataclass, field
from typing import List, Callable, Tuple, Optional

from custom_gui.ocr_cache import is_cached, save_cache
from custom_gui.ocr_bridge import parse_ocr_json


@dataclass
class BatchResult:
    ok: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    failed: List[Tuple[str, str]] = field(default_factory=list)
    cancelled: bool = False


def plan_batch(image_paths: List[str]) -> Tuple[List[str], List[str]]:
    """
    Splits the list using ocr_cache.is_cached. Preserves input order.
    Returns two lists of paths: (to_ocr, already_cached).
    """
    to_ocr = []
    already_cached = []
    for path in image_paths:
        if is_cached(path):
            already_cached.append(path)
        else:
            to_ocr.append(path)
    return to_ocr, already_cached


def run_batch(image_paths: List[str], 
              progress: Optional[Callable[[int, int], None]] = None, 
              should_cancel: Optional[Callable[[], bool]] = None, 
              python_exe: Optional[str] = None) -> BatchResult:
    """
    Runs the batch OCR on the given images.
    """
    result = BatchResult()
    
    # 1. Plan batch
    to_ocr, already_cached = plan_batch(image_paths)
    result.skipped = already_cached
    
    if not to_ocr:
        return result
        
    # 2. Reject duplicate basenames
    basenames = {}
    valid_to_ocr = []
    for path in to_ocr:
        bn = os.path.basename(path)
        if bn in basenames:
            result.failed.append((path, f"Duplicate basename: {bn} conflicts with {basenames[bn]}"))
            # Also fail the first one if we haven't already
            first_path = basenames[bn]
            if first_path in valid_to_ocr:
                valid_to_ocr.remove(first_path)
                result.failed.append((first_path, f"Duplicate basename: {bn} conflicts with {path}"))
        else:
            basenames[bn] = path
            valid_to_ocr.append(path)
            
    if not valid_to_ocr:
        return result

    staging_dir = tempfile.mkdtemp(prefix=".tmp_batch_staging_")
    output_dir = tempfile.mkdtemp(prefix=".tmp_batch_output_")
    stdout_fd, stdout_path = tempfile.mkstemp(prefix=".tmp_batch_stdout_")
    stderr_fd, stderr_path = tempfile.mkstemp(prefix=".tmp_batch_stderr_")
    
    try:
        # 3. Build staging directory
        for path in valid_to_ocr:
            bn = os.path.basename(path)
            dst = os.path.join(staging_dir, bn)
            try:
                os.link(path, dst)
            except OSError:
                shutil.copy2(path, dst)
                
        # 4. Run src/ocr.py ONCE
        exe = python_exe if python_exe else sys.executable
        cmd = [
            exe,
            "src/ocr.py",
            "--sourcedir", staging_dir,
            "--output", output_dir,
            "--json-only"
        ]
        
        with os.fdopen(stdout_fd, 'w') as stdout_file, os.fdopen(stderr_fd, 'w') as stderr_file:
            proc = subprocess.Popen(cmd, stdout=stdout_file, stderr=stderr_file, text=True)
            
            # 5. Polling loop
            total_files = len(valid_to_ocr)
            last_done = -1
            
            while proc.poll() is None:
                # Check cancel
                if should_cancel and should_cancel():
                    proc.terminate()
                    time.sleep(0.5)
                    if proc.poll() is None:
                        proc.kill()
                    result.cancelled = True
                    break
                    
                # Count json outputs
                json_count = len([f for f in os.listdir(output_dir) if f.endswith('.json')])
                if json_count != last_done:
                    last_done = json_count
                    if progress:
                        progress(json_count, total_files)
                        
                time.sleep(1.0)
                
        # Read stderr once if process failed
        process_stderr = ""
        if proc.returncode is not None and proc.returncode != 0:
            try:
                with open(stderr_path, 'r', encoding='utf-8') as f:
                    process_stderr = f.read()
            except Exception:
                process_stderr = "Could not read stderr."
                
        # 6. Harvest results
        for path in valid_to_ocr:
            bn = os.path.basename(path)
            stem = os.path.splitext(bn)[0]
            json_path = os.path.join(output_dir, f"{stem}.json")
            
            if os.path.exists(json_path):
                try:
                    parsed_results = parse_ocr_json(json_path, bn)
                    save_cache(path, parsed_results)
                    result.ok.append(path)
                except Exception as e:
                    result.failed.append((path, f"Failed to parse or save cache: {e}"))
            else:
                if result.cancelled:
                    result.failed.append((path, "Cancelled before completion"))
                else:
                    err_msg = "Output JSON not found"
                    if proc.returncode is not None and proc.returncode != 0:
                        err_msg = f"OCR process failed with code {proc.returncode}. Stderr: {process_stderr}"
                    result.failed.append((path, err_msg))
                    
    finally:
        # 7. Always delete both temporary directories and files
        shutil.rmtree(staging_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)
        if os.path.exists(stdout_path):
            try: os.unlink(stdout_path)
            except OSError: pass
        if os.path.exists(stderr_path):
            try: os.unlink(stderr_path)
            except OSError: pass
        
    return result
