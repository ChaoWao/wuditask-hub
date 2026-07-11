from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from wuditask.site_builder import build_site
from wuditask.workflow import claim_task

from tests.helpers import ACTOR, add_task, make_repository

ROOT = Path(__file__).resolve().parents[1]


class SiteTests(unittest.TestCase):
    def test_builds_static_snapshot_without_node(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repository = make_repository(base / "hub")
            task_id = "WDT-20260711T120000Z-A1B2C3"
            add_task(repository, task_id)
            claim_task(repository, ACTOR, task_id=task_id)
            output = base / "public"

            result = build_site(
                repository.load_index(),
                source=ROOT / "site",
                output=output,
                hub_repo="acme/wuditask",
            )
            snapshot = json.loads((output / "snapshot.json").read_text())

            self.assertEqual(1, result["counts"]["in_progress"])
            self.assertEqual("acme/wuditask", snapshot["hub_repo"])
            self.assertEqual(task_id, snapshot["open_tasks"][0]["id"])
            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "styles.css").is_file())
            self.assertTrue((output / "app.js").is_file())
            self.assertTrue((output / ".nojekyll").is_file())
            self.assertTrue((output / ".wuditask-site").is_file())

    def test_refuses_to_clear_unrelated_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repository = make_repository(base / "hub")
            output = base / "output"
            output.mkdir()
            sentinel = output / "keep-me.txt"
            sentinel.write_text("important")

            with self.assertRaisesRegex(Exception, "non-WudiTask"):
                build_site(
                    repository.load_index(),
                    source=ROOT / "site",
                    output=output,
                )
            self.assertEqual("important", sentinel.read_text())


if __name__ == "__main__":
    unittest.main()
