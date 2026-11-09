import os
import tempfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core import sync_engine as engine


class CopyFailuresTests(unittest.TestCase):
    def test_missing_source_reports_both_paths(self):
        with TemporaryDirectory() as temp:
            src = Path(temp) / 'missing.pdf'
            dst = Path(temp) / 'target' / 'missing.pdf'
            messages = []
            self.assertFalse(engine.safe_copy(src, dst, messages.append))
            self.assertIn(str(src), messages[0])
            self.assertIn(str(dst), messages[0])
            self.assertIn('source_exists=False', messages[0])

    def test_failed_conflict_preserves_state_and_does_not_advance_cursor(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            src, dst = root / 'source', root / 'target'
            src.mkdir()
            dst.mkdir()
            (src / 'a.txt').write_text('new version')
            (dst / 'a.txt').write_text('old')
            old_state = {'a.txt': {'size': 3, 'mtime': 1}}
            with patch.object(engine, '_load_state', return_value=old_state), \
                 patch.object(engine, '_save_state') as save_state, \
                 patch.object(engine, '_save_journal_cursors') as save_cursor, \
                 patch.object(engine.shutil, 'copy2', side_effect=FileNotFoundError('missing')), \
                 patch.object(engine, 'add_sync_log'):
                result = engine.sync_folder_two_way(src, dst, changed_paths={'a.txt'})
            self.assertEqual(result['errors'], 1)
            self.assertEqual(result['updated'], 0)
            self.assertEqual(save_state.call_args.args[1], old_state)
            self.assertTrue(save_cursor.call_args.kwargs['cancelled'])

    @unittest.skipUnless(os.name == 'nt', 'Windows long paths')
    def test_copy_deep_path(self):
        with TemporaryDirectory(dir=engine._io_path(tempfile.gettempdir())) as temp:
            src = Path(temp) / 'source.txt'
            src.write_text('deep path content')
            dst = Path(temp)
            for index in range(16):
                dst /= f'long-directory-{index:02}'
            dst /= 'target.txt'
            self.assertGreater(len(str(dst)), 260)
            self.assertTrue(engine.safe_copy(src, dst))
            self.assertEqual(engine._io_path(dst).read_text(), src.read_text())
