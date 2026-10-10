from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.file_scanner import FileEntry, iter_sync_files


STATE_DIR = Path("data") / "sync_state"
SUPPORTED_MODES = {"backup", "mirror", "two_way"}


def preview_sync(
    source_path,
    target_path,
    mode="backup",
    project_name="未命名專案",
    progress_func=None,
    cancel_func=None,
) -> dict[str, Any]:
    """
    Preview planned sync actions without changing files.

    This module is intentionally read-only:

    - does not copy files
    - does not delete files
    - does not write sync logs
    - does not update two-way sync state

    Supported modes:

    - backup: source -> target add/update preview
    - mirror: backup preview + target-only delete preview
    - two_way: bidirectional add/update/delete/conflict preview
    """

    mode = (mode or "backup").lower()
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"不支援的同步模式：{mode}")

    source = Path(source_path)
    target = Path(target_path)

    if not source.exists():
        raise FileNotFoundError(f"來源不存在：{source}")

    if mode == "two_way" and not target.exists():
        raise FileNotFoundError(f"目的不存在：{target}")

    if mode == "two_way":
        preview = _preview_two_way(
            source,
            target,
            project_name=project_name,
            progress_func=progress_func,
            cancel_func=cancel_func,
        )

    else:
        preview = _preview_one_way(
            source,
            target,
            mode=mode,
            progress_func=progress_func,
            cancel_func=cancel_func,
        )

    preview["summary"] = _build_summary(preview)
    preview.setdefault("cancelled", False)

    return preview


def _empty_preview() -> dict[str, list[dict[str, Any]]]:
    return {
        "add": [],
        "update": [],
        "delete": [],
        "conflict": [],
        "skip": [],
    }


def _preview_one_way(
    source: Path,
    target: Path,
    mode: str,
    progress_func=None,
    cancel_func=None,
) -> dict[str, Any]:
    preview = _empty_preview()

    def is_cancelled():
        return bool(cancel_func and cancel_func())

    source_files = list(_iter_file_entries(source, cancel_func=cancel_func))

    if is_cancelled():
        preview["cancelled"] = True
        return preview

    target_files = (
        list(_iter_file_entries(target, cancel_func=cancel_func))
        if mode == "mirror"
        else []
    )

    if is_cancelled():
        preview["cancelled"] = True
        return preview

    total_steps = len(source_files) + len(target_files)
    done_steps = 0
    source_keys = {
        entry.relative_path.as_posix()
        for entry in source_files
    }
    target_entries = {
        entry.relative_path.as_posix(): entry
        for entry in target_files
    }

    for src_entry in source_files:

        if is_cancelled():
            preview["cancelled"] = True
            return preview

        src_file = src_entry.path
        relative = src_entry.relative_path
        relative_key = relative.as_posix()
        target_file = target / relative
        target_entry = target_entries.get(relative_key)

        if mode == "mirror":
            target_exists = target_entry is not None
        else:
            target_exists = target_file.exists()

        if not target_exists:
            preview["add"].append(
                _make_action(
                    relative,
                    source=src_file,
                    target=target_file,
                    direction="source_to_target",
                    reason="Target file does not exist.",
                )
            )
            done_steps += 1
            _report_progress(
                progress_func,
                done_steps,
                total_steps,
                relative,
            )
            continue

        comparison_target = target_entry if target_entry else target_file

        if _needs_source_update(src_entry, comparison_target):
            preview["update"].append(
                _make_action(
                    relative,
                    source=src_file,
                    target=target_file,
                    direction="source_to_target",
                    reason="Source file is newer or file size changed.",
                )
            )

        done_steps += 1
        _report_progress(
            progress_func,
            done_steps,
            total_steps,
            relative,
        )

    if mode == "mirror":
        for target_entry in target_files:

            if is_cancelled():
                preview["cancelled"] = True
                return preview

            target_file = target_entry.path
            relative = target_entry.relative_path
            source_file = source / relative

            if relative.as_posix() not in source_keys:
                preview["delete"].append(
                    _make_action(
                        relative,
                        source=source_file,
                        target=target_file,
                        direction="delete_from_target",
                        reason="Target file does not exist in source.",
                    )
                )

            done_steps += 1
            _report_progress(
                progress_func,
                done_steps,
                total_steps,
                relative,
            )

    return preview


def _preview_two_way(
    source: Path,
    target: Path,
    project_name: str,
    progress_func=None,
    cancel_func=None,
) -> dict[str, Any]:
    preview = _empty_preview()
    state = _load_state(project_name)

    def is_cancelled():
        return bool(cancel_func and cancel_func())

    source_files = {
        entry.relative_path.as_posix(): entry
        for entry in _iter_file_entries(source, cancel_func=cancel_func)
    }

    if is_cancelled():
        preview["cancelled"] = True
        return preview

    target_files = {
        entry.relative_path.as_posix(): entry
        for entry in _iter_file_entries(target, cancel_func=cancel_func)
    }

    if is_cancelled():
        preview["cancelled"] = True
        return preview

    all_relatives = (
        set(source_files)
        | set(target_files)
        | set(state)
    )
    total_steps = len(all_relatives)
    done_steps = 0

    for relative_key in sorted(all_relatives):

        if is_cancelled():
            preview["cancelled"] = True
            return preview

        relative = Path(relative_key)
        src_entry = source_files.get(relative_key)
        tgt_entry = target_files.get(relative_key)
        was_synced = relative_key in state

        if src_entry and tgt_entry:
            _preview_two_way_existing_pair(
                preview,
                relative,
                src_entry,
                tgt_entry,
                state.get(relative_key),
            )

        elif src_entry and not tgt_entry:
            if was_synced:
                preview["delete"].append(
                    _make_action(
                        relative,
                        source=src_entry.path,
                        target=target / relative,
                        direction="delete_from_source",
                        reason="Target side appears to have deleted a previously synced file.",
                    )
                )
            else:
                preview["add"].append(
                    _make_action(
                        relative,
                        source=src_entry.path,
                        target=target / relative,
                        direction="source_to_target",
                        reason="New file exists only in source.",
                    )
                )

        elif tgt_entry and not src_entry:
            if was_synced:
                preview["delete"].append(
                    _make_action(
                        relative,
                        source=source / relative,
                        target=tgt_entry.path,
                        direction="delete_from_target",
                        reason="Source side appears to have deleted a previously synced file.",
                    )
                )
            else:
                preview["add"].append(
                    _make_action(
                        relative,
                        source=tgt_entry.path,
                        target=source / relative,
                        direction="target_to_source",
                        reason="New file exists only in target.",
                    )
                )

        else:
            preview["skip"].append(
                _make_action(
                    relative,
                    source=source / relative,
                    target=target / relative,
                    direction="none",
                    reason="Previously synced file no longer exists on either side.",
                )
            )

        done_steps += 1
        _report_progress(
            progress_func,
            done_steps,
            total_steps,
            relative,
        )

    return preview


def _preview_two_way_existing_pair(
    preview: dict[str, list[dict[str, Any]]],
    relative: Path,
    src_entry: FileEntry,
    tgt_entry: FileEntry,
    state_entry: Any,
) -> None:
    src_file = src_entry.path
    tgt_file = tgt_entry.path

    if _entries_match_synced_state(
        src_entry,
        tgt_entry,
        state_entry,
    ):
        return

    same_content = (
        src_entry.size == tgt_entry.size
        and abs(src_entry.mtime - tgt_entry.mtime) < 1
        and _files_have_same_content(src_file, tgt_file)
    )

    if same_content:
        return

    if src_entry.mtime >= tgt_entry.mtime:
        direction = "source_to_target"
        source = src_file
        target = tgt_file
        winner = "source"
    else:
        direction = "target_to_source"
        source = tgt_file
        target = src_file
        winner = "target"

    preview["conflict"].append(
        _make_action(
            relative,
            source=source,
            target=target,
            direction=direction,
            reason=f"Both sides changed; current sync would let {winner} win.",
        )
    )


def _entries_match_synced_state(
    src_entry: FileEntry,
    tgt_entry: FileEntry,
    state_entry: Any,
) -> bool:
    if not isinstance(state_entry, dict):
        return False

    state_size = state_entry.get("size")
    state_mtime = state_entry.get("mtime")

    if state_size != src_entry.size or state_size != tgt_entry.size:
        return False

    if not isinstance(state_mtime, (int, float)):
        return False

    return (
        abs(src_entry.mtime - state_mtime) < 1
        and abs(tgt_entry.mtime - state_mtime) < 1
    )


def _iter_file_entries(root: Path, cancel_func=None):
    yield from iter_sync_files(root, cancel_func=cancel_func)


def _needs_source_update(
    src_entry: FileEntry,
    target,
) -> bool:
    if isinstance(target, FileEntry):
        target_size = target.size
        target_mtime = target.mtime
    else:
        tgt_stat = target.stat()
        target_size = tgt_stat.st_size
        target_mtime = tgt_stat.st_mtime

    return (
        src_entry.size != target_size
        or src_entry.mtime > target_mtime
    )


def _files_have_same_content(
    left: Path,
    right: Path,
    chunk_size: int = 1024 * 1024,
) -> bool:
    with left.open("rb") as left_file, right.open("rb") as right_file:
        while True:
            left_chunk = left_file.read(chunk_size)
            right_chunk = right_file.read(chunk_size)

            if left_chunk != right_chunk:
                return False

            if not left_chunk:
                return True


def _report_progress(
    progress_func,
    done: int,
    total: int,
    relative: Path,
) -> None:
    if progress_func:
        progress_func(
            done,
            max(total, 1),
            str(relative),
        )


def _make_action(
    relative: Path,
    source: Path,
    target: Path,
    direction: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "path": relative.as_posix(),
        "source": str(source),
        "target": str(target),
        "direction": direction,
        "reason": reason,
    }


def _build_summary(
    preview: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    return {
        "add": len(preview["add"]),
        "update": len(preview["update"]),
        "delete": len(preview["delete"]),
        "conflict": len(preview["conflict"]),
        "skip": len(preview["skip"]),
        "total": (
            len(preview["add"])
            + len(preview["update"])
            + len(preview["delete"])
            + len(preview["conflict"])
            + len(preview["skip"])
        ),
    }


def _state_file_path(project_name: str) -> Path:
    safe_name = "".join(
        c if c.isalnum() or c in ("-", "_") else "_"
        for c in project_name
    )

    return STATE_DIR / f"{safe_name}.json"


def _load_state(project_name: str) -> dict[str, Any]:
    path = _state_file_path(project_name)

    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data

    except Exception:
        return {}

    return {}
