from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .errors import DataValidationError, WudiTaskError
from .model import require_valid_task, validate_task
from .util import atomic_write_json, read_json


@dataclass(frozen=True)
class TaskRecord:
    task: dict[str, Any]
    path: Path
    archived: bool


@dataclass
class TaskIndex:
    open: dict[str, TaskRecord]
    archived: dict[str, TaskRecord]

    @property
    def all(self) -> dict[str, TaskRecord]:
        return {**self.archived, **self.open}

    def get(self, task_id: str) -> TaskRecord | None:
        return self.open.get(task_id) or self.archived.get(task_id)


class TaskRepository:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.open_dir = self.root / "data" / "open"
        self.archive_dir = self.root / "data" / "archive"

    def ensure_layout(self) -> None:
        self.open_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _files(self, directory: Path, recursive: bool) -> Iterable[Path]:
        if not directory.exists():
            return []
        iterator = directory.rglob("*.json") if recursive else directory.glob("*.json")
        return sorted(path for path in iterator if path.is_file())

    def validation_issues(self) -> list[dict[str, str]]:
        issues: list[dict[str, str]] = []
        seen: dict[str, Path] = {}
        locations = (
            (self._files(self.open_dir, False), False),
            (self._files(self.archive_dir, True), True),
        )
        for files, archived in locations:
            for path in files:
                relative = path.relative_to(self.root).as_posix()
                try:
                    task = read_json(path)
                except WudiTaskError as exc:
                    issues.append({"path": relative, "message": exc.message})
                    continue
                for issue in validate_task(task, archived=archived):
                    issues.append(
                        {
                            "path": f"{relative}:{issue['path']}",
                            "message": issue["message"],
                        }
                    )
                if not isinstance(task, dict) or not isinstance(task.get("id"), str):
                    continue
                task_id = task["id"]
                if path.stem != task_id:
                    issues.append(
                        {
                            "path": relative,
                            "message": f"filename must be {task_id}.json",
                        }
                    )
                if task_id in seen:
                    issues.append(
                        {
                            "path": relative,
                            "message": f"duplicates task ID already stored at {seen[task_id]}",
                        }
                    )
                else:
                    seen[task_id] = path
                if archived and isinstance(task.get("completion"), dict):
                    completed_at = task["completion"].get("completed_at")
                    if isinstance(completed_at, str) and len(completed_at) >= 4:
                        expected_year = completed_at[:4]
                        try:
                            actual_year = path.relative_to(self.archive_dir).parts[0]
                        except (ValueError, IndexError):
                            actual_year = ""
                        if actual_year != expected_year:
                            issues.append(
                                {
                                    "path": relative,
                                    "message": f"archived task must be under {expected_year}/",
                                }
                            )
        return issues

    def load_index(self) -> TaskIndex:
        issues = self.validation_issues()
        if issues:
            raise DataValidationError(issues)
        open_tasks: dict[str, TaskRecord] = {}
        archived_tasks: dict[str, TaskRecord] = {}
        for path in self._files(self.open_dir, False):
            task = read_json(path)
            open_tasks[task["id"]] = TaskRecord(task=task, path=path, archived=False)
        for path in self._files(self.archive_dir, True):
            task = read_json(path)
            archived_tasks[task["id"]] = TaskRecord(task=task, path=path, archived=True)
        return TaskIndex(open=open_tasks, archived=archived_tasks)

    def add(self, task: dict[str, Any]) -> Path:
        require_valid_task(task, archived=False)
        index = self.load_index()
        if index.get(task["id"]):
            raise WudiTaskError(
                "task_already_exists",
                f"Task {task['id']} already exists.",
                details={"task_id": task["id"]},
            )
        path = self.open_dir / f"{task['id']}.json"
        atomic_write_json(path, task)
        return path

    def write_open(self, task: dict[str, Any]) -> Path:
        require_valid_task(task, archived=False)
        path = self.open_dir / f"{task['id']}.json"
        if not path.exists():
            raise WudiTaskError(
                "task_not_open",
                f"Task {task['id']} is not open.",
                details={"task_id": task["id"]},
            )
        atomic_write_json(path, task)
        return path

    def archive(self, task: dict[str, Any]) -> Path:
        require_valid_task(task, archived=True)
        source = self.open_dir / f"{task['id']}.json"
        if not source.exists():
            raise WudiTaskError(
                "task_not_open",
                f"Task {task['id']} is not open.",
                details={"task_id": task["id"]},
            )
        year = task["completion"]["completed_at"][:4]
        destination = self.archive_dir / year / f"{task['id']}.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(source, task)
        os.replace(source, destination)
        return destination
