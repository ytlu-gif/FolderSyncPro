from __future__ import annotations

import ctypes
import os
import struct
from dataclasses import dataclass
from pathlib import Path

from core.file_scanner import should_ignore_name


ERROR_JOURNAL_ENTRY_DELETED = 1177
ERROR_JOURNAL_NOT_ACTIVE = 1179

FSCTL_QUERY_USN_JOURNAL = 0x000900F4
FSCTL_READ_USN_JOURNAL = 0x000900BB

FILE_ATTRIBUTE_DIRECTORY = 0x00000010
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
GENERIC_READ = 0x80000000
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

USN_REASON_DATA_OVERWRITE = 0x00000001
USN_REASON_DATA_EXTEND = 0x00000002
USN_REASON_DATA_TRUNCATION = 0x00000004
USN_REASON_BASIC_INFO_CHANGE = 0x00008000
USN_REASON_CLOSE = 0x80000000
USN_REASON_RENAME_OLD_NAME = 0x00001000
USN_REASON_RENAME_NEW_NAME = 0x00002000
USN_REASON_FILE_DELETE = 0x00000200
USN_REASON_FILE_CREATE = 0x00000100
USN_REASON_REPARSE_POINT_CHANGE = 0x00100000
USN_REASON_SECURITY_CHANGE = 0x00000800

READ_REASON_MASK = (
    USN_REASON_DATA_OVERWRITE
    | USN_REASON_DATA_EXTEND
    | USN_REASON_DATA_TRUNCATION
    | USN_REASON_BASIC_INFO_CHANGE
    | USN_REASON_CLOSE
    | USN_REASON_RENAME_OLD_NAME
    | USN_REASON_RENAME_NEW_NAME
    | USN_REASON_FILE_DELETE
    | USN_REASON_FILE_CREATE
    | USN_REASON_REPARSE_POINT_CHANGE
    | USN_REASON_SECURITY_CHANGE
)

_USN_RECORD_HEADER = struct.Struct("<IHHQQqQIIIIHH")
_READ_USN_DATA = struct.Struct("<qIIQQQ")
_USN_JOURNAL_DATA = struct.Struct("<QqqqqQQ")


class USNJournalUnavailable(RuntimeError):
    """Raised when the Windows volume journal cannot be used safely."""

    def __init__(self, message: str, *, requires_elevation: bool = False):
        super().__init__(message)
        self.requires_elevation = requires_elevation


@dataclass(frozen=True, slots=True)
class JournalCursor:
    volume_root: str
    journal_id: int
    next_usn: int


@dataclass(frozen=True, slots=True)
class USNRecord:
    file_reference_number: int
    parent_file_reference_number: int
    usn: int
    reason: int
    file_attributes: int
    file_name: str


@dataclass(frozen=True, slots=True)
class JournalChanges:
    paths: frozenset[str]
    cursor: JournalCursor | None
    full_scan_required: bool
    reason: str = ""
    needs_elevation: bool = False


def volume_root_for_path(root_path) -> str:
    root = Path(root_path).resolve()
    anchor = root.anchor

    if not anchor or not anchor.endswith("\\"):
        raise USNJournalUnavailable("USN Journal 只支援 Windows 本機磁碟區")

    return anchor.upper()


def read_changed_paths(
    root_path,
    previous_cursor: JournalCursor | None,
) -> JournalChanges:
    """Read changed paths since a saved journal cursor.

    This function never raises for normal capability or permission failures.
    It returns ``full_scan_required=True`` so callers can preserve the
    existing full-scan fallback.
    """

    if os.name != "nt":
        return JournalChanges(
            frozenset(),
            None,
            True,
            "USN Journal 只支援 Windows",
        )

    root = Path(root_path).resolve()

    try:
        volume_root = volume_root_for_path(root)
        journal = _query_journal(volume_root)
    except (OSError, USNJournalUnavailable) as exc:
        return JournalChanges(
            frozenset(),
            None,
            True,
            str(exc),
            getattr(exc, "requires_elevation", False),
        )

    current_cursor = JournalCursor(
        volume_root=volume_root,
        journal_id=journal[0],
        next_usn=journal[2],
    )

    if previous_cursor is None:
        return JournalChanges(
            frozenset(),
            current_cursor,
            True,
            "尚未建立 USN Journal 游標，需要先做一次完整掃描",
        )

    if (
        previous_cursor.volume_root.upper() != volume_root
        or previous_cursor.journal_id != journal[0]
        or previous_cursor.next_usn < journal[1]
        or previous_cursor.next_usn > journal[2]
    ):
        return JournalChanges(
            frozenset(),
            current_cursor,
            True,
            "USN Journal 游標已失效，需要重新建立完整索引",
        )

    if previous_cursor.next_usn == journal[2]:
        return JournalChanges(
            frozenset(),
            current_cursor,
            False,
        )

    try:
        records = _read_records(
            volume_root,
            previous_cursor.next_usn,
            journal[0],
            journal[2],
        )
        paths = _resolve_record_paths(root, records)
    except (OSError, USNJournalUnavailable) as exc:
        return JournalChanges(
            frozenset(),
            current_cursor,
            True,
            str(exc),
            getattr(exc, "requires_elevation", False),
        )

    return JournalChanges(
        paths=frozenset(paths),
        cursor=current_cursor,
        full_scan_required=False,
    )


def _kernel32():
    if os.name != "nt":
        raise USNJournalUnavailable("USN Journal 只支援 Windows")

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.DeviceIoControl.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_void_p,
    ]
    kernel32.DeviceIoControl.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    return kernel32


def _open_volume(volume_root: str):
    kernel32 = _kernel32()
    handle = kernel32.CreateFileW(
        "\\\\.\\" + volume_root.rstrip("\\"),
        GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        OPEN_EXISTING,
        0,
        None,
    )

    if handle == INVALID_HANDLE_VALUE or not handle:
        error = ctypes.get_last_error()
        raise USNJournalUnavailable(
            f"無法開啟 {volume_root} 的 USN Journal，Windows error {error}",
            requires_elevation=error == 5,
        )

    return kernel32, handle


def _query_journal(volume_root: str) -> tuple[int, int, int, int]:
    kernel32, handle = _open_volume(volume_root)

    try:
        output = ctypes.create_string_buffer(4096)
        returned = ctypes.c_uint32()
        ok = kernel32.DeviceIoControl(
            handle,
            FSCTL_QUERY_USN_JOURNAL,
            None,
            0,
            output,
            len(output),
            ctypes.byref(returned),
            None,
        )

        if not ok:
            error = ctypes.get_last_error()
            raise USNJournalUnavailable(
                    f"無法查詢 {volume_root} 的 USN Journal，Windows error {error}",
                    requires_elevation=error == 5,
            )

        if returned.value < _USN_JOURNAL_DATA.size:
            raise USNJournalUnavailable("USN Journal 回傳資料格式不完整")

        values = _USN_JOURNAL_DATA.unpack_from(output.raw)
        journal_id, first_usn, next_usn, lowest_valid_usn = values[:4]
        return journal_id, max(first_usn, lowest_valid_usn), next_usn, values[5]

    finally:
        kernel32.CloseHandle(handle)


def _read_records(
    volume_root: str,
    start_usn: int,
    journal_id: int,
    end_usn: int,
) -> list[USNRecord]:
    kernel32, handle = _open_volume(volume_root)
    records: list[USNRecord] = []

    try:
        current_usn = start_usn

        while current_usn < end_usn:
            request = _READ_USN_DATA.pack(
                current_usn,
                READ_REASON_MASK,
                1,
                0,
                0,
                journal_id,
            )
            input_buffer = ctypes.create_string_buffer(request)
            output = ctypes.create_string_buffer(1024 * 1024)
            returned = ctypes.c_uint32()

            ok = kernel32.DeviceIoControl(
                handle,
                FSCTL_READ_USN_JOURNAL,
                input_buffer,
                len(request),
                output,
                len(output),
                ctypes.byref(returned),
                None,
            )

            if not ok:
                error = ctypes.get_last_error()
                if error == ERROR_JOURNAL_ENTRY_DELETED:
                    raise USNJournalUnavailable(
                        "USN Journal 舊記錄已被覆寫"
                    )
                if error == ERROR_JOURNAL_NOT_ACTIVE:
                    raise USNJournalUnavailable("USN Journal 尚未啟用")
                raise USNJournalUnavailable(
                    f"無法讀取 USN Journal，Windows error {error}",
                    requires_elevation=error == 5,
                )

            if returned.value < 8:
                break

            next_usn = struct.unpack_from("<q", output.raw)[0]
            if next_usn <= current_usn:
                break

            offset = 8
            while offset + _USN_RECORD_HEADER.size <= returned.value:
                header = _USN_RECORD_HEADER.unpack_from(output.raw, offset)
                record_length = header[0]

                if (
                    record_length < _USN_RECORD_HEADER.size
                    or offset + record_length > returned.value
                ):
                    raise USNJournalUnavailable("USN Journal 記錄格式不完整")

                name_length = header[11]
                name_offset = header[12]
                name_start = offset + name_offset
                name_end = name_start + name_length

                if name_end > offset + record_length:
                    raise USNJournalUnavailable("USN Journal 檔名範圍無效")

                file_name = output.raw[name_start:name_end].decode(
                    "utf-16-le",
                    errors="replace",
                )

                records.append(
                    USNRecord(
                        file_reference_number=header[3],
                        parent_file_reference_number=header[4],
                        usn=header[5],
                        reason=header[7],
                        file_attributes=header[10],
                        file_name=file_name,
                    )
                )
                offset += record_length

            current_usn = next_usn

        return records

    finally:
        kernel32.CloseHandle(handle)


def _resolve_record_paths(root: Path, records: list[USNRecord]) -> set[str]:
    directory_refs = _directory_reference_map(root)
    paths: set[str] = set()

    for record in records:
        if record.file_attributes & FILE_ATTRIBUTE_DIRECTORY:
            raise USNJournalUnavailable(
                "USN Journal 包含資料夾變更，需要完整掃描確認子檔案"
            )

        parent = directory_refs.get(record.parent_file_reference_number)
        if parent is None:
            raise USNJournalUnavailable(
                "無法解析 USN Journal 的父資料夾，需要完整掃描"
            )

        relative = Path(parent) / record.file_name
        if any(
            should_ignore_name(part, is_dir=False)
            for part in relative.parts
        ):
            continue

        paths.add(relative.as_posix())

    return paths


def _directory_reference_map(root: Path) -> dict[int, Path]:
    result: dict[int, Path] = {}
    stack = [(root, Path("."))]

    while stack:
        folder, relative = stack.pop()
        reference = _file_reference_number(folder)
        result[reference] = relative

        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    if should_ignore_name(entry.name, is_dir=True):
                        continue
                    child = Path(entry.path)
                    stack.append((child, relative / entry.name))
        except OSError:
            continue

    return result


def _file_reference_number(path: Path) -> int:
    kernel32 = _kernel32()
    handle = kernel32.CreateFileW(
        str(path),
        0,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )

    if handle == INVALID_HANDLE_VALUE or not handle:
        error = ctypes.get_last_error()
        raise USNJournalUnavailable(
            f"無法取得資料夾識別碼，Windows error {error}",
            requires_elevation=error == 5,
        )

    class _FileInformation(ctypes.Structure):
        _fields_ = [
            ("file_attributes", ctypes.c_uint32),
            ("creation_time", ctypes.c_byte * 8),
            ("last_access_time", ctypes.c_byte * 8),
            ("last_write_time", ctypes.c_byte * 8),
            ("volume_serial_number", ctypes.c_uint32),
            ("file_size_high", ctypes.c_uint32),
            ("file_size_low", ctypes.c_uint32),
            ("number_of_links", ctypes.c_uint32),
            ("file_index_high", ctypes.c_uint32),
            ("file_index_low", ctypes.c_uint32),
        ]

    try:
        kernel32.GetFileInformationByHandle.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_FileInformation),
        ]
        kernel32.GetFileInformationByHandle.restype = ctypes.c_int
        info = _FileInformation()

        if not kernel32.GetFileInformationByHandle(
            handle,
            ctypes.byref(info),
        ):
            error = ctypes.get_last_error()
            raise USNJournalUnavailable(
                f"無法取得資料夾識別碼，Windows error {error}"
            )

        return (info.file_index_high << 32) | info.file_index_low

    finally:
        kernel32.CloseHandle(handle)
