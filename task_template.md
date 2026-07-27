# Jules 発注指示書 テンプレート (taskXX_prompt.txt)

Task XX: [NEW/FIX] <タスクタイトル>

1. Purpose & Background:
<実装する機能の背景・目的・問題意識を記載>

2. Definition of Done (DoD):
   - <完了条件1: 具体的な動作・ロジック>
   - <完了条件2: UIおよびレスポンス形式>
   - <完了条件3: 単体テスト全件グリーン>

3. Allowed Scope (Whitelist):
   - <変更を認めるファイルパス1>
   - <変更を認めるファイルパス2>

4. Prohibited Scope (Blacklist):
   - `.nightly/*`
   - `AGENTS.md`
   - Existing unit test deletions or alterations

5. Existing Unit Test Protection:
   - Do NOT delete, skip, or alter expectations of existing unit tests.
