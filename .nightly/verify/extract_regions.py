# -*- coding: utf-8 -*-
"""水色マークの範囲だけを OCR 結果から抜き出す（精度確認用）。

前提: 先に全面 OCR を走らせ、<画像フォルダ>/_ocr結果/ に .json があること。

    mkdir jpg\\_ocr結果
    <venv>\\Scripts\\python.exe src\\ocr.py --sourcedir <画像フォルダ> --output jpg\\_ocr結果
    <venv>\\Scripts\\python.exe .nightly\\verify\\extract_regions.py [画像フォルダ]

出力: <画像フォルダ>/_ocr結果/_範囲抽出.txt

**アプリと同じ経路を通す。** 別実装で近似しない。ここで出る文字列は、
アプリで「マーク読取」→「保存」したときに得られるものと同じである。

    parse_ocr_json         アプリが OCR 結果を読む形
    detect_marks           水色マーク（Task 45）
    detect_page_mark       橙色 = 【広告】（Task 47）
    count_rtl_lines        横書き（右→左）の行数（Task 50）
    filter_lines_by_region 矩形で行を絞る
    assemble_text          縦書きの読み順で組む

2026-08-28 に 52枚で使用。118範囲 / 7,040字。
"""
import os
import sys
import glob
import io

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from custom_gui.ocr_bridge import parse_ocr_json            # noqa: E402
from custom_gui.mark_detector import load_image, detect_marks, detect_page_mark  # noqa: E402
from custom_gui.region_filter import filter_lines_by_region  # noqa: E402
from custom_gui.text_assembler import assemble_text          # noqa: E402
from custom_gui.rtl import count_rtl_lines                   # noqa: E402


def main(src):
    ocr = os.path.join(src, '_ocr結果')
    out = os.path.join(ocr, '_範囲抽出.txt')
    if not os.path.isdir(ocr):
        print('OCR 結果がありません: %s' % ocr)
        print('先に src/ocr.py --sourcedir ... --output ... を走らせること')
        return

    buf = io.StringIO()
    rows = []
    for img_path in sorted(glob.glob(os.path.join(src, '*.jpg'))):
        name = os.path.basename(img_path)
        page = name.split('_')[-1].replace('.jpg', '')
        json_path = os.path.join(ocr, os.path.splitext(name)[0] + '.json')
        if not os.path.exists(json_path):
            rows.append((page, '', 0, 0, 0, 0))
            continue

        lines = parse_ocr_json(json_path, name)
        img = load_image(img_path)
        regions = detect_marks(img)
        mark = detect_page_mark(img)

        buf.write('=' * 70 + '\n')
        buf.write('p%s   %s   OCR行数 %d   マーク %d 個%s\n'
                  % (page, name, len(lines), len(regions),
                     ('   ' + mark) if mark else ''))
        buf.write('=' * 70 + '\n')

        if not regions:
            buf.write('（水色マークなし）\n\n')
            rows.append((page, mark or '', 0, len(lines), 0, 0))
            continue

        chars = rtl = 0
        for i, r in enumerate(regions, 1):
            x1, y1, x2, y2 = r.bbox
            picked = filter_lines_by_region((x1, y1, x2, y2), lines)
            text = assemble_text(picked)
            n_rtl = count_rtl_lines(picked)
            chars += len(text.replace('\n', ''))
            rtl += n_rtl
            buf.write('--- 範囲 %d [%s]  x=%d y=%d w=%d h=%d  行 %d%s\n'
                      % (i, r.kind, x1, y1, x2 - x1, y2 - y1, len(picked),
                         ('  [横書き? %d]' % n_rtl) if n_rtl else ''))
            buf.write(text.rstrip() + '\n\n')

        rows.append((page, mark or '', len(regions), len(lines), chars, rtl))

    with io.open(out, 'w', encoding='utf-8') as f:
        f.write(buf.getvalue())

    print('page  広告   範囲  OCR行  抽出文字  横書き')
    for page, mark, nreg, nlines, nchars, nrtl in rows:
        if nreg or mark:
            print('  %s  %-6s %3d  %5d  %7d  %5d'
                  % (page, mark, nreg, nlines, nchars, nrtl))
    print()
    print('合計: 範囲 %d / 抽出文字 %d / 横書き行 %d'
          % (sum(r[2] for r in rows), sum(r[4] for r in rows), sum(r[5] for r in rows)))
    print('書き出し: %s' % out)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'jpg'))
