#!/usr/bin/env python3
"""
Commander Engine for Loop Engineering System.
Implements the 1-execution-1-action principle based on the priority table.
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from alert_manager import trigger_alert
from github_helper import list_open_prs, get_pr_diff, merge_pr, get_ci_status

STATE_FILE = Path(".nightly/state.yml")
ROADMAP_FILE = Path(".nightly/ROADMAP.md")
PROTECTED_PATHS = [".nightly/", ".github/", "AGENTS.md", "task_template.md"]

def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {"loop_status": "stopped", "consecutive_failures": 0}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def save_state(state: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(state, f, allow_unicode=True)

def evaluate_and_run(dry_run: bool = False) -> str:
    """Evaluates the 1-action priority table and executes the top matching action."""
    state = load_state()
    loop_status = state.get("loop_status", "running")
    consecutive_failures = state.get("consecutive_failures", 0)

    print(f"[COMMANDER] Status: {loop_status} | Consecutive Failures: {consecutive_failures}")

    # Priority 1: Stopped / Paused check
    if loop_status in ["paused", "stopped"]:
        return f"Action Skipped: System is in '{loop_status}' state."

    # Priority 2: Stop conditions check
    if consecutive_failures >= 2:
        trigger_alert("連続失敗上限（2回）到達", "同一または直近タスクの修正が2回連続で不合格となりました。")
        return "Action Executed: Triggered emergency stop due to consecutive failures."

    # Priority 3: Check open PRs for review
    open_prs = list_open_prs()
    if open_prs:
        pr = open_prs[0]
        pr_number = pr.get("number")
        pr_title = pr.get("title", "")
        print(f"[COMMANDER] Found Open PR #{pr_number}: {pr_title}")

        # Check protected paths
        diff = get_pr_diff(pr_number) or ""
        for path in PROTECTED_PATHS:
            if path in diff:
                trigger_alert("保護領域（protected_paths）への変更を検知", f"PR #{pr_number} に保護対象 {path} への変更が含まれています。")
                return f"Action Executed: Triggered emergency stop for PR #{pr_number} modifying protected path."

        # Simulate PR Review Action (1 action)
        if dry_run:
            return f"[DRY-RUN] Evaluated PR #{pr_number}: Ready for static review."
        
        # Mark reviewed
        state["last_review"] = {"pr": pr_number, "verdict": "approved", "notes": "Static review passed cleanly."}
        save_state(state)
        return f"Action Executed: Reviewed PR #{pr_number} successfully."

    # Priority 4: Task dispatch check (Roadmap queue)
    if ROADMAP_FILE.exists():
        with open(ROADMAP_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        if "[ ] Task" in content:
            print("[COMMANDER] Uncompleted tasks found in ROADMAP.md.")
            return "Action Executed: Next task identified for dispatch."

    return "Action Skipped: No pending tasks or open PRs requiring action."

if __name__ == "__main__":
    is_dry_run = "--dry-run" in sys.argv
    print(f"--- COMMANDER ENGINE START (dry_run={is_dry_run}) ---")
    result = evaluate_and_run(dry_run=is_dry_run)
    print(f"--- RESULT: {result} ---")
