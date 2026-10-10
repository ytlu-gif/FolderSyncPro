import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.file_scanner import should_ignore_name
from core.scanner import scan_folder


class FileScannerTests(unittest.TestCase):

    def test_should_ignore_default_high_churn_names(self):
        self.assertTrue(should_ignore_name(".git", is_dir=True))
        self.assertTrue(should_ignore_name("__pycache__", is_dir=True))
        self.assertTrue(should_ignore_name("Thumbs.db", is_dir=False))
        self.assertTrue(should_ignore_name("~$draft.docx", is_dir=False))

        self.assertFalse(should_ignore_name("Documents", is_dir=True))
        self.assertFalse(should_ignore_name("report.docx", is_dir=False))

    def test_scan_folder_skips_default_ignored_dirs_and_files(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            (root / "keep.txt").write_text(
                "keep",
                encoding="utf-8",
            )

            git_dir = root / ".git" / "objects"
            git_dir.mkdir(parents=True)
            (git_dir / "ignored.txt").write_text(
                "ignored",
                encoding="utf-8",
            )

            cache_dir = root / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "ignored.pyc").write_bytes(b"cache")

            (root / "Thumbs.db").write_text(
                "ignored",
                encoding="utf-8",
            )

            result = scan_folder(root)

            self.assertEqual(result["files"], 1)
            self.assertEqual(result["folders"], 0)


if __name__ == "__main__":
    unittest.main()
