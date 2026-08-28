# -*- coding: utf-8 -*-
"""手描きマークの色あいを数える。**3色目が使われていないかを検知する道具**。

    <venv>\\Scripts\\python.exe .nightly\\verify\\hue_scan.py [画像フォルダ]

AGENTS.md §8.1 は、承認者のご判断としてマークの色の意味を定めている。

    水色 H=90 / S=157-159 / V=233-238  -> OCR させたい範囲
    橙色 H=25 / S=159     / V=236-239  -> そのページは広告

そして「**3色目のマーカーをお使いになったとき、この判断は無効になる**」と
書いてある。この道具は、その条件が起きたかどうかを測る。

新しい素材を受け取ったら、まずこれを走らせること。水色と橙色の帯だけに
画素が集まっていれば、既存の判断がそのまま使える。第三の帯が立ち上がって
いたら、承認者に意味を伺うこと。**勝手に解釈しない。**

判定の条件（S>=120 かつ V>=180）は手描きの条件のみで、色あいは問わない。
紙・活字は彩度 2-5、題字の印刷インクは彩度 68・明度 88 で、どちらも落ちる。

2026-08-27 に 52枚で使用。橙-黄 50,437画素 / 水色-青 1,036,874画素。
他の帯は 1,000画素に届かなかった。
"""
import os
import sys
import glob

import cv2
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BANDS = [
    ('赤   (H 0-9,171-179)', None),
    ('橙-黄 (H 10-35)  = 広告', (10, 36)),
    ('黄緑-緑 (H 36-74)', (36, 75)),
    ('水色-青 (H 75-110) = 範囲', (75, 111)),
    ('紫-赤紫 (H 111-170)', (111, 171)),
]

KNOWN = {'橙-黄 (H 10-35)  = 広告', '水色-青 (H 75-110) = 範囲'}


def main(src):
    total = np.zeros(180, dtype=np.int64)
    per_page = []
    files = sorted(glob.glob(os.path.join(src, '*.jpg')))
    if not files:
        print('画像が1枚もありません: %s' % src)
        return

    for p in files:
        page = os.path.basename(p).split('_')[-1].replace('.jpg', '')
        img = cv2.imdecode(np.fromfile(p, np.uint8), cv2.IMREAD_COLOR)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        strong = (hsv[:, :, 1] >= 120) & (hsv[:, :, 2] >= 180)
        hs = hsv[:, :, 0][strong]
        hist = np.bincount(hs, minlength=180) if hs.size else np.zeros(180, np.int64)
        total += hist
        per_page.append((page, hist))

    print('画像 %d 枚 / 手描きの条件（S>=120 かつ V>=180）に合う画素の色あい分布' % len(files))
    unknown = []
    for name, rng in BANDS:
        if rng is None:
            v = int(total[0:10].sum() + total[171:180].sum())
        else:
            v = int(total[rng[0]:rng[1]].sum())
        flag = ''
        if v >= 1000 and name not in KNOWN:
            flag = '   <-- ★3色目の疑い。承認者に意味を伺うこと'
            unknown.append(name)
        print('  %-26s %9d 画素%s' % (name, v, flag))

    print()
    print('=== 橙（広告）が 2000 画素以上あるページ ===')
    ad = [(pg, int(h[10:36].sum())) for pg, h in per_page if int(h[10:36].sum()) >= 2000]
    for pg, n in ad:
        print('  p%s  %7d 画素' % (pg, n))
    print('  該当 %d ページ' % len(ad))

    print()
    if unknown:
        print('★ 既知でない色が見つかった: %s' % '、'.join(unknown))
        print('  AGENTS.md §8.1 の判断は、この場合 無効になる。承認者に伺うこと。')
    else:
        print('既知の2色のみ。AGENTS.md §8.1 の判断はそのまま使える。')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'jpg'))
