import os
import pypdfium2
from typing import List, Tuple, Dict

RENDER_DPI = 300
PDF_EXTENSIONS = (".pdf",)

def list_pdfs_in_folder(folder: str) -> List[str]:
    """
    Returns full paths of PDFs directly inside the given folder,
    case-insensitive (.PDF counts), sorted by file name, NO recursion, [] when none.
    """
    if not os.path.exists(folder) or not os.path.isdir(folder):
        return []
        
    pdf_paths = []
    for entry in os.scandir(folder):
        if entry.is_file():
            ext = os.path.splitext(entry.name)[1].lower()
            if ext in PDF_EXTENSIONS:
                pdf_paths.append(entry.path)
                
    pdf_paths.sort(key=lambda path: os.path.basename(path).lower())
    return pdf_paths

def plan_pdf_pages(pdf_path: str, cache_dir: str) -> List[Tuple[str, str, int]]:
    """
    Opens the PDF ONLY to count pages. Renders NOTHING.
    Returns, for each page, (png_path, pdf_path, page_index).
    png_path must live under cache_dir and be named <pdf stem>_p<index+1, 0-padded to 4>.png
    """
    try:
        doc = pypdfium2.PdfDocument(str(pdf_path))
        page_count = len(doc)
        doc.close()
    except Exception:
        # e.g., corrupt PDF, password protected, or not a PDF
        return []

    results = []
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    for i in range(page_count):
        png_name = f"{stem}_p{i+1:04d}.png"
        png_path = os.path.join(cache_dir, png_name)
        results.append((png_path, pdf_path, i))

    return results

def ensure_page_rendered(png_path: str, pdf_path: str, page_index: int) -> str:
    """
    Renders that single page at RENDER_DPI and writes png_path,
    ONLY if png_path does not already exist. Returns png_path.
    Creates parent directories as needed.
    """
    if os.path.exists(png_path):
        return png_path

    os.makedirs(os.path.dirname(png_path), exist_ok=True)

    doc = pypdfium2.PdfDocument(str(pdf_path))
    scale = RENDER_DPI / 72.0
    pages = doc.render(pypdfium2.PdfBitmap.to_pil,
                       page_indices=[page_index],
                       scale=scale)
    pil_image = next(iter(pages)).convert("RGB")
    pil_image.save(png_path)
    doc.close()
    
    return png_path

def build_source_list(folder: str, cache_dir: str) -> Tuple[List[str], Dict[str, Tuple[str, int]]]:
    """
    Combines images and PDFs found in `folder` into ONE ordered list
    of displayable paths, plus a registry mapping
        png_path -> (pdf_path, page_index)
    for the PDF-derived entries only.
    
    ORDER:
      sort ALL SOURCE FILES by file name, case-insensitively;
      an image contributes itself;
      a PDF contributes all of its pages, in page order, consecutively.
    """
    from custom_gui.image_sequence import list_images_in_folder
    
    images = list_images_in_folder(folder)
    pdfs = list_pdfs_in_folder(folder)
    
    # Combine source files and sort them case-insensitively
    all_sources = images + pdfs
    all_sources.sort(key=lambda path: os.path.basename(path).lower())
    
    displayable_paths = []
    registry = {}
    
    for src in all_sources:
        ext = os.path.splitext(src)[1].lower()
        if ext in PDF_EXTENSIONS:
            pdf_pages = plan_pdf_pages(src, cache_dir)
            for png_path, pdf_path, page_index in pdf_pages:
                displayable_paths.append(png_path)
                registry[png_path] = (pdf_path, page_index)
        else:
            displayable_paths.append(src)
            
    return displayable_paths, registry
