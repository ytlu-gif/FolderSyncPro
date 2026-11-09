"""Read-only Windows filesystem detection and conservative copy diagnostics."""

import ctypes
import os
from pathlib import Path

FAT32_MAX_FILE_SIZE = (1 << 32) - 1


def get_volume_info(path):
    """Return (mount point, filesystem), or None when unavailable."""
    if os.name != 'nt':
        return None
    try:
        from ctypes import wintypes
        candidate = Path(os.path.abspath(path))
        while not candidate.exists() and candidate.parent != candidate:
            candidate = candidate.parent
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        get_path = kernel.GetVolumePathNameW
        get_path.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        get_path.restype = wintypes.BOOL
        get_info = kernel.GetVolumeInformationW
        get_info.argtypes = [
            wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD,
        ]
        get_info.restype = wintypes.BOOL
        mount, filesystem = ctypes.create_unicode_buffer(32768), ctypes.create_unicode_buffer(64)
        if not get_path(str(candidate), mount, len(mount)):
            return None
        if not get_info(mount.value, None, 0, None, None, None, filesystem, len(filesystem)):
            return None
        return mount.value, filesystem.value.upper()
    except (OSError, ValueError):
        return None


def fat_directory_usage(folder):
    """Estimate live short/long name entries; not an on-disk allocation audit."""
    files, slots = 0, 2  # '.' and '..' in non-root directories
    with os.scandir(folder) as entries:
        for entry in entries:
            length = len(entry.name.encode('utf-16-le')) // 2
            slots += 1 + (length + 12) // 13
            files += 1
    return files, slots


def copy_error_hint(error, source, target, cache):
    """Diagnose only specific Windows errors, cached per copy operation/folder."""
    code = getattr(error, 'winerror', None)
    if code not in (82, 223):
        return None
    target = Path(target)
    key = ('hint', str(target.parent), code)
    if key in cache:
        return cache[key]
    info = get_volume_info(target.parent)
    if not info or info[1] != 'FAT32':
        cache[key] = None
        return None
    mount, filesystem = info
    if code == 223:
        try:
            if Path(source).stat().st_size <= FAT32_MAX_FILE_SIZE:
                return None
        except OSError:
            return None
        message = (
            f'接收檔案的磁碟 {mount} 為 {filesystem}，來源檔案超過 FAT32 單檔 '
            '4,294,967,295 bytes 上限。請使用 NTFS／exFAT 磁碟，或由原應用程式分割檔案。'
        )
    else:
        usage = ''
        try:
            count, slots = fat_directory_usage(target.parent)
            usage = f'目前 {count:,} 個項目，估計占用 {slots:,} 個目錄項目（非精確磁碟配置值）。'
        except OSError:
            pass
        message = (
            f'接收檔案的磁碟 {mount} 為 {filesystem}，WinError 82 可能是單一資料夾的'
            '目錄項目容量已達上限；長檔名會占用多個目錄項目，即使磁碟仍有空間也可能失敗。'
            f'{usage} 請使用 NTFS／exFAT 磁碟，或在來源程式將資料依年月分資料夾。'
            '此為可能原因，仍需排除空間、權限與檔案系統異常。'
        )
    message += f'\n資料夾：{target.parent}\n變更磁碟格式前請先備份；本程式不會自動格式化磁碟。'
    cache[key] = message
    return message
