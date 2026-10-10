# -*- coding: utf-8 -*-
"""号ごとの進捗管理表（work\\進捗管理表.html）を、ファイルの有無と時刻から作る（10-10 承認者のご依頼: 作業漏れの防止と担当の把握）。
工程の状態は機械で測る。測れない所（人の確認の完了・監査の判定済み など）は .nightly\\進捗_手で付ける.csv の行で上書きする。

使い方: .venv\\Scripts\\python.exe .nightly\\verify\\progress_table.py
"""
import sys, os, re, csv, glob, html
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8")
BASE = r"C:\Users\user\ndlocr-lite-custom"
W = os.path.join(BASE, "work")
PR = os.path.join(W, "proofread")
LEDGER = os.path.join(BASE, ".nightly", "進捗_手で付ける.csv")
OUT = os.path.join(W, "進捗管理表.html")
STAGES = [  # (鍵, 表示, 担当)
    ("入荷", "入荷", "承認者"),
    ("全体OCR", "① 全体OCR", "機械"),
    ("一括処理", "① 枠ごとのOCR", "機械"),
    ("AI点検", "②④ 読み方・誤字の指摘", "Sonnet（夜）"),
    ("判定", "⑤ 画像で判定・置き換え", "指揮官"),
    ("監査", "監査", "Antigravity（日中）"),
    ("人の確認", "⑥ 人の確認", "承認者"),
    ("Excel", "⑦ Excel", "指揮官"),
    ("納品", "納品", "承認者"),
]
DONE, PART, WAIT, TODO, NA, OPEN = "済", "途中", "待ち", "未", "—", "未定"


def t(p):
    return datetime.fromtimestamp(os.path.getmtime(p))


def rows(p):
    with open(p, encoding="utf-8-sig") as fp:
        return sum(1 for _ in csv.DictReader(fp))


def pages_of(pdf):
    try:
        import pypdfium2
        return len(pypdfium2.PdfDocument(pdf))
    except Exception:
        return None


def ledger():
    got = {}
    if os.path.exists(LEDGER):
        with open(LEDGER, encoding="utf-8-sig") as fp:
            for r in csv.DictReader(fp):
                if r.get("号") and r.get("工程") and r.get("状態"):
                    got[(r["号"].strip(), r["工程"].strip())] = r
    return got


def measure(n, led):
    s = {}
    pdf = os.path.join(W, f"国際寫眞新聞_{n}号.pdf")
    pg = pages_of(pdf)
    s["入荷"] = (DONE, f"{pg} 頁・{t(pdf):%m-%d}", "")
    js = os.path.join(W, "output", "01_raw_ocr", f"国際寫眞新聞_{n}号.json")
    s["全体OCR"] = (DONE, f"{t(js):%m-%d %H:%M}", "") if os.path.exists(js) else (TODO, "", "")
    cache = glob.glob(os.path.join(W, ".ndlocr_cache", f"国際寫眞新聞_{n}号_p*.work.json"))
    s["一括処理"] = (DONE, f"保存 {len(cache)} 頁", "") if cache else (TODO, "", "")
    checks = glob.glob(os.path.join(PR, f"{n}号_*指揮官の確認.csv"))
    plans = glob.glob(os.path.join(PR, f"{n}号_p*_校正案.csv"))
    if checks:
        s["AI点検"] = (DONE, f"確認の CSV {len(checks)} 本", "Sonnet")
    elif plans:
        s["AI点検"] = (DONE, f"校正案 {len(plans)} 頁", "Antigravity")
    else:
        s["AI点検"] = (TODO, "", "")
    hum = os.path.join(PR, f"{n}号_人へ回す.csv")
    if os.path.exists(hum):
        n_chk = sum(rows(p) for p in checks)
        s["判定"] = (DONE, f"判定 {n_chk} 行・人へ回す {rows(hum)} 行", "")
    elif checks:
        s["判定"] = (PART, f"確認の CSV {len(checks)} 本", "")
    else:
        s["判定"] = (TODO, "", "")
    aud = [p for d in glob.glob(os.path.join(PR, "監査_*")) for p in glob.glob(os.path.join(d, f"{n}号_p*_校正案.csv"))]
    if aud:
        k = sum(rows(p) for p in aud)  # 指摘の一覧.txt は号ごとの集計の行も「<号>号」で始まるので数えない（10-10 に 1 件ずつ多く数えた）
        s["監査"] = (WAIT, f"返却 {max(t(p) for p in aud):%m-%d}・指摘 {k} 件・判定待ち", "指揮官")
    else:
        s["監査"] = (OPEN, "頼むかは 142〜145号の結果で決める", "")
    if os.path.exists(hum):
        # 機械の書き込み（apply_fixes 等は書く直前に work\backup\<時刻>_… を作る）から 2 分以内の保存は、人の形跡に数えない（10-10 に誤って数えた）
        bk = []
        for d in glob.glob(os.path.join(W, "backup", "*_*_*")):
            m = re.match(r"(\d{8}_\d{6})_", os.path.basename(d))
            if m:
                bk.append(datetime.strptime(m.group(1), "%Y%m%d_%H%M%S").timestamp())
        machine = lambda ts: any(b <= ts <= b + 120 for b in bk)
        after = [p for p in cache if os.path.getmtime(p) > os.path.getmtime(hum) + 600 and not machine(os.path.getmtime(p))]
        if after:
            last = max(t(p) for p in after)
            s["人の確認"] = (PART, f"ビューアで保存 {len(after)} 頁（最終 {last:%m-%d %H:%M}）", "")
        else:
            s["人の確認"] = (TODO, "", "")
    else:
        s["人の確認"] = (TODO, "", "")
    xl = [p for p in glob.glob(os.path.join(W, "*.xlsx")) + glob.glob(os.path.join(W, "納品", "*", "*.xlsx")) if f"_{n}号" in os.path.basename(p)]
    s["Excel"] = (DONE, f"{max(t(p) for p in xl):%m-%d}", "") if xl else (TODO, "", "")
    dl = [p for p in glob.glob(os.path.join(W, "納品", "*", "*")) if f"_{n}号" in os.path.basename(p) and "ご納品" in os.path.basename(p)]
    s["納品"] = (DONE, f"{max(t(p) for p in dl):%m-%d}（{os.path.basename(os.path.dirname(dl[0]))}）", "") if dl else (TODO, "", "")
    for key, _, _ in STAGES:  # 手で付けた行が勝つ
        r = led.get((str(n), key))
        if r:
            s[key] = (r["状態"].strip(), " ".join(x for x in (r.get("日付", ""), r.get("メモ", "")) if x).strip(), r.get("誰", "").strip())
    if s["納品"][0] == DONE:  # 納品済みの号は、測れなかった前の工程を「—」にする
        for key, _, _ in STAGES:
            if s[key][0] in (TODO, PART, WAIT, OPEN):
                s[key] = (NA, "納品済みのため", s[key][2])
    return s


def main():
    led = ledger()
    nums = sorted(int(m.group(1)) for p in glob.glob(os.path.join(W, "国際寫眞新聞_*号.pdf"))
                  if (m := re.search(r"_(\d+)号\.pdf$", p)))
    now = datetime.now()
    color = {DONE: "ok", PART: "part", WAIT: "part", TODO: "todo", NA: "na", OPEN: "na"}
    head = "".join(f"<th>{html.escape(lbl)}<br><span class='who'>{html.escape(who)}</span></th>" for _, lbl, who in STAGES)
    body = []
    for n in nums:
        s = measure(n, led)
        # 次の一手: 判定待ちの監査（脇の工程）と、順番の工程で最初に残っている 1 つ
        nxt = [(lbl, s[key][2] or who) for key, lbl, who in STAGES if key == "監査" and s[key][0] in (WAIT, PART)]
        nxt += [(lbl, s[key][2] or who) for key, lbl, who in STAGES if key != "監査" and s[key][0] not in (DONE, NA, OPEN)][:1]
        cells = []
        for key, _, who in STAGES:
            st, det, by = s[key]
            by_txt = f"<div class='who'>{html.escape(by)}</div>" if by and by not in who else ""
            cells.append(f"<td class='{color.get(st, 'part')}'><b>{html.escape(st)}</b>"
                         f"<div class='det'>{html.escape(det)}</div>{by_txt}</td>")
        nx = "".join(f"<div>{html.escape(l)}<div class='who'>{html.escape(w)}</div></div>" for l, w in nxt) if nxt else "完了"
        body.append(f"<tr><th>{n}号</th>{''.join(cells)}<td class='next'>{nx}</td></tr>")
        print(f"{n}号: " + " / ".join(f"{k}={s[k][0]}" for k, _, _ in STAGES) + " → 次: " + ("・".join(f"{l}（{w}）" for l, w in nxt) if nxt else "完了"))
    page = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>進捗管理表</title>
<style>
:root{{--bg:#fff;--fg:#1f2328;--mut:#656d76;--line:#d0d7de;--head:#f6f8fa;--ok:#dafbe1;--part:#fff8c5;--todo:#fff;--na:#f6f8fa}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0d1117;--fg:#e6edf3;--mut:#9198a1;--line:#30363d;--head:#161b22;--ok:#12361f;--part:#3b2e00;--todo:#0d1117;--na:#161b22}}}}
body{{background:var(--bg);color:var(--fg);font:14px/1.5 "Yu Gothic UI","Meiryo",sans-serif;margin:0;padding:16px}}
h1{{font-size:20px;margin:0 0 4px}}p.note{{color:var(--mut);font-size:13px;margin:4px 0}}
.wrap{{overflow-x:auto}}table{{border-collapse:collapse;min-width:1100px}}
th,td{{border:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left}}
thead th{{background:var(--head);font-size:13px}}tbody th{{background:var(--head);white-space:nowrap}}
td.ok{{background:var(--ok)}}td.part{{background:var(--part)}}td.todo{{background:var(--todo)}}td.na{{background:var(--na);color:var(--mut)}}
td.next{{font-weight:bold}}.who{{color:var(--mut);font-size:12px;font-weight:normal}}.det{{font-size:12px}}
</style></head><body>
<h1>進捗管理表（号ごと）</h1>
<p class="note">測った時刻 {now:%Y-%m-%d %H:%M}。ファイルの有無と時刻から機械で測っています。色: 緑＝済／黄＝途中・待ち／白＝未／灰＝この号では不要・未定。見出しの下は担当。「次の一手」は順番で最初に残っている工程と、判定待ちの監査。</p>
<div class="wrap"><table><thead><tr><th>号</th>{head}<th>次の一手</th></tr></thead><tbody>
{''.join(body)}
</tbody></table></div>
<p class="note">機械で測れない所（⑥ 人の確認の完了・監査の判定済み など）は {html.escape(LEDGER)} の行で上書きしています（列: 号,工程,状態,日付,誰,メモ）。</p>
<p class="note">⑥ の「途中」は、人へ回す一覧を作った 10 分後より後に、ビューアで保存された頁があることを表します。誰が保存したかまでは測っていません。</p>
</body></html>
"""
    with open(OUT, "w", encoding="utf-8") as fp:
        fp.write(page)
    print(f"{len(nums)} 号 → {OUT}")
    if not nums:
        print("号が 0 件（無効）"); sys.exit(1)


main()
