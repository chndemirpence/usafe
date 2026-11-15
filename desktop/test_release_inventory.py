import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from release_inventory import check, create, safe_path


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        for name in ("USAFE Connect.exe", "Tor Browser/Browser/firefox.exe", "Source/connect_app.py", "Source/LICENSE", "_internal/runtime/tor/tor.exe"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture")
        manifest = {"release": "fixture", "source": "https://example.invalid", "archive_sha256": "fixture", "signing_key": "fixture",
                    "files": {"tor/tor.exe": hashlib.sha256(b"fixture").hexdigest()}}
        (self.root / "_internal/runtime/verified-files.json").write_text(json.dumps(manifest))

    def test_clean_package_and_changed_missing_extra_files(self):
        create(self.root, "fixture")
        self.assertTrue(check(self.root)["matches"])
        (self.root / "USAFE Connect.exe").write_bytes(b"modified")
        (self.root / "Source/LICENSE").unlink()
        (self.root / "extra.txt").touch()
        report = check(self.root)
        self.assertFalse(report["matches"])
        self.assertEqual(report["changed"], ["USAFE Connect.exe"])
        self.assertEqual(report["missing"], ["Source/LICENSE"])
        self.assertEqual(report["extra"], ["extra.txt"])
        self.assertFalse(report["publisher_authenticated"])

    def test_rejects_private_browser_state(self):
        (self.root / "Tor Browser/Browser/places.sqlite").touch()
        with self.assertRaisesRegex(ValueError, "Private"):
            create(self.root, "fixture")

    def test_rejects_changed_runtime_before_inventory_creation(self):
        (self.root / "_internal/runtime/tor/tor.exe").write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "runtime differs"):
            create(self.root, "fixture")

    def test_rejects_paths_outside_package(self):
        for name in ("../secret", "C:/secret", "/secret", "folder/../../secret", "folder\\secret", "name:stream"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_path(self.root, name)

    def test_does_not_overwrite_existing_inventory(self):
        create(self.root, "fixture")
        with self.assertRaises(ValueError):
            create(self.root, "fixture")


if __name__ == "__main__":
    unittest.main()
