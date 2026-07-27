import os
import time
import pytest
from custom_gui.pdf_loader import (
    plan_pdf_pages, ensure_page_rendered, list_pdfs_in_folder, build_source_list
)
from reportlab.pdfgen import canvas
from PIL import Image

def create_pdf(path: str, pages: int):
    c = canvas.Canvas(path)
    for i in range(pages):
        c.drawString(100, 750, f"Page {i+1}")
        c.showPage()
    c.save()

def test_plan_pdf_pages_multi(tmp_path):
    pdf_path = str(tmp_path / "a.pdf")
    create_pdf(pdf_path, 3)
    
    cache_dir = str(tmp_path / "cache")
    os.makedirs(cache_dir)
    
    # [H](a) 3 page PDF returns exactly 3 tuples, no files created
    results = plan_pdf_pages(pdf_path, cache_dir)
    assert len(results) == 3
    
    basenames = [os.path.basename(r[0]) for r in results]
    assert basenames == ["a_p0001.png", "a_p0002.png", "a_p0003.png"]
    
    indices = [r[2] for r in results]
    assert indices == [0, 1, 2]
    
    # Assert NO file was created on disk by this call
    assert not os.path.exists(results[0][0])
    assert not os.path.exists(results[1][0])
    assert not os.path.exists(results[2][0])

def test_plan_pdf_pages_single(tmp_path):
    pdf_path = str(tmp_path / "single.pdf")
    create_pdf(pdf_path, 1)
    
    cache_dir = str(tmp_path / "cache")
    os.makedirs(cache_dir)
    
    # [H](b) 1 page PDF returns exactly 1 tuple
    results = plan_pdf_pages(pdf_path, cache_dir)
    assert len(results) == 1
    assert os.path.basename(results[0][0]) == "single_p0001.png"

def test_ensure_page_rendered(tmp_path):
    pdf_path = str(tmp_path / "doc.pdf")
    c = canvas.Canvas(pdf_path) # Default size is A4 in reportlab
    c.drawString(100, 750, "Test")
    c.showPage()
    c.save()
    
    cache_dir = str(tmp_path / "cache")
    os.makedirs(cache_dir)
    
    png_path = os.path.join(cache_dir, "doc_p0001.png")
    
    # [H](c) Creates the file, opens with Pillow, plausible dimensions
    returned_path = ensure_page_rendered(png_path, pdf_path, 0)
    assert returned_path == png_path
    assert os.path.exists(png_path)
    
    with Image.open(png_path) as img:
        w, h = img.size
        # Tolerance: pypdfium2 might round slightly differently, give +/- 5 pixels
        # Reportlab A4 is 595.275 x 841.889
        expected_w = int(595.275 * 300 / 72) # 2480
        expected_h = int(841.889 * 300 / 72) # 3507
        
        assert abs(w - expected_w) <= 5, f"Width {w} not within tolerance of {expected_w}"
        assert abs(h - expected_h) <= 5, f"Height {h} not within tolerance of {expected_h}"

def test_ensure_page_rendered_no_re_render(tmp_path):
    pdf_path = str(tmp_path / "doc2.pdf")
    create_pdf(pdf_path, 1)
    
    cache_dir = str(tmp_path / "cache")
    os.makedirs(cache_dir)
    
    png_path = os.path.join(cache_dir, "doc2_p0001.png")
    
    ensure_page_rendered(png_path, pdf_path, 0)
    assert os.path.exists(png_path)
    
    # Record mtime
    mtime1 = os.path.getmtime(png_path)
    
    # Delay briefly to ensure mtime would change if rewritten
    time.sleep(0.1)
    
    # Call again
    ensure_page_rendered(png_path, pdf_path, 0)
    
    mtime2 = os.path.getmtime(png_path)
    # [H](d) Assert mtime is unchanged
    assert mtime1 == mtime2

def test_list_pdfs_in_folder(tmp_path):
    # [H](e) list_pdfs_in_folder on folder with a.pdf, B.PDF, notes.txt and sub-folder
    folder = tmp_path / "pdfs"
    folder.mkdir()
    
    (folder / "a.pdf").touch()
    (folder / "B.PDF").touch()
    (folder / "notes.txt").touch()
    
    sub = folder / "sub"
    sub.mkdir()
    (sub / "c.pdf").touch()
    
    pdfs = list_pdfs_in_folder(str(folder))
    basenames = [os.path.basename(p) for p in pdfs]
    
    # case-insensitive sorting should yield a.pdf then B.PDF
    assert basenames == ["a.pdf", "B.PDF"]

def test_build_source_list_ordering(tmp_path):
    # [H](f) THE ORDERING TEST: b.jpg, a.pdf (3 pages), c.png
    folder = tmp_path / "mixed"
    folder.mkdir()
    
    (folder / "b.jpg").touch()
    (folder / "c.png").touch()
    
    pdf_path = str(folder / "a.pdf")
    create_pdf(pdf_path, 3)
    
    cache_dir = str(tmp_path / "cache")
    os.makedirs(cache_dir)
    
    paths, registry = build_source_list(str(folder), cache_dir)
    
    basenames = [os.path.basename(p) for p in paths]
    assert basenames == ["a_p0001.png", "a_p0002.png", "a_p0003.png", "b.jpg", "c.png"]
    
    # [H](g) Registry check
    a1 = os.path.join(cache_dir, "a_p0001.png")
    a2 = os.path.join(cache_dir, "a_p0002.png")
    a3 = os.path.join(cache_dir, "a_p0003.png")
    
    assert a1 in registry
    assert registry[a1] == (pdf_path, 0)
    assert registry[a2] == (pdf_path, 1)
    assert registry[a3] == (pdf_path, 2)
    
    b_jpg = str(folder / "b.jpg")
    c_png = str(folder / "c.png")
    assert b_jpg not in registry
    assert c_png not in registry

def test_build_source_list_empty(tmp_path):
    # [H](h) Empty folder returns ([], {}) and does not raise
    folder = tmp_path / "empty"
    folder.mkdir()
    
    cache_dir = str(tmp_path / "cache")
    paths, registry = build_source_list(str(folder), cache_dir)
    
    assert paths == []
    assert registry == {}

def test_plan_pdf_pages_invalid(tmp_path):
    # [H](i) File that is not really a PDF
    pdf_path = tmp_path / "not_real.pdf"
    with open(pdf_path, "wb") as f:
        f.write(b"not a pdf")
        
    cache_dir = str(tmp_path / "cache")
    
    # Decision: Return [] and do not crash
    results = plan_pdf_pages(str(pdf_path), cache_dir)
    assert results == []

