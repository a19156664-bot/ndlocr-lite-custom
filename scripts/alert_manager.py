#!/usr/bin/env python3
"""
Alert Manager for Loop Engineering System.
Handles emergency stopping and alerts user via GitHub Issue when anomalies occur.
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, Any

from github_helper import create_issue

STATE_FILE = Path(".nightly/state.yml")

def trigger_alert(reason: str, details: str) -> None:
    """Transition state.yml to 'stopped' and raise [LOOP-ALERT] Issue."""
    print(f"\n🚨 [ALERT MANAGER] TRIPPED! Reason: {reason}", file=sys.stderr)
    
    # 1. Update state.yml
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = yaml.safe_load(f) or {}
        state["loop_status"] = "stopped"
        state["last_review"] = {
            "verdict": "STOPPED",
            "notes": f"Alert triggered: {reason} - {details}"
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            yaml.safe_dump(state, f, allow_unicode=True)
    
    # 2. Create Issue
    issue_title = f"[LOOP-ALERT] ループエンジニアリング自動停止: {reason}"
    issue_body = f"""## 🚨 自動停止アラート (Safety Tripped)

**停止理由**: {reason}

### 詳細
{details}

---
### 人間（オーナー）へのお願い
1. 状況を確認し、必要に応じてコードまたは指示書を修正してください。
2. 再開するには `.nightly/state.yml` の `loop_status` を `running` に戻し、`consecutive_failures` を `0` にリセットしてください。
"""
    res = create_issue(title=issue_title, body=issue_body, labels=["LOOP-ALERT", "bug"])
    if res:
        print(f"[ALERT MANAGER] Issue created: {res}")
    else:
        print(f"[ALERT MANAGER] Failed to create Issue via gh. Please inspect state.yml.", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("[AlertManager] Running test alert...")
        trigger_alert("Test Alert", "This is a dry-run test of the alert system.")
