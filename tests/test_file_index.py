import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.file_index import FileIndex
from core.file_scanner import FileEntry


class FileIndexTests(unittest.TestCase):

    def test_file_index_replace_snapshot_and_remove_path(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "index.db"
            project_root = root / "source"
            project_root.mkdir()

            entry = FileEntry(
                path=project_root / "a.txt",
                relative_path=Path("a.txt"),
                size=3,
                mtime=123.0,
            )

            index = FileIndex(db_path)
            index.replace_snapshot(
                "project",
                "source",
                project_root,
                [entry],
            )

            self.assertEqual(
                index.get_paths("project", "source", project_root),
                {"a.txt"},
            )

            index.remove_path(
                "project",
                "source",
                project_root,
                "a.txt",
            )

            self.assertEqual(
                index.get_paths("project", "source", project_root),
                set(),
            )

            index.set_usn_cursor(
                "project",
                "source",
                project_root,
                "C:\\",
                123,
                456,
            )

            self.assertEqual(
                index.get_usn_cursor(
                    "project",
                    "source",
                    project_root,
                ),
                ("C:\\", 123, 456),
            )


if __name__ == "__main__":
    unittest.main()
