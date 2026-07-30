# 📜 ループエンジニアリング 業務日報 兼 開発進捗記録簿

**プロジェクト名**: NDLOCR-Lite カスタマイズ OCR アプリ（範囲指定OCR）
**運用モード**: パターンB（パイプライン一括検収・まとめ承認モデル）
**最新更新日時**: 2026-07-30
**進捗ステータス**: 🟢 実用段階（master 6d079b6・230 tests passed）

---

## 📊 1. タスク進捗サマリー一覧

| タスクID | 機能・タスク概要 | 担当 | 検証結果 | 統合状態 | 備考 |
|---|---|---|---|---|---|
| **Task 01** | custom_gui 雛形とテスト基盤 | Jules | Pending | 未統合 | ブロック1 |
| **Task 02** | OCRブリッジ（結果の構造化） | Jules | Pending | 未統合 | ブロック1 |
| **Task 03** | 画像ビューア（表示・座標変換） | Jules | Pending | 未統合 | ブロック1 |
| **Task 04** | 矩形ドラッグ選択UI | Jules | Pending | 未統合 | ブロック2 |
| **Task 05** | 範囲フィルタ（bbox絞り込み） | Jules | Pending | 未統合 | ブロック2 |
| **Task 06** | 範囲OCR結果の表示・ハイライト | Jules | Pending | 未統合 | ブロック2 |
| **Task 07-09** | 複数矩形・一覧・出力 | Jules | Pending | 未統合 | ブロック3（DoD未確定） |
| **Task 10-12** | PDF・ページ送り・一括処理 | Jules | Pending | 未統合 | ブロック4（DoD未確定） |

---

## 📝 2. 本日の業務日報（2026-07-27）

### 📌 実施業務内容
1. NDLOCR-Lite のライセンス調査（一次情報で確認）— CC BY 4.0、ソース・学習スクリプト共に公開、依存ライブラリに制約ライセンスなし
2. 要件確定（3問の認識統一）— ①手動矩形選択方式 ②C方式(fork+追加モジュール) ③第1弾ゴールは実用アプリ一式
3. `ndl-lab/ndlocr-lite` を `a19156664-bot/ndlocr-lite-custom` へ fork、`C:\Users\user\ndlocr-lite-custom` へ clone
4. `upstream` remote 登録および **push URL の無効化**（NDLリポジトリへの誤 push 防止）
5. スターターキット（AGENTS.md / CLAUDE.md / task_template.md / .agents / .nightly / scripts）を配置
6. AGENTS.md をプロジェクト固有値へ更新（リポジトリ名・`master`ブランチ・pytest・Jules CLI実パス）
7. Python 仮想環境構築と依存インストール（Python 3.13.5 / 全32パッケージ成功）
8. **OCR実機検証に成功**（`resource/digidepo_2531162_0024.jpg` を6.0秒で処理、txt/json/xml 出力）
9. `.nightly/ROADMAP.md` に4ブロック12タスクを分解・登録

---

## 🧠 3. 課題と獲得した知見 (Lessons Learned & Gotchas)

* **知見1: OCR結果JSONに行単位の `boundingBox` が含まれる。** → 範囲指定OCRは「全面OCR → 矩形内フィルタ」で実現可能。部分画像を切り出して再推論する必要がなく、実装が大幅に簡素化される。ROADMAPの設計前提に反映済み。
* **知見2: fork のデフォルトブランチは `main` ではなく `master`。** 憲法の保護対象ブランチ名を `master` に修正済み。以後 `git push origin main` は存在しないブランチへの操作となるため注意。
* **知見3: Jules CLI の実体は npm 経由の `C:\Users\user\AppData\Roaming\npm\jules.ps1`。** 旧AGENTS.mdに記載の `%TEMP%\jules_tmp\jules.exe` は**存在しない**。§7.3 を実環境に合わせて修正済み。
* **知見4: gh CLI はインストール済み・認証済み**（`a19156664-bot`、スコープ `gist, read:org, repo`）。ただし **`workflow` スコープがない**ため、`.github/workflows/` を変更する push は失敗する見込み。CI設定を触る場合は再認証が必要。
* **知見5: モデルファイル（.onnx 計約150MB）は Git LFS ではなく実体でコミットされている。** clone だけで動作する反面、リポジトリが重い。
* **知見6: 上流の `.gitignore` は `.venv` `__pycache__` を既に除外済み。** 失敗モードカタログ A-3（不要ファイル混入）の予防が上流側で完了している。
* **知見7: Python 3.13.5 で全依存パッケージがインストール可能。** `requirements.txt` は 3.11以上に onnxruntime 1.26.0 を割り当てており、3.13でも問題なく動作した。

---

# 📜 業務日報（2026-07-30）— 永続化と保存不具合の解消

**master**: `6d079b6`
**テスト**: **230 passed**（前回セッション開始時 191 → 230、+39）
**進捗ステータス**: 🟢 実用段階。中断・再開が可能になった

## 📊 本セッションのマージ履歴

| コミット | 内容 | テスト |
|---|---|---|
| `50122e7` | Task 33b 矩形横のインラインエディタ | |
| `3a22872` | Task 35 + 35b 保存アイコン2種・保存先ダイアログ廃止・改行数表示 | |
| `b4907f8` | Task 36 + 36b 広告 / 表紙 ボタン | |
| `8cbe6b4` | Task 37 右クリックで Pan 切替・カーソルでモード可視化 | |
| `7b1b2bb` | Task 38 Ctrl+S 保存・Enter 確定・次ページ確認 | 184 → 191 |
| `07bec90` | chore `resource/*.csv` `*.txt` を .gitignore | 191 |
| `ed96acf` | **Task 39 系** 矩形・修正文字・マークの永続化 | 191 → 215 |
| `ed96acf` | **Task 40** 保存の拒否が見えない不具合の修正 | 215 → 227 |
| `6d079b6` | **Task 41** Pan カーソルの Windows 対応 | 227 → 230 |

## 📌 実施業務内容

### Task 39 / 39b / 39c — 作業状態の永続化（3回の差し戻しを要した）

`custom_gui/work_state.py`（新規・純粋）を追加し、矩形・F2/インライン修正・
広告/表紙マークを `.ndlocr_cache/<画像名>.work.json` へ**操作のたびに原子的に
保存**、起動時に復元する。`ocr_cache.py` と同じ方式（tempfile + os.replace、
schema、size/mtime による陳腐化検知）を踏襲。PDF ページは PDF 本体の隣に
`<PDF名>_p0004.work.json` として保存する（レンダリング先の一時フォルダは
終了時に消えるため）。

- Task 39: `Failed`。import 漏れ・復元処理なし・結線3/6箇所。実機検証 7項目中7項目 FAIL
- Task 39b: 機能は成立（22項目通過）。ただし範囲外のガード1行で既存13件が破損
- Task 39c: テストのハンドラ経由化は成功。ただし `app.py` を構文エラーにした
- 最終的にユーザー承認のもと、指揮官が `app.py` をガード2行の削除のみに差し戻した

### Task 40 — 「このページ保存・Ctrl+S が効かない」の修正

ユーザー報告。真因は**拒否がステータス欄の英字表示だけで見えないこと**。
ユーザー自身が「OCR（select）を行っていない場合」と特定した。

`_start_export("current")` の結末を4通りに整理した。

| 状態 | 変更後 |
|---|---|
| 矩形もマークも無い | モーダル「OCRデータがございません。」 |
| 矩形あり・OCR未完了 | `_pending_export` に予約し、OCR完了後に自動保存 |
| 矩形あり・OCRエラー | ダイアログでエラー内容を表示 |
| 上記以外 | 確認なしで即上書き |

`_show_overwrite_dialog` はメソッドごと削除。

### Task 41 — Pan のカーソルが Windows で手にならない

`ft.MouseCursor.GRAB` / `GRABBING` は **Flutter の Windows embedder に
マッピングが無く、既定の矢印にフォールバックする**（flutter/flutter #99323、
P2、2026年7月時点で Open）。`CLICK`（IDC_HAND 指差しの手）と
`ALL_SCROLL`（IDC_SIZEALL 四方向矢印）に差し替えた。

### その他

- `.nightly/verify/` を新設し、指揮官の検収ツール26本を保全（従来はセッション固有の一時ディレクトリにあり、セッションをまたぐと失われていた）

---

## 🧠 課題と獲得した知見（2026-07-30）

* **知見8: `except Exception: pass` は import 漏れを隠蔽する。**
  Task 39 は `work_state` を import せずに `work_state.save_work_state()` を
  呼び、その `NameError` を自分で書いた `except Exception: pass` が飲み込んだ。
  **ユーザーには保存されたように見えて、ディスクには何も書かれていない。**
  指示書で「書き込み失敗は握り潰せ」と書いたことが蓋になった。
  → 以後、握り潰しは **`except (OSError, TypeError, ValueError)` のように
  対象を限定**させ、プログラムの誤り（NameError / AttributeError /
  ImportError）は落ちるようにする。「NameError が伝播すること」を
  `pytest.raises` で検証するテストを必須にした。

* **知見9: 「メソッドが呼ばれたこと」を検証するテストは結線漏れを検出できない。**
  Task 39b のテスト11件はすべて `_rects.append` と `_persist_work_state()` の
  直接呼び出しでハンドラを迂回しており、6種の欠陥注入のうち**4種が素通り**した。
  → **`os.path.exists` でファイルの実在を確認**させ、`_on_pan_end` /
  `delete_rect` / `btn_mark_ad.on_click` / `_switch_image` といった
  **実ハンドラを発火**させることを指示書で個別に指定する。到達方法（既存の
  `test_edit_enter.py` / `test_pan.py` の手法を流用せよ）まで書くと成功率が上がる。

* **知見10: flet の enum に値が存在することは、その値が動作することを意味しない。**
  Task 37 で `ft.MouseCursor.GRAB` の存在だけを確認し、プラットフォーム対応を
  検証しなかった。Windows には開いた手・握った手のカーソルが**そもそも存在
  しない**。Win32 の手は `IDC_HAND`（指差し）だけ。
  → 以後、プラットフォーム依存の値は **Flutter 側の実装状況まで確認**する。
  設定しても例外が出ずアサーションも通る値は機能テストで検出できないため、
  `tests/test_flet_constants.py` にガードを追加した。

* **知見11: Jules は「2行削除せよ」に3回失敗し、4行削除して構文エラーにした。**
  消えたのは `with self.selections_lock:`（Task 30c の重大修正）と
  `if hasattr(self, 'mark_label'):`（Task 36 のガード）。
  → 削除系の指示は**削除対象の行を完全に引用**し、隣接する保護対象の行を
  名指しで「絶対に消すな」と書く。それでも失敗し得るため、`ast.parse` を
  検収の最初に回す。

* **知見12: Jules は指示書ファイル自身を削除する。**
  Task 39b・39c が `.nightly/prompts/taskXXb_prompt.txt` を削除した。
  → 指示書の冒頭に「DO NOT DELETE THIS FILE」を書き、`.nightly/` への変更を
  全面禁止した。検収時は必ず `ls .nightly/prompts/taskXX_prompt.txt` で確認する。

* **知見13: 作業用ファイルの残置は常態。** Task 35 が20個、36 が16個、39 が10個、
  39b が3個、39c が4個。39c の `test_diff.py` `test_tmp.py` 等は
  **`test_` 始まりでリポジトリ直下に置かれるため pytest が収集してしまう**。
  → 指示書で実名を列挙し、「スクラッチはシステムの一時ディレクトリへ。
  `test_*.py` の名前を絶対に付けるな」と明記した。Task 40 / 41 では0個になった。

* **知見14: 提出前の `pytest --collect-only` は必須。** Task 39 の
  `test_persistence.py` は22行目が `IndentationError` で、**収集段階で
  スイート全体が停止**していた。実機検証7項目が丸ごと未実施のまま「納品」された。

* **知見15: 検収ツールを一時ディレクトリに置くと失われる。**
  `verify*.py` は毎回作り直していた。`.nightly/verify/` に移し、README で
  使い方を残した。

* **知見16: 上書き確認に autofocus を付けないという判断が、キーボード操作の
  行き止まりを作った。** Task 38 で「Enter 連打で未確認のファイルを潰す事故を
  防ぐ」ため意図的に外したが、**2回目以降の保存は必ず上書き確認を通る**ため
  `Ctrl+S` → `Enter` が毎回死んだ。広告/表紙ボタンが押した瞬間に
  `<画像名>.txt` を作ることも効いていた。
  → 安全側に倒す判断は、**その状態が「例外」なのか「常態」なのか**を確認する。

* **知見17: 無効なテストは通算12件。** いずれも「検証対象そのものをモック
  または迂回で置き換える」パターン。欠陥再注入を全指示書で必須にしてから
  検出できるようになったが、**注入する欠陥の選び方**が重要。実際に出荷された
  欠陥と同じ形（結線漏れ・握り潰し）を注入すること。
