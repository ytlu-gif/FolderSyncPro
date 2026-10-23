from __future__ import annotations

import argparse
import json
import socket
import time

from core.usn_journal import JournalCursor, read_changed_paths


IDLE_TIMEOUT_SECONDS = 300
MAX_REQUEST_BYTES = 1024 * 1024


def _receive_line(connection) -> bytes:
    chunks = []
    total = 0

    while True:
        chunk = connection.recv(65536)
        if not chunk:
            raise RuntimeError("主程式提前關閉連線")

        newline = chunk.find(b"\n")
        if newline >= 0:
            chunks.append(chunk[:newline])
            total += newline
            break

        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_REQUEST_BYTES:
            raise RuntimeError("USN helper 收到過大的請求")

    return b"".join(chunks)


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


def _handle_request(request, expected_token):
    if request.get("token") != expected_token:
        return {"ok": False, "error": "invalid token"}, False

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


def serve(port: int, token: str):
    deadline = time.monotonic() + IDLE_TIMEOUT_SECONDS

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", port))
        server.listen(1)
        server.settimeout(2.0)

        while time.monotonic() < deadline:
            try:
                connection, _address = server.accept()
            except socket.timeout:
                continue

            deadline = time.monotonic() + IDLE_TIMEOUT_SECONDS
            with connection:
                try:
                    request = json.loads(_receive_line(connection).decode("utf-8"))
                    response, should_stop = _handle_request(request, token)
                except (KeyError, TypeError, ValueError, RuntimeError) as exc:
                    response = {"ok": False, "error": str(exc)}
                    should_stop = False

                connection.sendall(
                    (json.dumps(response, ensure_ascii=False) + "\n").encode(
                        "utf-8"
                    )
                )

            if should_stop:
                return


def main():
    parser = argparse.ArgumentParser(description="FolderSyncPro USN helper")
    parser.add_argument("--server", action="store_true")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()

    if args.server:
        serve(args.port, args.token)


if __name__ == "__main__":
    main()

