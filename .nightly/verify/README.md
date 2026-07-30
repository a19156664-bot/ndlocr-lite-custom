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
python .nightly/verify/inject40.py <mode>     # 欠陥を入れる
python -m pytest tests/ -q                    # 落ちることを確認
python .nightly/verify/inject40.py restore    # 元に戻す

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
| `inject*.py` | 意図的に欠陥を入れ、テストが検出できるかを証明する |
| `probe*.py` | 原因切り分けのための一時的な改変（診断専用） |
| `diag40.py` | 不具合の再現スクリプト（Task 40 の保存拒否） |
| `watch.sh` | Jules セッションが終端状態に達するまでポーリングする |

## 主要スクリプトの対象

| ファイル | 検証対象 |
|---|---|
| `verify39.py` / `verify39b.py` | Task 39 永続化（計22項目） |
| `inject39b.py` | 永続化の結線6箇所・復元・採番 |
| `diag40.py` | 保存拒否がステータス欄だけで見えない問題の再現 |
| `inject40.py` | OCRデータ無しダイアログ・上書き・OCR待ち予約 |
| `inject41.py` | Pan カーソルの値・SELECT ドラッグ・ドラッグ終了 |
| `probe39c.py` | Task 39c が壊した app.py の切り分け |
