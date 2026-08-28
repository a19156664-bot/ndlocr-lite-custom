# -*- coding: utf-8 -*-
"""手描きマークの検出結果を、承認者が目で見られる画像にする。

    <venv>\\Scripts\\python.exe .nightly\\verify\\marks_overlay.py [画像フォルダ]

省略時は jpg/ を見る。出力は <画像フォルダ>/_検出結果/ に置く。

    _一覧.jpg            全ページの縮小一覧。検出したページに赤枠
    pXXXXXX_検出.jpg     1ページずつ原寸。赤=囲み・緑=傍線・数字は検出順

ヘッドレスで確かめられないのは「画面に出る絵」だけである。この道具は
その一歩手前まで——どこを範囲と判定したか——を目に見える形にする。
2026-08-27 に 52枚で使用。
"""
import os
import sys
import glob

import cv2
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

from custom_gui.mark_detector import load_image, detect_marks  # noqa: E402

BOX_COLOR = (0, 0, 255)      # BGR 赤 = 囲み
LINE_COLOR = (0, 160, 0)     # BGR 緑 = 傍線


def main(src):
    out = os.path.join(src, '_検出結果')
    os.makedirs(out, exist_ok=True)

    rows, thumbs = [], []
    for p in sorted(glob.glob(os.path.join(src, '*.jpg'))):
        name = os.path.basename(p)
        page = name.split('_')[-1].replace('.jpg', '')
        img = load_image(p)
        h, w = img.shape[:2]
        regions = detect_marks(img)

        vis = img.copy()
        nb = nl = 0
        for i, r in enumerate(regions, 1):
            x1, y1, x2, y2 = r.bbox
            col = BOX_COLOR if r.kind == 'box' else LINE_COLOR
            if r.kind == 'box':
                nb += 1
            else:
                nl += 1
            cv2.rectangle(vis, (x1, y1), (x2, y2), col, 4)
            cv2.putText(vis, str(i), (x1 + 6, max(30, y1 + 34)),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.1, col, 3, cv2.LINE_AA)

        band = np.full((46, w, 3), 255, np.uint8)
        cv2.putText(band, 'p%s  box=%d  line=%d' % (page, nb, nl), (10, 33),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2, cv2.LINE_AA)
        vis = np.vstack([band, vis])

        cv2.imencode('.jpg', vis, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tofile(
            os.path.join(out, 'p%s_検出.jpg' % page))

        rows.append((page, nb, nl))
        thumbs.append((nb + nl,
                       cv2.resize(vis, (240, int(240 * vis.shape[0] / vis.shape[1])))))

    if not thumbs:
        print('画像が1枚もありません: %s' % src)
        return

    COLS = 8
    tw = 240
    th = max(t[1].shape[0] for t in thumbs)
    nrows = (len(thumbs) + COLS - 1) // COLS
    sheet = np.full((nrows * (th + 8) + 8, COLS * (tw + 8) + 8, 3), 230, np.uint8)
    for i, (n, t) in enumerate(thumbs):
        r, c = divmod(i, COLS)
        y, x = 8 + r * (th + 8), 8 + c * (tw + 8)
        sheet[y:y + t.shape[0], x:x + tw] = t
        if n > 0:
            cv2.rectangle(sheet, (x - 3, y - 3), (x + tw + 2, y + t.shape[0] + 2),
                          BOX_COLOR, 3)
    cv2.imencode('.jpg', sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])[1].tofile(
        os.path.join(out, '_一覧.jpg'))

    hit = [r for r in rows if r[1] + r[2] > 0]
    print('総ページ %d / マークあり %d ページ / 囲み %d / 傍線 %d'
          % (len(rows), len(hit), sum(r[1] for r in rows), sum(r[2] for r in rows)))
    print('書き出し: %s' % out)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'jpg'))
