import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.sync_engine import sync_folder


class IncrementalSyncTests(unittest.TestCase):

    def test_backup_changed_paths_only_copy_selected_file(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()

            (source / "changed.txt").write_text(
                "changed",
                encoding="utf-8",
            )
            (source / "untouched.txt").write_text(
                "untouched",
                encoding="utf-8",
            )

            with patch("core.sync_engine.add_sync_log"):
                result = sync_folder(
                    source,
                    target,
                    mode="backup",
                    project_name="unit-test-incremental-backup",
                    changed_paths={"changed.txt"},
                )

            self.assertEqual(result["copied"], 1)
            self.assertTrue((target / "changed.txt").exists())
            self.assertFalse((target / "untouched.txt").exists())

    def test_mirror_changed_paths_delete_selected_missing_file(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()

            target_file = target / "remove.txt"
            target_file.write_text(
                "remove",
                encoding="utf-8",
            )

            def fake_soft_delete(path, log_func=None):
                path.unlink()
                return True

            with patch("core.sync_engine.add_sync_log"):
                with patch(
                    "core.sync_engine._soft_delete",
                    side_effect=fake_soft_delete,
                ):
                    result = sync_folder(
                        source,
                        target,
                        mode="mirror",
                        project_name="unit-test-incremental-mirror",
                        changed_paths={"remove.txt"},
                    )

            self.assertEqual(result["deleted"], 1)
            self.assertFalse(target_file.exists())


if __name__ == "__main__":
    unittest.main()
