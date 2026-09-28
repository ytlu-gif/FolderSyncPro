import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.sync_preview import preview_sync


class SyncPreviewTests(unittest.TestCase):

    def test_backup_preview_adds_and_updates_without_deletes(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()

            (source / "new.txt").write_text(
                "new file",
                encoding="utf-8",
            )

            (source / "changed.txt").write_text(
                "new content",
                encoding="utf-8",
            )

            (target / "changed.txt").write_text(
                "old",
                encoding="utf-8",
            )

            old_time = time.time() - 60
            os.utime(
                target / "changed.txt",
                (old_time, old_time),
            )

            (target / "target_only.txt").write_text(
                "must stay",
                encoding="utf-8",
            )

            preview = preview_sync(
                source,
                target,
                mode="backup",
            )

            self.assertEqual(preview["summary"]["add"], 1)
            self.assertEqual(preview["summary"]["update"], 1)
            self.assertEqual(preview["summary"]["delete"], 0)
            self.assertEqual(preview["summary"]["conflict"], 0)

            self.assertEqual(
                preview["add"][0]["path"],
                "new.txt",
            )

            self.assertEqual(
                preview["update"][0]["path"],
                "changed.txt",
            )

    def test_mirror_preview_includes_target_only_deletes(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()

            (source / "keep.txt").write_text(
                "keep",
                encoding="utf-8",
            )

            (target / "keep.txt").write_text(
                "keep",
                encoding="utf-8",
            )

            (target / "remove.txt").write_text(
                "remove",
                encoding="utf-8",
            )

            preview = preview_sync(
                source,
                target,
                mode="mirror",
            )

            self.assertEqual(preview["summary"]["add"], 0)
            self.assertEqual(preview["summary"]["delete"], 1)
            self.assertEqual(
                preview["delete"][0]["path"],
                "remove.txt",
            )
            self.assertEqual(
                preview["delete"][0]["direction"],
                "delete_from_target",
            )

    def test_two_way_preview_adds_target_only_file_to_source(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()

            (target / "target_new.txt").write_text(
                "new on target",
                encoding="utf-8",
            )

            preview = preview_sync(
                source,
                target,
                mode="two_way",
                project_name="unit-test-project",
            )

            self.assertEqual(preview["summary"]["add"], 1)
            self.assertEqual(preview["summary"]["delete"], 0)
            self.assertEqual(
                preview["add"][0]["path"],
                "target_new.txt",
            )
            self.assertEqual(
                preview["add"][0]["direction"],
                "target_to_source",
            )


if __name__ == "__main__":
    unittest.main()
