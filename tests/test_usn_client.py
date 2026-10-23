import unittest
from unittest.mock import patch

from core.usn_client import read_changed_paths_with_elevation
from core.usn_journal import JournalChanges, JournalCursor


class _FakeClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def read_changed_paths(self, root_path, previous_cursor):
        self.calls.append((root_path, previous_cursor))
        return self.result


class USNClientTests(unittest.TestCase):

    @patch("core.usn_client._CLIENT")
    @patch("core.usn_client.read_changed_paths")
    def test_permission_failure_uses_elevated_client(
        self,
        direct_reader,
        client,
    ):
        cursor = JournalCursor("D:\\", 123, 456)
        direct_reader.return_value = JournalChanges(
            frozenset(),
            cursor,
            True,
            "access denied",
            True,
        )
        client.read_changed_paths.return_value = JournalChanges(
            frozenset({"changed.txt"}),
            cursor,
            False,
        )

        result = read_changed_paths_with_elevation("D:\\data", cursor)

        self.assertEqual(result.paths, {"changed.txt"})
        client.read_changed_paths.assert_called_once_with("D:\\data", cursor)

    @patch("core.usn_client._CLIENT")
    @patch("core.usn_client.read_changed_paths")
    def test_non_permission_failure_keeps_direct_fallback(
        self,
        direct_reader,
        client,
    ):
        direct = JournalChanges(
            frozenset(),
            None,
            True,
            "journal overflow",
            False,
        )
        direct_reader.return_value = direct

        result = read_changed_paths_with_elevation("D:\\data", None)

        self.assertIs(result, direct)
        client.read_changed_paths.assert_not_called()


if __name__ == "__main__":
    unittest.main()
