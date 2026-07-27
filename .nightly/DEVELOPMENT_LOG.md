# 📜 ループエンジニアリング 業務日報 兼 開発進捗記録簿

**プロジェクト名**: NDLOCR-Lite カスタマイズ OCR アプリ（範囲指定OCR）
**運用モード**: パターンB（パイプライン一括検収・まとめ承認モデル）
**最新更新日時**: 2026-07-27
**進捗ステータス**: 🟡 環境構築完了・発注準備中

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
