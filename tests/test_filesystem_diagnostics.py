from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core import filesystem_diagnostics as fs
from core import sync_engine as engine


def win_error(code):
    error = OSError('copy failed')
    error.winerror = code
    return error


class FilesystemDiagnosticsTests(unittest.TestCase):
    def test_fat32_directory_limit_reports_estimate_and_caches(self):
        with patch.object(fs, 'get_volume_info', return_value=('E:\\', 'FAT32')), \
             patch.object(fs, 'fat_directory_usage', return_value=(4095, 65522)) as usage:
            cache = {}
            hint = fs.copy_error_hint(win_error(82), 'source.csv', Path('cache/a.csv'), cache)
            again = fs.copy_error_hint(win_error(82), 'source.csv', Path('cache/b.csv'), cache)
            self.assertIn('FAT32', hint)
            self.assertIn('4,095', hint)
            self.assertIn('65,522', hint)
            self.assertIn('可能', hint)
            self.assertEqual(hint, again)
            usage.assert_called_once()

    def test_ntfs_or_unknown_volume_does_not_claim_fat32_limit(self):
        for info in [('D:\\', 'NTFS'), None]:
            with self.subTest(info=info), patch.object(fs, 'get_volume_info', return_value=info):
                self.assertIsNone(fs.copy_error_hint(win_error(82), 's', 't', {}))

    def test_permission_error_is_not_mislabeled_as_format_limit(self):
        with patch.object(fs, 'get_volume_info') as detect:
            self.assertIsNone(fs.copy_error_hint(win_error(5), 's', 't', {}))
            detect.assert_not_called()

    def test_fat32_large_file_hint(self):
        with patch.object(fs, 'get_volume_info', return_value=('E:\\', 'FAT32')), \
             patch.object(Path, 'stat', return_value=SimpleNamespace(st_size=1 << 32)):
            hint = fs.copy_error_hint(win_error(223), 's', 't', {})
            self.assertIn('4,294,967,295', hint)

    def test_directory_estimate_uses_utf16_units(self):
        with TemporaryDirectory() as temp:
            (Path(temp) / ('a' * 184)).write_text('x')
            self.assertEqual(fs.fat_directory_usage(temp), (1, 18))

    def test_repeated_failures_emit_one_notice_and_count_all_errors(self):
        with TemporaryDirectory() as temp:
            src = Path(temp) / 'source.csv'
            src.write_text('data')
            target = Path(temp) / 'target.csv'
            messages = []
            failures, report = engine._count_failures(messages.append)
            with patch.object(engine.shutil, 'copy2', side_effect=win_error(82)), \
                 patch.object(fs, 'get_volume_info', return_value=('E:\\', 'FAT32')):
                for _ in range(3):
                    self.assertFalse(engine.safe_copy(src, target, report))
            self.assertEqual(failures['errors'], 3)
            self.assertEqual(sum(t.startswith('[磁碟格式提醒]') for t in messages), 1)
            self.assertEqual(sum(t.startswith('[錯誤]') for t in messages), 3)

    def test_oversize_preflight_does_not_touch_target(self):
        with TemporaryDirectory() as temp:
            src = Path(temp) / 'source'
            src.write_text('12345')
            target = Path(temp) / 'target'
            with patch.object(engine, 'FAT32_MAX_FILE_SIZE', 3), \
                 patch.object(engine, 'get_volume_info', return_value=('E:\\', 'FAT32')), \
                 patch.object(engine.shutil, 'copy2') as copy:
                self.assertFalse(engine.safe_copy(src, target))
                copy.assert_not_called()
                self.assertFalse(target.exists())
