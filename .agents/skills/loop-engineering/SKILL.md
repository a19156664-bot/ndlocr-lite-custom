---
name: loop-engineering
description: JulesとAntigravityの連携によるフェーズ承認型自動ループエンジニアリングの指揮・検収・オーケストレーションスキル。
---

# ループエンジニアリング 指揮・オーケストレーションスキル

## 目的
本スキルは、指揮官AI（Antigravity）が実行部隊AI（Jules）に対して発注を行い、自律監視・自動検収・品質検証を経て成果物を `main` ブランチへ安全に統合する「パイプラインまとめ承認モデル」を実現するための標準指示書です。

## 運用プロトコル

### 1. 指揮官 (Antigravity) の原則
- アプリケーションのコード（JS/HTML/CSS等）を直接実装してはならない。
- 不具合が発生した際は、プログラムを直さずまずコマンド・ログ閲覧で徹底的に原因を特定する。
- 原因特定後、検証可能な DoD（完了条件）を定めた発注指示書を作成し、Jules へ発注する。

### 2. 発注直後の 30分タイマー（schedule）絶対起動プロトコル
- Jules CLI にてセッションを創出した直後、必ず例外なく `schedule` ツールを用いて以下をセットする：
  `DurationSeconds: 1800`
  `Prompt: 'Jules Task XX の成果物自動チェックタイマー (Session: <SESSION_ID>)'`

### 3. 検収プロトコル
- タイマー起動時または成果物作成時、`jules remote pull --session <SESSION_ID> --apply` を実行。
- 単体テスト `python -m pytest tests/ -v` を実行し、全件グリーンであることを確認。
- あわせて `git diff` による静的レビュー（テストの実質性・スコープ逸脱・クレジット表示の保全）を並置する。
- 成果物は使い捨て統合ブランチ `integration/task-<開始ID>-<終了ID>` に積載する。
- 人間に総括検収レポートを提出し、明示的承認 (`[WRITE-I]`) を受けてから `git push origin master` を実行する。
