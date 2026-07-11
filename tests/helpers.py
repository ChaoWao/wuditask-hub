from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from wuditask.model import Identity
from wuditask.repository import TaskRepository
from wuditask.workflow import create_task

ACTOR = Identity("alice", 1001)
OTHER_ACTOR = Identity("bob", 1002)


def spec(
    title: str = "Test task",
    *,
    repo: str = "acme/service",
    dependencies: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "repo": repo,
        "goal": f"Complete {title.lower()} with observable behavior.",
        "context": ["Keep the public API stable."],
        "acceptance_criteria": [
            {
                "description": f"{title} passes its regression check.",
                "verification": {
                    "type": "command",
                    "value": "python3 -m unittest",
                },
            }
        ],
        "dependencies": dependencies or [],
        "priority": "P2",
        "links": [],
    }


def make_repository(root: Path) -> TaskRepository:
    repository = TaskRepository(root)
    repository.ensure_layout()
    return repository


def add_task(
    repository: TaskRepository,
    task_id: str,
    *,
    title: str = "Test task",
    repo: str = "acme/service",
    dependencies: list[str] | None = None,
) -> dict[str, Any]:
    return create_task(
        repository,
        spec(title, repo=repo, dependencies=dependencies),
        ACTOR,
        task_id=task_id,
        now="2026-07-11T12:00:00Z",
    )["task"]


def git(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *command],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
