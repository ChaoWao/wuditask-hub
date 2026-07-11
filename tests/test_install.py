from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from wuditask.install import install_agent_access

ROOT = Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def test_installer_registers_both_agent_products(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            result = install_agent_access(ROOT, home=home)
            config = json.loads((home / ".wuditask" / "config.json").read_text())

            self.assertEqual(str(ROOT.resolve()), config["hub_path"])
            self.assertEqual(
                str((home / ".wuditask" / "config.json").resolve()),
                result["config"],
            )
            for base in (home / ".agents" / "skills", home / ".claude" / "skills"):
                self.assertTrue((base / "wuditask").is_symlink())
                self.assertTrue((base / "wuditask-install").is_symlink())
                self.assertEqual(
                    (ROOT / ".agents" / "skills" / "wuditask").resolve(),
                    (base / "wuditask").resolve(),
                )
            self.assertTrue((home / ".local" / "bin" / "wuditask").is_symlink())

    def test_install_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            install_agent_access(ROOT, home=home)
            second = install_agent_access(ROOT, home=home)
            self.assertTrue(all(not link["changed"] for link in second["links"]))


if __name__ == "__main__":
    unittest.main()
