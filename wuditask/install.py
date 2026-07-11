from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from .errors import WudiTaskError
from .util import atomic_write_json, utc_now


def _git_value(root: Path, *arguments: str) -> str | None:
    process = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        return None
    return process.stdout.strip() or None


def _link(source: Path, destination: Path, *, replace: bool) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = source.resolve()
    if destination.is_symlink() and destination.resolve() == source:
        return {"path": str(destination), "target": str(source), "changed": False}
    backup = None
    if os.path.lexists(destination):
        if not replace:
            raise WudiTaskError(
                "install_path_exists",
                f"Install destination already exists: {destination}",
                details={
                    "path": str(destination),
                    "action": "Inspect it, then rerun install with --replace to preserve it as a backup.",
                },
            )
        suffix = utc_now().replace("-", "").replace(":", "")
        backup = destination.with_name(f"{destination.name}.backup-{suffix}")
        destination.rename(backup)
    destination.symlink_to(source, target_is_directory=source.is_dir())
    result = {
        "path": str(destination),
        "target": str(source),
        "changed": True,
    }
    if backup is not None:
        result["backup"] = str(backup)
    return result


def install_agent_access(
    hub_root: Path,
    *,
    home: Path | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    hub_root = hub_root.resolve()
    home = (home or Path.home()).resolve()
    tool = hub_root / "tools" / "wuditask.py"
    operational_skill = hub_root / ".agents" / "skills" / "wuditask"
    installer_skill = hub_root / ".agents" / "skills" / "wuditask-install"
    for required in (
        tool,
        operational_skill / "SKILL.md",
        installer_skill / "SKILL.md",
    ):
        if not required.exists():
            raise WudiTaskError(
                "invalid_hub_clone",
                f"WudiTask clone is missing {required.relative_to(hub_root)}.",
                details={"hub_path": str(hub_root)},
            )

    links = []
    for product_path in (home / ".agents" / "skills", home / ".claude" / "skills"):
        links.append(
            _link(operational_skill, product_path / "wuditask", replace=replace)
        )
        links.append(
            _link(installer_skill, product_path / "wuditask-install", replace=replace)
        )
    launcher = _link(tool, home / ".local" / "bin" / "wuditask", replace=replace)
    links.append(launcher)

    config = {
        "schema_version": 1,
        "hub_path": str(hub_root),
        "remote": _git_value(hub_root, "remote", "get-url", "origin"),
        "branch": _git_value(hub_root, "branch", "--show-current") or "main",
        "installed_at": utc_now(),
    }
    config_path = home / ".wuditask" / "config.json"
    atomic_write_json(config_path, config)
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    launcher_on_path = str((home / ".local" / "bin").resolve()) in {
        str(Path(entry).expanduser().resolve()) for entry in path_entries if entry
    }
    return {
        "message": f"Registered WudiTask clone at {hub_root}.",
        "config": str(config_path),
        "hub_path": str(hub_root),
        "links": links,
        "launcher": str(home / ".local" / "bin" / "wuditask"),
        "launcher_on_path": launcher_on_path,
    }
