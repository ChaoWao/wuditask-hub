#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HUB_ROOT))

from wuditask.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(default_hub=HUB_ROOT))
