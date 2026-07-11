from __future__ import annotations

from typing import Any


class WudiTaskError(Exception):
    """A user-facing error with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Any | None = None,
        exit_code: int = 2,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.exit_code = exit_code

    def as_dict(self) -> dict[str, Any]:
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details is not None:
            error["details"] = self.details
        return {"ok": False, "error": error}


class DataValidationError(WudiTaskError):
    def __init__(self, issues: list[dict[str, str]]) -> None:
        super().__init__(
            "invalid_task_data",
            f"Task data has {len(issues)} validation issue(s).",
            details={"issues": issues},
        )
