from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .errors import WudiTaskError


def _run(
    command: list[str],
    *,
    cwd: Path,
    allowed: set[int] | None = {0},
    timeout: int = 180,
) -> subprocess.CompletedProcess[str]:
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired as exc:
        raise WudiTaskError(
            "selfupdate_command_timeout",
            f"Self-update command timed out: {' '.join(command)}",
            details={"timeout_seconds": timeout},
            exit_code=4,
        ) from exc
    if allowed is not None and process.returncode not in allowed:
        raise WudiTaskError(
            "selfupdate_command_failed",
            f"Self-update command failed: {' '.join(command)}",
            details={
                "returncode": process.returncode,
                "stdout": process.stdout.strip(),
                "stderr": process.stderr.strip(),
            },
            exit_code=4,
        )
    return process


def _git_value(root: Path, *arguments: str) -> str:
    value = _run(["git", *arguments], cwd=root).stdout.strip()
    if not value:
        raise WudiTaskError(
            "selfupdate_git_state_invalid",
            f"Git returned no value for: git {' '.join(arguments)}",
            exit_code=4,
        )
    return value


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    process = _run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        allowed={0, 1},
    )
    return process.returncode == 0


def _worktree_changes(root: Path) -> list[str]:
    output = _run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
    ).stdout
    return [line for line in output.splitlines() if line]


def _candidate_verification(checkout: Path) -> dict[str, Any]:
    tool = checkout / "tools" / "wuditask.py"
    tests = checkout / "tests"
    if not tool.is_file() or not tests.is_dir():
        raise WudiTaskError(
            "selfupdate_candidate_invalid",
            "The candidate does not contain the WudiTask CLI and test suite.",
            details={"checkout": str(checkout)},
            exit_code=4,
        )
    validate = _run(
        [
            sys.executable,
            str(tool),
            "--local",
            "--json",
            "validate",
        ],
        cwd=checkout,
        allowed=None,
    )
    if validate.returncode != 0:
        raise WudiTaskError(
            "selfupdate_candidate_failed",
            "Candidate task data validation failed; the installed clone was not changed.",
            details={
                "step": "validate",
                "stdout": validate.stdout.strip(),
                "stderr": validate.stderr.strip(),
            },
            exit_code=4,
        )
    test = _run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
        ],
        cwd=checkout,
        allowed=None,
    )
    if test.returncode != 0:
        raise WudiTaskError(
            "selfupdate_candidate_failed",
            "Candidate tests failed; the installed clone was not changed.",
            details={
                "step": "tests",
                "stdout": test.stdout.strip(),
                "stderr": test.stderr.strip(),
            },
            exit_code=4,
        )
    summary_lines = (test.stderr or test.stdout).strip().splitlines()
    return {
        "validate": "passed",
        "tests": "passed",
        "test_summary": summary_lines[-1] if summary_lines else "passed",
    }


def self_update(hub_root: Path, *, check_only: bool = False) -> dict[str, Any]:
    root = hub_root.expanduser().resolve()
    top_level = Path(_git_value(root, "rev-parse", "--show-toplevel")).resolve()
    if top_level != root:
        raise WudiTaskError(
            "selfupdate_invalid_hub",
            "The configured hub path is not the root of its Git repository.",
            details={"hub_path": str(root), "git_root": str(top_level)},
        )
    branch = _git_value(root, "branch", "--show-current")
    remote = _git_value(root, "remote", "get-url", "origin")
    changes = _worktree_changes(root)
    if changes and not check_only:
        raise WudiTaskError(
            "selfupdate_dirty_worktree",
            "WudiTask has local changes; refusing to overwrite or stash them.",
            details={
                "hub_path": str(root),
                "changes": changes,
                "action": "Commit, discard, or move these changes explicitly, then retry.",
            },
            exit_code=3,
        )

    _run(["git", "fetch", "--quiet", "origin", branch], cwd=root)
    local_head = _git_value(root, "rev-parse", "HEAD")
    remote_ref = f"origin/{branch}"
    remote_head = _git_value(root, "rev-parse", remote_ref)
    commit_count = int(
        _git_value(root, "rev-list", "--count", f"{local_head}..{remote_head}")
    )
    commits = _run(
        [
            "git",
            "log",
            "--max-count=20",
            "--format=%h %s",
            f"{local_head}..{remote_head}",
        ],
        cwd=root,
    ).stdout.splitlines()

    if local_head == remote_head:
        return {
            "message": "WudiTask is already up to date.",
            "status": "up_to_date",
            "hub_path": str(root),
            "branch": branch,
            "remote": remote,
            "commit": local_head,
            "worktree_clean": not changes,
            "reinstall_required": False,
        }
    if not _is_ancestor(root, local_head, remote_head):
        state = (
            "local_ahead" if _is_ancestor(root, remote_head, local_head) else "diverged"
        )
        if check_only:
            return {
                "message": f"WudiTask cannot fast-forward because the clone is {state}.",
                "status": state,
                "hub_path": str(root),
                "branch": branch,
                "remote": remote,
                "local_commit": local_head,
                "remote_commit": remote_head,
                "worktree_clean": not changes,
                "reinstall_required": False,
            }
        raise WudiTaskError(
            f"selfupdate_{state}",
            f"WudiTask cannot fast-forward because the clone is {state}.",
            details={
                "hub_path": str(root),
                "branch": branch,
                "local_commit": local_head,
                "remote_commit": remote_head,
                "action": "Resolve the local Git history explicitly; self-update will not reset or rebase it.",
            },
            exit_code=3,
        )
    if check_only:
        return {
            "message": f"WudiTask has {commit_count} update commit(s) available.",
            "status": "update_available",
            "hub_path": str(root),
            "branch": branch,
            "remote": remote,
            "local_commit": local_head,
            "remote_commit": remote_head,
            "commit_count": commit_count,
            "commits": commits,
            "worktree_clean": not changes,
            "reinstall_required": False,
        }

    verification: dict[str, Any] = {}
    candidate_head = ""
    for attempt in range(1, 4):
        with tempfile.TemporaryDirectory(prefix="wuditask-selfupdate-") as temporary:
            checkout = Path(temporary) / "hub"
            _run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--depth",
                    "1",
                    "--single-branch",
                    "--branch",
                    branch,
                    remote,
                    str(checkout),
                ],
                cwd=root,
            )
            candidate_head = _git_value(checkout, "rev-parse", "HEAD")
            verification = _candidate_verification(checkout)
        _run(["git", "fetch", "--quiet", "origin", branch], cwd=root)
        remote_head = _git_value(root, "rev-parse", remote_ref)
        if candidate_head == remote_head:
            verification["attempts"] = attempt
            break
    else:
        raise WudiTaskError(
            "selfupdate_remote_moving",
            "The remote branch changed during candidate verification.",
            details={"attempts": 3, "action": "Retry self-update."},
            exit_code=3,
        )

    if _worktree_changes(root) or _git_value(root, "rev-parse", "HEAD") != local_head:
        raise WudiTaskError(
            "selfupdate_local_changed",
            "The installed clone changed during candidate verification.",
            details={"action": "Inspect the clone and retry; no merge was attempted."},
            exit_code=3,
        )
    if not _is_ancestor(root, local_head, candidate_head):
        raise WudiTaskError(
            "selfupdate_diverged",
            "The verified candidate no longer fast-forwards the installed clone.",
            details={"local_commit": local_head, "candidate_commit": candidate_head},
            exit_code=3,
        )

    _run(["git", "merge", "--ff-only", candidate_head], cwd=root)
    return {
        "message": f"Updated WudiTask from {local_head[:7]} to {candidate_head[:7]}.",
        "status": "updated",
        "hub_path": str(root),
        "branch": branch,
        "remote": remote,
        "from_commit": local_head,
        "to_commit": candidate_head,
        "commit_count": commit_count,
        "commits": commits,
        "verification": verification,
        "reinstall_required": False,
    }
