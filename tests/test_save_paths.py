import os
from custom_gui.save_paths import resolve_export_dir, export_basename, export_targets

def test_resolve_export_dir():
    assert resolve_export_dir(os.path.join("a", "b", "c.png")) == os.path.abspath(os.path.join("a", "b"))
    assert resolve_export_dir(os.path.join("a", "b", "c.png"), pdf_source=os.path.join("x", "y.pdf")) == os.path.abspath(os.path.join("x"))

def test_export_basename():
    assert export_basename(os.path.join("a", "b", "foo_0008.jpg"), "current", "") == "foo_0008"
    assert export_basename("any", "all", os.path.join("C:", os.sep, "scan", "国際寫眞新聞_028号")) == "国際寫眞新聞_028号_all"
    assert export_basename("any", "all", "C:\\") == "export_all"
    assert export_basename("any", "all", "/") == "export_all"

def test_export_targets():
    csv_path, txt_path = export_targets(os.path.join("a", "b", "foo.png"), "current")
    assert csv_path == os.path.abspath(os.path.join("a", "b", "foo.csv"))
    assert txt_path == os.path.abspath(os.path.join("a", "b", "foo.txt"))
    
    csv_path, txt_path = export_targets(
        os.path.join("tmp", "ndlocr_pdf_xyz", "page_0003.png"),
        "all",
        pdf_source=os.path.join("C:", os.sep, "scan", "book.pdf")
    )
    assert csv_path == os.path.abspath(os.path.join("C:", os.sep, "scan", "scan_all.csv"))
    assert txt_path == os.path.abspath(os.path.join("C:", os.sep, "scan", "scan_all.txt"))
