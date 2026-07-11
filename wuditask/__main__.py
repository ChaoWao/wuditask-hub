from pathlib import Path

from .cli import main


raise SystemExit(main(default_hub=Path(__file__).resolve().parents[1]))
