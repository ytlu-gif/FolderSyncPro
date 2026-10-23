import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.sync_engine import _state_file_path, sync_folder


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

    def test_two_way_same_content_different_mtime_is_not_conflict(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()

            source_file = source / "same.pdf"
            target_file = target / "same.pdf"
            source_file.write_bytes(b"same content")
            target_file.write_bytes(b"same content")

            old_time = time.time() - 120
            new_time = time.time()
            os.utime(
                source_file,
                (old_time, old_time),
            )
            os.utime(
                target_file,
                (new_time, new_time),
            )

            project_name = "unit-test-two-way-same-content-mtime-drift"
            state_path = _state_file_path(project_name)
            state_path.unlink(missing_ok=True)

            try:
                with patch("core.sync_engine.add_sync_log"):
                    result = sync_folder(
                        source,
                        target,
                        mode="two_way",
                        project_name=project_name,
                    )

                self.assertEqual(result["copied"], 0)
                self.assertEqual(result["updated"], 0)
                self.assertEqual(result["conflicts"], 0)
                self.assertEqual(
                    source_file.read_bytes(),
                    target_file.read_bytes(),
                )

            finally:
                state_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
