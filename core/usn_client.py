from __future__ import annotations

import atexit
import ctypes
import json
import multiprocessing.connection as mp_connection
import os
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
        self._listener = None
        self._connection = None
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
            except (
                EOFError,
                KeyError,
                OSError,
                RuntimeError,
                TimeoutError,
                ValueError,
            ):
                self._started = False
                self._close_transport()
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
            if (
                not self._started
                and self._connection is None
                and self._listener is None
            ):
                return

            try:
                if self._connection is not None:
                    self._exchange({"op": "shutdown"}, timeout=5.0)
            except (EOFError, OSError, RuntimeError, TimeoutError, ValueError):
                pass
            finally:
                self._started = False
                self._close_transport()

    def _ensure_started(self) -> bool:
        if self._started:
            try:
                self._exchange({"op": "ping"}, timeout=3.0)
                return True
            except (EOFError, OSError, RuntimeError, TimeoutError, ValueError):
                self._started = False

                self._close_transport()

        try:
            listener = mp_connection.Listener(
                family="AF_PIPE",
                authkey=None,
            )
        except (OSError, RuntimeError):
            return False

        self._listener = listener
        pipe_name = str(listener.address)
        if not self._launch_helper(pipe_name):
            self._close_transport()
            return False

        accepted = []

        def accept_connection():
            try:
                accepted.append(listener.accept())
            except (OSError, RuntimeError):
                return

        accept_thread = threading.Thread(
            target=accept_connection,
            name="FolderSyncPro-USN-pipe",
            daemon=True,
        )
        accept_thread.start()
        deadline = time.monotonic() + _CONNECT_TIMEOUT
        while accept_thread.is_alive() and time.monotonic() < deadline:
            accept_thread.join(0.15)

        if not accepted:
            self._close_transport()
            return False

        self._connection = accepted[0]
        try:
            response = self._exchange({"op": "ping"}, timeout=3.0)
            if response.get("ok"):
                self._started = True
                return True
        except (EOFError, OSError, RuntimeError, TimeoutError, ValueError):
            pass

        self._close_transport()
        return False

    def _launch_helper(self, pipe_name: str) -> bool:
        if os.name != "nt":
            return False

        project_root = Path(__file__).resolve().parents[1]
        helper_path = Path(sys.executable).with_name(
            "FolderSyncProUsnHelper.exe"
        )

        if getattr(sys, "frozen", False):
            executable = helper_path
            params = f"--server --pipe {pipe_name}"
        else:
            executable = Path(sys.executable)
            params = f"-m usn_helper --server --pipe {pipe_name}"
            working_directory = project_root

        if not executable.exists():
            return False

        if getattr(sys, "frozen", False):
            working_directory = executable.parent

        # The pipe name is generated by multiprocessing and intentionally has
        # no whitespace or quoting characters. No bearer token is exposed in
        # the elevated process command line.
        if (
            not pipe_name.startswith("\\\\.\\pipe\\")
            or any(char in pipe_name for char in ' \t\r\n"')
        ):
            return False

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
                str(working_directory),
                0,
            )
        except (AttributeError, OSError, TypeError):
            return False

        return int(result or 0) > 32

    def _exchange(self, payload, timeout=_REQUEST_TIMEOUT):
        if self._connection is None:
            raise RuntimeError("USN helper 尚未啟動")

        message = dict(payload)
        encoded = json.dumps(message, ensure_ascii=False).encode("utf-8")
        self._connection.send_bytes(encoded)
        if not self._connection.poll(timeout):
            raise TimeoutError("USN helper 回應逾時")

        response = self._connection.recv_bytes(_MAX_RESPONSE_BYTES)
        return json.loads(response.decode("utf-8"))

    def _close_transport(self):
        connection = self._connection
        listener = self._listener
        self._connection = None
        self._listener = None

        for transport in (connection, listener):
            if transport is None:
                continue
            try:
                transport.close()
            except (OSError, ValueError):
                pass


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

