import json
import os
import subprocess
import tempfile
import sys
from typing import List, Dict, Any

def run_ocr_and_parse(image_path: str) -> List[Dict[str, Any]]:
    """
    Run src/ocr.py via subprocess and parse its JSON output.
    
    We use subprocess here to run the upstream src/ocr.py script instead of direct
    import. This ensures strict isolation from the upstream codebase, prevents any 
    potential state/memory leaks from the ML models within the same process, and 
    perfectly aligns with the "additive architecture (C method)" rule where we just 
    use the upstream script as an external black box tool.
    
    Args:
        image_path: Path to the image file to process.
        
    Returns:
        List of dictionaries with normalized OCR results.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    filename = os.path.basename(image_path)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Construct the command to run the upstream OCR script
        cmd = [
            sys.executable,
            "src/ocr.py",
            "--sourceimg", image_path,
            "--output", temp_dir
        ]
        
        try:
            # Run the command
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"OCR failed:\nstdout: {e.stdout}\nstderr: {e.stderr}")
        
        # Look for the output JSON file
        # The script usually creates a file named like <original_image_name>.json
        name_without_ext = os.path.splitext(filename)[0]
        json_path = os.path.join(temp_dir, f"{name_without_ext}.json")
        
        if not os.path.exists(json_path):
            # Try to find any json file in case the naming convention differs
            json_files = [f for f in os.listdir(temp_dir) if f.endswith('.json')]
            if not json_files:
                raise FileNotFoundError(f"OCR output JSON not found in {temp_dir}")
            json_path = os.path.join(temp_dir, json_files[0])
            
        return parse_ocr_json(json_path, filename)


def parse_ocr_json(json_path: str, source_name: str) -> List[Dict[str, Any]]:
    """
    Parse the upstream OCR JSON output into a normalized format.
    
    Args:
        json_path: Path to the JSON output file.
        source_name: Name of the source image to attach to the results.
        
    Returns:
        List of dictionaries with normalized OCR results.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
            
    results = []
    
    # The JSON structure has "contents" which is a list of lists of blocks
    contents = data.get("contents", [])
    
    for pg in contents:
        for block in pg:
            if "boundingBox" not in block or "text" not in block:
                continue
                
            # Parse boundingBox
            # It can be a list of lists [[x, y], ...] or a list of strings ["x y", ...]
            raw_bbox = block["boundingBox"]
            xs = []
            ys = []
            for pt in raw_bbox:
                if isinstance(pt, str):
                    x, y = map(float, pt.split())
                    xs.append(x)
                    ys.append(y)
                elif isinstance(pt, (list, tuple)):
                    xs.append(float(pt[0]))
                    ys.append(float(pt[1]))
                    
            if not xs or not ys:
                continue
                
            x1, x2 = min(xs), max(xs)
            y1, y2 = min(ys), max(ys)
            
            # Ensure x1 < x2 and y1 < y2
            if x1 >= x2: x2 = x1 + 1
            if y1 >= y2: y2 = y1 + 1
            
            # Parse isVertical
            is_vert_raw = block.get("isVertical", False)
            if isinstance(is_vert_raw, str):
                is_vert = is_vert_raw.lower() == "true"
            else:
                is_vert = bool(is_vert_raw)
                
            confidence = float(block.get("confidence", 0.0))
            
            results.append({
                "text": str(block.get("text", "")),
                "bbox": (x1, y1, x2, y2),
                "confidence": confidence,
                "is_vertical": is_vert,
                "source_image": source_name
            })
            
    return results
