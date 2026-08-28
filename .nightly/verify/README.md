# 指揮官の検収ツール（.nightly/verify/）

Jules の納品物を検収するために指揮官（AI指揮官）が使う道具置き場です。
**アプリケーション機能コードでもテストでもありません。** pytest は
`test_*.py` しか収集しないため、ここのファイルは収集対象外です。

これらは元々セッション固有の一時ディレクトリに置いていたため、セッションを
またぐと失われていました。再作成のコストを避けるため 2026-07-30 に保全した
ものです。

## 使い方

すべて作業ツリー `C:\Users\user\ndlocr-work` を対象にハードコードして
います。パスが違う場合は先頭の定数を書き換えてください。

```bash
# 実ウィジェット検証（ヘッドレスで本物のコントロールを駆動する）
/c/Users/user/ndlocr-lite-custom/.venv/Scripts/python.exe .nightly/verify/verify39.py

# 欠陥再注入（テストが本当に落ちるかの証明）
#   台帳はリポジトリの外にある。末尾「欠陥再注入の台帳」を参照
python C:\Users\user\ndlocr_sabotage\inject40.py <mode>     # 欠陥を入れる
python -m pytest tests/ -q                                  # 落ちることを確認
python C:\Users\user\ndlocr_sabotage\inject40.py restore    # 元に戻す

# Jules セッションの完了待ち
#   watch.conf の1行目にセッションID、2行目にポーリング間隔（秒）
bash .nightly/verify/watch.sh
```

`inject*.py` は必ず `restore` で戻すこと。`*.injbak` が残っていたら
戻し忘れです。

## 種別

| 接頭辞 | 役割 |
|---|---|
| `verify*.py` | 実ウィジェットを駆動して DoD を1項目ずつ確認する |
| `probe*.py` | 原因切り分けのための一時的な改変（診断専用） |
| `diag40.py` | 不具合の再現スクリプト（Task 40 の保存拒否） |
| `watch.sh` | Jules セッションが終端状態に達するまでポーリングする |

## 主要スクリプトの対象

| ファイル | 検証対象 |
|---|---|
| `verify39.py` / `verify39b.py` | Task 39 永続化（計22項目） |
| `diag40.py` | 保存拒否がステータス欄だけで見えない問題の再現 |
| `probe39c.py` | Task 39c が壊した app.py の切り分け |

---

## 欠陥再注入の台帳（このリポジトリには置かない）

    C:\Users\user\ndlocr_sabotage\

`inject*.py` 8本は 2026-08-27 にここへ移した。**リポジトリに置くと Jules が
clone して読める**ためである。どこに欠陥を注入して検査するかを実装者に先に
見せると、破壊試験がその点だけを避けた実装を招く。

台帳は `C:\Users\user\ndlocr-work` を対象に絶対パスで書かれているため、
リポジトリの外に置いても動作は変わらない。

---

## マーク検出と OCR 精度の道具（2026-08-28 保全）

一時ディレクトリで書いて失うことを繰り返さないため、ここに置いた（知見15）。
いずれも引数なしで走らせると `jpg/` を見る。第1引数で別のフォルダを指定できる。

| 道具 | 何をするか |
|---|---|
| `hue_scan.py` | 手描きの色あいを数える。**3色目が使われていないかを検知する** |
| `marks_overlay.py` | マーク検出の結果を、承認者が目で見られる画像にする |
| `extract_regions.py` | 範囲ごとの本文を、**アプリと同じ経路**で抜き出す |

```powershell
.\.venv\Scripts\python.exe .nightly\verify\hue_scan.py
.\.venv\Scripts\python.exe .nightly\verify\marks_overlay.py
.\.venv\Scripts\python.exe .nightly\verify\extract_regions.py
```

**`extract_regions.py` は先に全面 OCR が要る。**

```powershell
mkdir jpg\_ocr結果
.\.venv\Scripts\python.exe src\ocr.py --sourcedir jpg --output jpg\_ocr結果
```

出力先が存在しないと `Output Directory is not found.` と出て、**何も作らずに終わる**。

**新しい素材を受け取ったら、まず `hue_scan.py` を走らせること。**
AGENTS.md §8.1 の色の判断は「3色目が使われたら無効」と定めてある。
第三の帯が立ち上がっていたら、意味を勝手に解釈せず承認者に伺う。

2026-08-28 の実測（52枚）: 囲み68・傍線50・範囲118個・抽出7,040字・横書き80行・広告9ページ。
