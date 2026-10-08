# -*- coding: utf-8 -*-
"""Antigravity の代わりに Sonnet（相棒）へ渡す材料を作る（10-08 承認者「Antigravity 側の作業を Sonnet 5.5 を代役に」）。
work\\proofread\\<号>号_校正の入力.csv（make_proof_input.py が作る）の、指定の頁の枠ごとに、枠の画像と問いを書く。
読むだけ。書く先は work\\proofread\\sonnet\\<号>_<段>_<頁>\\ （git の外）。

使い方: .venv\\Scripts\\python.exe .nightly\\verify\\make_sonnet_set.py <号> <orient|proof> <頁の始め> <頁の終わり>
  orient … ② 読み方の点検（縦で読み直す／拾い落とし／そのまま）。枠の画像は長い辺 1000px まで縮める
  proof  … ④ 誤字の指摘。枠の画像は長い辺 2000px まで（字を見比べるため）。2000px を超える枠は縦に 2 つに割る
"""
import os, sys, csv
sys.stdout.reconfigure(encoding="utf-8")
from PIL import Image
BASE = r"C:\Users\user\ndlocr-lite-custom"

def main():
    num, stage, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    assert stage in ("orient", "proof")
    src = os.path.join(BASE, "work", "proofread", f"{num}号_校正の入力.csv")
    # 5 つ目の引数（頁,枠 の CSV）があれば、その枠だけにする（③で書いた枠の④など）
    only = None
    if len(sys.argv) > 5:
        only = {(int(r["頁"]), str(r["枠"])) for r in csv.DictReader(open(sys.argv[5], encoding="utf-8-sig", newline=""))}
    tag = "" if only is None else "_" + os.path.splitext(os.path.basename(sys.argv[5]))[0]
    out = os.path.join(BASE, "work", "proofread", "sonnet", f"{num}_{stage}_p{a:03d}-{b:03d}{tag}")
    os.makedirs(out, exist_ok=True)
    rows = [r for r in csv.DictReader(open(src, encoding="utf-8-sig", newline="")) if a <= int(r["頁"]) <= b
            and (only is None or (int(r["頁"]), str(r["枠"])) in only)]
    imgs, qs = {}, []
    cap = 1000 if stage == "orient" else 2000
    for r in rows:
        pg, fr = int(r["頁"]), r["枠"]
        if pg not in imgs:
            imgs[pg] = Image.open(os.path.join(BASE, "work", "cache_images", f"{num}号", f"国際寫眞新聞_{num}号_p{pg:04d}.png")).convert("RGB")
        x1, y1, x2, y2 = (int(r[k]) for k in ("x1", "y1", "x2", "y2"))
        c = imgs[pg].crop((max(0, x1 - 10), max(0, y1 - 10), x2 + 10, y2 + 10))
        parts = [c]
        if stage == "proof" and max(c.size) > cap:
            if c.size[1] >= c.size[0]:
                h = c.size[1] // 2
                parts = [c.crop((0, 0, c.size[0], h + 20)), c.crop((0, h - 20, c.size[0], c.size[1]))]
            else:
                w = c.size[0] // 2
                parts = [c.crop((w - 20, 0, c.size[0], c.size[1])), c.crop((0, 0, w + 20, c.size[1]))]  # 右から読むので右半分が先
        names = []
        for k, p in enumerate(parts):
            f = min(1.0, cap / max(p.size))
            if f < 1: p = p.resize((max(1, int(p.size[0] * f)), max(1, int(p.size[1] * f))), Image.LANCZOS)
            n = f"p{pg:03d}_R{fr}{'' if len(parts) == 1 else '_' + 'ab'[k]}.png"
            p.save(os.path.join(out, n)); names.append(n)
        text = r["文字"]
        qs.append({"頁": pg, "枠": fr, "下書きの字数": len("".join(text.split())), "画像": " ".join(names), "下書き": text})
    if not qs:
        print("この頁の範囲に枠が無い"); return 1
    with open(os.path.join(out, "questions.csv"), "w", encoding="utf-8-sig", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=list(qs[0].keys())); w.writeheader(); w.writerows(qs)
    print(f"{out}  枠 {len(qs)}・画像 {sum(len(q['画像'].split()) for q in qs)}・頁 {len({q['頁'] for q in qs})}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
