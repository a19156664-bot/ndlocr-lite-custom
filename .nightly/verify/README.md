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
