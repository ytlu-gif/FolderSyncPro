import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.usn_journal import (
    JournalCursor,
    USNJournalUnavailable,
    USNRecord,
    read_changed_paths,
)


class USNJournalTests(unittest.TestCase):

    @patch(
        "core.usn_journal._query_journal",
        return_value=(123, 100, 200, 0),
    )
    def test_missing_cursor_requires_full_scan(self, _query):
        with TemporaryDirectory() as temp_dir:
            changes = read_changed_paths(temp_dir, None)

        self.assertTrue(changes.full_scan_required)
        self.assertEqual(changes.paths, frozenset())
        self.assertEqual(changes.cursor.journal_id, 123)
        self.assertEqual(changes.cursor.next_usn, 200)

    @patch(
        "core.usn_journal._query_journal",
        return_value=(123, 100, 200, 0),
    )
    def test_current_cursor_returns_no_changes(self, _query):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cursor = JournalCursor(
                volume_root=root.anchor.upper(),
                journal_id=123,
                next_usn=200,
            )
            changes = read_changed_paths(root, cursor)

        self.assertFalse(changes.full_scan_required)
        self.assertEqual(changes.paths, frozenset())

    @patch(
        "core.usn_journal._directory_reference_map",
        return_value={42: Path("documents")},
    )
    @patch(
        "core.usn_journal._read_records",
        return_value=[
            USNRecord(
                file_reference_number=99,
                parent_file_reference_number=42,
                usn=150,
                reason=0,
                file_attributes=0,
                file_name="report.docx",
            )
        ],
    )
    @patch(
        "core.usn_journal._query_journal",
        return_value=(123, 100, 200, 0),
    )
    def test_changed_file_is_resolved_to_relative_path(
        self,
        _query,
        _read,
        _directory_map,
    ):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cursor = JournalCursor(
                volume_root=root.anchor.upper(),
                journal_id=123,
                next_usn=100,
            )
            changes = read_changed_paths(root, cursor)

        self.assertFalse(changes.full_scan_required)
        self.assertEqual(changes.paths, {"documents/report.docx"})

    @patch(
        "core.usn_journal._query_journal",
        side_effect=USNJournalUnavailable("journal unavailable"),
    )
    def test_journal_failure_requests_full_scan(self, _query):
        with TemporaryDirectory() as temp_dir:
            changes = read_changed_paths(
                temp_dir,
                JournalCursor("C:\\", 123, 100),
            )

        self.assertTrue(changes.full_scan_required)
        self.assertIn("journal unavailable", changes.reason)

    @patch(
        "core.usn_journal._query_journal",
        side_effect=USNJournalUnavailable(
            "access denied",
            requires_elevation=True,
        ),
    )
    def test_permission_failure_marks_elevation_required(self, _query):
        with TemporaryDirectory() as temp_dir:
            changes = read_changed_paths(temp_dir, None)

        self.assertTrue(changes.full_scan_required)
        self.assertTrue(changes.needs_elevation)


if __name__ == "__main__":
    unittest.main()
