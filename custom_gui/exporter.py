import os
import csv
import io
from custom_gui.region_filter import filter_lines_by_region
from custom_gui.text_assembler import assemble_text

def build_export_rows(image_name: str, rects: list, ocr_results: list, edited_texts: dict = None) -> list:
    """
    Builds export rows from selection rectangles and OCR results.
    Each row is a dict matching the required CSV columns.
    
    Args:
        edited_texts: Optional dictionary mapping region_id to edited string.
                      When provided, this string is used instead of the raw OCR text.
                      `line_count` remains the number of raw OCR lines inside the rect.
    """
    basename = os.path.basename(image_name.replace('\\', '/'))
    rows = []
    
    for rect in rects:
        x1, y1, x2, y2 = rect.bbox
        filtered_lines = filter_lines_by_region((x1, y1, x2, y2), ocr_results)
        line_count = len(filtered_lines)
        
        if edited_texts and rect.rect_id in edited_texts:
            text = edited_texts[rect.rect_id]
        else:
            text = assemble_text(filtered_lines)
        
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
    if not rows:
        return ""
        
    SEP = "｜"
    
    images_order = []
    image_segments = {}
    
    for row in rows:
        image_name = row['image_name']
        if image_name not in image_segments:
            image_segments[image_name] = []
            images_order.append(image_name)
            
        text = row.get('text', '').strip()
        if not text:
            continue
            
        # replace \r\n and \n with SEP
        text = text.replace('\r\n', SEP).replace('\n', SEP)
        
        # split by SEP, filter empty, and extend the segments list
        segments = [seg.strip() for seg in text.split(SEP)]
        segments = [seg for seg in segments if seg]
        
        image_segments[image_name].extend(segments)
        
    # Check if all segments are empty
    if not any(image_segments.values()):
        return ""

    if len(images_order) == 1:
        image_name = images_order[0]
        segments = image_segments[image_name]
        return SEP.join(segments) + "\n"
        
    lines = []
    for image_name in images_order:
        segments = image_segments[image_name]
        if not segments:
            continue
        line = f"{image_name}\t{SEP.join(segments)}"
        lines.append(line)
        
    return "\n".join(lines) + "\n"

def build_export_rows_multi(pages: list) -> list:
    """
    Builds export rows from multiple pages.
    
    Args:
        pages: List of dictionaries, where each dictionary represents one image's data.
               Format: {
                   "image_name": str,
                   "rects": list,
                   "ocr_results": list,
                   "edited_texts": dict (optional)
               }
               Alternatively, the tuple format is (image_path, rects, ocr_results, edited_texts).
               
    Returns:
        List of rows representing all the regions across all passed images.
        Rows are ordered by image (as provided in `pages`) and within an image by region order.
    """
    all_rows = []
    for page_data in pages:
        if isinstance(page_data, tuple):
            image_name = page_data[0]
            rects = page_data[1]
            ocr_results = page_data[2]
            edited_texts = page_data[3] if len(page_data) > 3 else None
        else:
            image_name = page_data["image_name"]
            rects = page_data.get("rects", [])
            ocr_results = page_data.get("ocr_results", [])
            edited_texts = page_data.get("edited_texts", None)
            
        if not rects:
            continue
            
        rows = build_export_rows(image_name, rects, ocr_results, edited_texts)
        all_rows.extend(rows)
        
    return all_rows
