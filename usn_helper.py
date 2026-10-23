from __future__ import annotations

import argparse
import ctypes
import json
import multiprocessing.connection as mp_connection
import time

from core.usn_journal import JournalCursor, read_changed_paths


IDLE_TIMEOUT_SECONDS = 300
CONNECT_TIMEOUT_SECONDS = 15
MAX_REQUEST_BYTES = 1024 * 1024

_GENERIC_READ = 0x80000000
_GENERIC_WRITE = 0x40000000
_OPEN_EXISTING = 3
_FILE_FLAG_OVERLAPPED = 0x40000000
_PIPE_READMODE_MESSAGE = 0x00000002
_ERROR_FILE_NOT_FOUND = 2
_ERROR_PIPE_BUSY = 231
_ERROR_SEM_TIMEOUT = 121
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def _connect_pipe(pipe_name: str):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    set_pipe_state = kernel32.SetNamedPipeHandleState
    set_pipe_state.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    set_pipe_state.restype = ctypes.c_int

    deadline = time.monotonic() + CONNECT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        handle = create_file(
            pipe_name,
            _GENERIC_READ | _GENERIC_WRITE,
            0,
            None,
            _OPEN_EXISTING,
            _FILE_FLAG_OVERLAPPED,
            None,
        )
        if handle != _INVALID_HANDLE_VALUE:
            read_mode = ctypes.c_uint32(_PIPE_READMODE_MESSAGE)
            if not set_pipe_state(handle, ctypes.byref(read_mode), None, None):
                kernel32.CloseHandle(handle)
                error_code = ctypes.get_last_error()
                raise OSError(error_code, ctypes.WinError(error_code))
            return mp_connection.PipeConnection(handle)

        error_code = ctypes.get_last_error()
        if error_code not in (
            _ERROR_FILE_NOT_FOUND,
            _ERROR_PIPE_BUSY,
            _ERROR_SEM_TIMEOUT,
        ):
            raise OSError(error_code, ctypes.WinError(error_code))
        time.sleep(0.15)

    raise TimeoutError("無法連線到 FolderSyncPro USN 管道")


def _receive_message(connection):
    payload = connection.recv_bytes(MAX_REQUEST_BYTES)
    return json.loads(payload.decode("utf-8"))


def _cursor_from_dict(value):
    if not isinstance(value, dict):
        return None

    return JournalCursor(
        volume_root=str(value["volume_root"]),
        journal_id=int(value["journal_id"]),
        next_usn=int(value["next_usn"]),
    )


def _cursor_to_dict(cursor):
    if cursor is None:
        return None

    return {
        "volume_root": cursor.volume_root,
        "journal_id": cursor.journal_id,
        "next_usn": cursor.next_usn,
    }


def _handle_request(request):
    operation = request.get("op")
    if operation == "ping":
        return {"ok": True}, False

    if operation == "shutdown":
        return {"ok": True}, True

    if operation != "read_changed_paths":
        return {"ok": False, "error": "unsupported operation"}, False

    changes = read_changed_paths(
        request["root"],
        _cursor_from_dict(request.get("previous_cursor")),
    )

    return {
        "ok": True,
        "changes": {
            "paths": sorted(changes.paths),
            "cursor": _cursor_to_dict(changes.cursor),
            "full_scan_required": changes.full_scan_required,
            "reason": changes.reason,
        },
    }, False


def serve(pipe_name: str):
    deadline = time.monotonic() + IDLE_TIMEOUT_SECONDS

    try:
        connection = _connect_pipe(pipe_name)
        try:
            while time.monotonic() < deadline:
                remaining = min(2.0, deadline - time.monotonic())
                if not connection.poll(max(remaining, 0.0)):
                    continue

                try:
                    request = _receive_message(connection)
                    response, should_stop = _handle_request(request)
                except (
                    EOFError,
                    KeyError,
                    TypeError,
                    ValueError,
                    RuntimeError,
                ) as exc:
                    response = {"ok": False, "error": str(exc)}
                    should_stop = False

                connection.send_bytes(
                    json.dumps(response, ensure_ascii=False).encode("utf-8")
                )
                deadline = time.monotonic() + IDLE_TIMEOUT_SECONDS
                if should_stop:
                    return
        finally:
            connection.close()
    except (EOFError, OSError, RuntimeError, TimeoutError):
        return


def main():
    parser = argparse.ArgumentParser(description="FolderSyncPro USN helper")
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--pipe", required=True)
    args = parser.parse_args()

    if args.server:
        serve(args.pipe)


if __name__ == "__main__":
    main()

