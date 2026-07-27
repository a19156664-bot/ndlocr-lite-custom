import os
import csv
import io
from custom_gui.region_filter import filter_lines_by_region
from custom_gui.text_assembler import assemble_text

def build_export_rows(image_name: str, rects: list, ocr_results: list) -> list:
    """
    Builds export rows from selection rectangles and OCR results.
    Each row is a dict matching the required CSV columns.
    """
    basename = os.path.basename(image_name.replace('\\', '/'))
    rows = []
    
    for rect in rects:
        x1, y1, x2, y2 = rect.bbox
        filtered_lines = filter_lines_by_region((x1, y1, x2, y2), ocr_results)
        text = assemble_text(filtered_lines)
        line_count = len(filtered_lines)
        
        row = {
            "image_name": basename,
            "region_id": rect.rect_id,
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "line_count": line_count,
            "text": text
        }
        rows.append(row)
        
    return rows

def rows_to_csv_text(rows: list) -> str:
    """
    Converts a list of dict rows to CSV formatted string.
    Uses proper escaping for commas and newlines.
    """
    output = io.StringIO(newline="")
    fieldnames = ["image_name", "region_id", "x1", "y1", "x2", "y2", "line_count", "text"]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()

def rows_to_txt_text(rows: list) -> str:
    """
    Converts a list of dict rows to human readable TXT formatted string.
    """
    blocks = []
    for row in rows:
        block = f"=== {row['image_name']} / Region {row['region_id']} ===\n{row['text']}"
        blocks.append(block)
    
    if not blocks:
        return ""
        
    return "\n\n".join(blocks) + "\n"
