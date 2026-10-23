from __future__ import annotations

import atexit
import ctypes
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from core.usn_journal import (
    JournalChanges,
    JournalCursor,
    read_changed_paths,
)


_CONNECT_TIMEOUT = 15.0
_REQUEST_TIMEOUT = 30.0
_MAX_RESPONSE_BYTES = 16 * 1024 * 1024


def _cursor_to_dict(cursor: JournalCursor | None):
    if cursor is None:
        return None

    return {
        "volume_root": cursor.volume_root,
        "journal_id": cursor.journal_id,
        "next_usn": cursor.next_usn,
    }


def _cursor_from_dict(value) -> JournalCursor | None:
    if not isinstance(value, dict):
        return None

    return JournalCursor(
        volume_root=str(value["volume_root"]),
        journal_id=int(value["journal_id"]),
        next_usn=int(value["next_usn"]),
    )


class ElevatedUSNClient:
    """Talk to one elevated helper process for the lifetime of the GUI."""

    def __init__(self):
        self._port: int | None = None
        self._token: str | None = None
        self._started = False
        self._disabled = False
        self._lock = threading.Lock()

    def read_changed_paths(
        self,
        root_path,
        previous_cursor: JournalCursor | None,
    ) -> JournalChanges | None:
        if os.name != "nt" or self._disabled:
            return None

        with self._lock:
            if not self._ensure_started():
                self._disabled = True
                return None

            request = {
                "op": "read_changed_paths",
                "root": str(Path(root_path).resolve()),
                "previous_cursor": _cursor_to_dict(previous_cursor),
            }

            try:
                response = self._exchange(request)
            except (OSError, RuntimeError, ValueError, KeyError):
                self._started = False
                return None

            if not response.get("ok"):
                return None

            changes = response.get("changes")
            if not isinstance(changes, dict):
                return None

            return JournalChanges(
                paths=frozenset(changes.get("paths", [])),
                cursor=_cursor_from_dict(changes.get("cursor")),
                full_scan_required=bool(changes.get("full_scan_required")),
                reason=str(changes.get("reason", "")),
                needs_elevation=False,
            )

    def close(self):
        with self._lock:
            if not self._started:
                return

            try:
                self._exchange({"op": "shutdown"}, timeout=5.0)
            except (OSError, RuntimeError, ValueError):
                pass
            finally:
                self._started = False
                self._port = None
                self._token = None

    def _ensure_started(self) -> bool:
        if self._started:
            try:
                self._exchange({"op": "ping"}, timeout=3.0)
                return True
            except (OSError, RuntimeError, ValueError):
                self._started = False

        port = self._find_free_port()
        token = secrets.token_urlsafe(32)

        if not self._launch_helper(port, token):
            return False

        deadline = time.monotonic() + _CONNECT_TIMEOUT
        while time.monotonic() < deadline:
            try:
                self._port = port
                self._token = token
                response = self._exchange({"op": "ping"}, timeout=1.0)
                if response.get("ok"):
                    self._started = True
                    return True
            except (OSError, RuntimeError, ValueError):
                time.sleep(0.15)

        self._port = None
        self._token = None
        return False

    @staticmethod
    def _find_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            return int(probe.getsockname()[1])

    def _launch_helper(self, port: int, token: str) -> bool:
        if os.name != "nt":
            return False

        project_root = Path(__file__).resolve().parents[1]
        helper_path = Path(sys.executable).with_name(
            "FolderSyncProUsnHelper.exe"
        )

        if getattr(sys, "frozen", False):
            executable = helper_path
            arguments = [
                "--server",
                "--port",
                str(port),
                "--token",
                token,
            ]
        else:
            script = project_root / "usn_helper.py"
            executable = Path(sys.executable)
            arguments = [
                str(script),
                "--server",
                "--port",
                str(port),
                "--token",
                token,
            ]

        if not executable.exists():
            return False

        params = subprocess.list2cmdline(arguments)

        try:
            shell32 = ctypes.WinDLL("shell32", use_last_error=True)
            shell32.ShellExecuteW.argtypes = [
                ctypes.c_void_p,
                ctypes.c_wchar_p,
                ctypes.c_wchar_p,
                ctypes.c_wchar_p,
                ctypes.c_wchar_p,
                ctypes.c_int,
            ]
            shell32.ShellExecuteW.restype = ctypes.c_void_p
            result = shell32.ShellExecuteW(
                None,
                "runas",
                str(executable),
                params,
                str(executable.parent),
                0,
            )
        except (AttributeError, OSError):
            return False

        return int(result or 0) > 32

    def _exchange(self, payload, timeout=_REQUEST_TIMEOUT):
        if self._port is None or self._token is None:
            raise RuntimeError("USN helper 尚未啟動")

        message = dict(payload)
        message["token"] = self._token
        encoded = (json.dumps(message, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )

        with socket.create_connection(
            ("127.0.0.1", self._port),
            timeout=timeout,
        ) as connection:
            connection.sendall(encoded)
            connection.settimeout(timeout)
            response = self._receive_line(connection)

        return json.loads(response.decode("utf-8"))

    @staticmethod
    def _receive_line(connection) -> bytes:
        chunks = []
        total = 0

        while True:
            chunk = connection.recv(65536)
            if not chunk:
                raise RuntimeError("USN helper 提前關閉連線")

            newline = chunk.find(b"\n")
            if newline >= 0:
                chunks.append(chunk[:newline])
                total += newline
                break

            chunks.append(chunk)
            total += len(chunk)
            if total > _MAX_RESPONSE_BYTES:
                raise RuntimeError("USN helper 回應過大")

        return b"".join(chunks)


_CLIENT: ElevatedUSNClient | None = None


def read_changed_paths_with_elevation(
    root_path,
    previous_cursor: JournalCursor | None,
) -> JournalChanges:
    """Use the elevated helper only when direct USN access is denied."""

    direct = read_changed_paths(root_path, previous_cursor)
    if not direct.needs_elevation:
        return direct

    global _CLIENT
    if _CLIENT is None:
        _CLIENT = ElevatedUSNClient()
        atexit.register(_CLIENT.close)

    elevated = _CLIENT.read_changed_paths(root_path, previous_cursor)
    return elevated or direct

