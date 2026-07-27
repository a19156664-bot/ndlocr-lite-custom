#!/usr/bin/env python3
"""
Jules Session Automator for Loop Engineering System.
Automatically submits tasks and initiates sessions with Jules API / GitHub triggers.
"""

import sys
import os
import json
import yaml
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from github_helper import run_gh_command, create_issue

STATE_FILE = Path(".nightly/state.yml")

def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def trigger_jules_session(title: str, prompt_body: str) -> bool:
    """
    Submits task to Jules via GitHub API / Issue bot trigger AND Jules CLI.
    """
    print(f"[JulesSession] Creating or updating Issue for: {title}...")
    
    # 1. Create Issue via GitHub API (clean env)
    issue_url = create_issue(title, prompt_body)
    issue_num = None
    if issue_url:
        print(f"[JulesSession] Issue created successfully: {issue_url}")
        issue_num = issue_url.split("/")[-1]
    
    # 2. Trigger via Jules CLI (jules new --repo owner/repo)
    cli_args = [
        "jules", "new",
        "--repo", "a19156664-bot/ndlocr-lite-custom",
        f"{title}\n\n{prompt_body}"
    ]
    print(f"[JulesSession] Triggering Jules CLI session via subprocess...")
    try:
        env = os.environ.copy()
        env.pop("GITHUB_TOKEN", None)
        res = subprocess.run(cli_args, capture_output=True, text=True, check=True, env=env, shell=True)
        print(f"[JulesSession] Jules CLI stdout: {res.stdout}")
    except Exception as e:
        print(f"[JulesSession] Jules CLI error: {e}")

    # 3. Update state.yml
    state = load_state()
    state["current_task"] = f"Task 08 ({title})"
    state["loop_status"] = "running"
    if issue_num:
        state["issue_number"] = issue_num
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(state, f, allow_unicode=True)

    print(f"[JulesSession] State updated. Jules session active for: {title}.")
    return True

if __name__ == "__main__":
    prompt = """Task 08: [NEW] タスクの優先度（Priority: High, Medium, Low）設定と表示・フィルタリング機能

## 目的
TODOタスクごとに優先度（high, medium, low）を設定・保存可能にし、UIでのラベル/バッジ表示および優先度別の操作を可能にする。

## 完了条件 (DoD)
- `js/store.js` の `addTodo` および `updateTodo` にて優先度（`priority`: `'high'`, `'medium'`, `'low'`。デフォルトは `'medium'`）を保存可能にし、`updatePriority(id, priority)` を実装すること
- `tests/store.test.js` に `updatePriority()` および優先度保存の単体テスト（Test 7）を追加し、既存テスト（Test 1〜6）を含め全7件が正常パスすること
- `index.html` および `js/app.js` に優先度選択UIおよびバッジ表示・切替機能を追加すること

## 変更許可ファイル (スコープ)
- index.html
- style.css
- js/store.js
- js/app.js
- tests/store.test.js

## 変更禁止パス
- .nightly/
- .github/
- AGENTS.md
- task_template.md"""

    print("[JulesSession] Executing automatic session registration for Task 08...")
    success = trigger_jules_session("[Task-08] タスクの優先度設定と表示機能の実装", prompt)
    if success:
        print("[JulesSession] Automatic session registration COMPLETE for Task 08.")

