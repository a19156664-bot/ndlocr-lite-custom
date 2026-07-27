#!/usr/bin/env python3
"""
GitHub Helper for Loop Engineering System.
Provides helper functions to interface with GitHub via `gh` CLI.
"""

import subprocess
import json
import sys
import os
from typing import Dict, Any, List, Optional

def run_gh_command(cmd_args: List[str]) -> Optional[str]:
    """Execute a gh CLI command using clean environment (removing invalid GITHUB_TOKEN if present)."""
    full_cmd = ["gh"] + cmd_args
    env = os.environ.copy()
    env.pop("GITHUB_TOKEN", None)  # Remove dummy/invalid GITHUB_TOKEN to force keyring authentication
    try:
        res = subprocess.run(full_cmd, capture_output=True, text=True, check=True, env=env)
        return res.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[GitHubHelper] Command failed or gh not installed: {full_cmd} -> {e}", file=sys.stderr)
        return None

def create_issue(title: str, body: str, labels: Optional[List[str]] = None) -> Optional[str]:
    """Create a GitHub Issue."""
    cmd = ["issue", "create", "--title", title, "--body", body]
    if labels:
        for lbl in labels:
            cmd.extend(["--label", lbl])
    return run_gh_command(cmd)

def list_open_prs() -> List[Dict[str, Any]]:
    """List open PRs formatted as JSON."""
    out = run_gh_command(["pr", "list", "--json", "number,title,headRefName,state,url,files"])
    if out:
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            pass
    return []

def get_pr_diff(pr_number: int) -> Optional[str]:
    """Get diff text for a given PR number."""
    return run_gh_command(["pr", "diff", str(pr_number)])

def get_ci_status(ref: str = "main") -> Optional[str]:
    """Get CI status for a branch or ref."""
    out = run_gh_command(["run", "list", "--branch", ref, "--limit", "1", "--json", "conclusion"])
    if out:
        try:
            data = json.loads(out)
            if data and len(data) > 0:
                return data[0].get("conclusion")
        except json.JSONDecodeError:
            pass
    return None

def merge_pr(pr_number: int, merge_method: str = "squash") -> bool:
    """Merge a PR if tests pass."""
    res = run_gh_command(["pr", "merge", str(pr_number), f"--{merge_method}", "--auto"])
    return res is not None

if __name__ == "__main__":
    print("[GitHubHelper] Dry run check...")
    status = get_ci_status("main")
    print(f"CI Status: {status}")
