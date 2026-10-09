# -*- coding: utf-8 -*-
"""166号から（10-09 入荷）印は PDF の注釈になった。注釈から枠の位置を頁の画像の画素（300dpi）で取り出す。

    四角（Square）   … その四角
    多角形（Polygon）… 頂点を囲む四角（L 字の記事など）
    手書き（Ink）    … 線 1 本ごとに、その線を囲む四角（写真説明を丸で囲んだ線。1 つの注釈に何本も入る）
    メモ欄（Popup）  … 無視（中身は空だった）

使い方: .venv\\Scripts\\python.exe .nightly\\verify\\annot_rects.py <PDF> [--json 出力先]
出力: 頁（1 始まり）ごとに [x1, y1, x2, y2, 種類] の並び。並びは注釈の順（作業者が描いた順）のまま。
"""
import sys, json, ctypes
import pypdfium2 as pdfium
import pypdfium2.raw as raw

DPI = 300  # custom_gui/pdf_loader.py の RENDER_DPI と同じ
SQUARE, POLYGON, INK = 5, 7, 15


def _box(points, page_h, s):
    xs = [p[0] for p in points]; ys = [p[1] for p in points]
    # PDF は左下が原点・画像は左上が原点
    return [round(min(xs) * s, 1), round((page_h - max(ys)) * s, 1),
            round(max(xs) * s, 1), round((page_h - min(ys)) * s, 1)]


def _vertices(a):
    n = raw.FPDFAnnot_GetVertices(a, None, 0)
    buf = (raw.FS_POINTF * n)()
    raw.FPDFAnnot_GetVertices(a, buf, n)
    return [(p.x, p.y) for p in buf]


def _ink_paths(a):
    out = []
    for k in range(raw.FPDFAnnot_GetInkListCount(a)):
        n = raw.FPDFAnnot_GetInkListPath(a, k, None, 0)
        buf = (raw.FS_POINTF * n)()
        raw.FPDFAnnot_GetInkListPath(a, k, buf, n)
        out.append([(p.x, p.y) for p in buf])
    return out


def page_rects(pdf_path):
    pdf = pdfium.PdfDocument(pdf_path)
    s = DPI / 72.0
    res = {}
    for i in range(len(pdf)):
        pg = pdf[i]
        page_h = pg.get_height()
        rects = []
        for k in range(raw.FPDFPage_GetAnnotCount(pg.raw)):
            a = raw.FPDFPage_GetAnnot(pg.raw, k)
            st = raw.FPDFAnnot_GetSubtype(a)
            if st == SQUARE:
                r = raw.FS_RECTF(); raw.FPDFAnnot_GetRect(a, ctypes.byref(r))
                rects.append(_box([(r.left, r.bottom), (r.right, r.top)], page_h, s) + ["四角"])
            elif st == POLYGON:
                rects.append(_box(_vertices(a), page_h, s) + ["多角形"])
            elif st == INK:
                for path in _ink_paths(a):
                    if len(path) >= 2:
                        rects.append(_box(path, page_h, s) + ["手書き"])
            raw.FPDFPage_CloseAnnot(a)
        res[i + 1] = rects
    pdf.close()
    return res


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    res = page_rects(sys.argv[1])
    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    kinds = {}
    for rs in res.values():
        for r in rs:
            kinds[r[4]] = kinds.get(r[4], 0) + 1
    print("頁", len(res), "枠のある頁", sum(1 for v in res.values() if v), "枠", sum(len(v) for v in res.values()), kinds)
