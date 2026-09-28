from __future__ import annotations

import json
from pathlib import Path
from typing import Any


STATE_DIR = Path("data") / "sync_state"
SUPPORTED_MODES = {"backup", "mirror", "two_way"}


def preview_sync(
    source_path,
    target_path,
    mode="backup",
    project_name="未命名專案",
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
        )

    else:
        preview = _preview_one_way(
            source,
            target,
            mode=mode,
        )

    preview["summary"] = _build_summary(preview)

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
) -> dict[str, Any]:
    preview = _empty_preview()

    for src_file in _iter_files(source):
        relative = src_file.relative_to(source)
        target_file = target / relative

        if not target_file.exists():
            preview["add"].append(
                _make_action(
                    relative,
                    source=src_file,
                    target=target_file,
                    direction="source_to_target",
                    reason="Target file does not exist.",
                )
            )
            continue

        if _needs_source_update(src_file, target_file):
            preview["update"].append(
                _make_action(
                    relative,
                    source=src_file,
                    target=target_file,
                    direction="source_to_target",
                    reason="Source file is newer or file size changed.",
                )
            )

    if mode == "mirror":
        for target_file in _iter_files(target):
            relative = target_file.relative_to(target)
            source_file = source / relative

            if not source_file.exists():
                preview["delete"].append(
                    _make_action(
                        relative,
                        source=source_file,
                        target=target_file,
                        direction="delete_from_target",
                        reason="Target file does not exist in source.",
                    )
                )

    return preview


def _preview_two_way(
    source: Path,
    target: Path,
    project_name: str,
) -> dict[str, Any]:
    preview = _empty_preview()
    state = _load_state(project_name)

    source_files = {
        file.relative_to(source).as_posix(): file
        for file in _iter_files(source)
    }

    target_files = {
        file.relative_to(target).as_posix(): file
        for file in _iter_files(target)
    }

    all_relatives = (
        set(source_files)
        | set(target_files)
        | set(state)
    )

    for relative_key in sorted(all_relatives):
        relative = Path(relative_key)
        src_file = source_files.get(relative_key)
        tgt_file = target_files.get(relative_key)
        was_synced = relative_key in state

        if src_file and tgt_file:
            _preview_two_way_existing_pair(
                preview,
                relative,
                src_file,
                tgt_file,
            )

        elif src_file and not tgt_file:
            if was_synced:
                preview["delete"].append(
                    _make_action(
                        relative,
                        source=src_file,
                        target=target / relative,
                        direction="delete_from_source",
                        reason="Target side appears to have deleted a previously synced file.",
                    )
                )
            else:
                preview["add"].append(
                    _make_action(
                        relative,
                        source=src_file,
                        target=target / relative,
                        direction="source_to_target",
                        reason="New file exists only in source.",
                    )
                )

        elif tgt_file and not src_file:
            if was_synced:
                preview["delete"].append(
                    _make_action(
                        relative,
                        source=source / relative,
                        target=tgt_file,
                        direction="delete_from_target",
                        reason="Source side appears to have deleted a previously synced file.",
                    )
                )
            else:
                preview["add"].append(
                    _make_action(
                        relative,
                        source=tgt_file,
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

    return preview


def _preview_two_way_existing_pair(
    preview: dict[str, list[dict[str, Any]]],
    relative: Path,
    src_file: Path,
    tgt_file: Path,
) -> None:
    src_stat = src_file.stat()
    tgt_stat = tgt_file.stat()

    same_content = (
        src_stat.st_size == tgt_stat.st_size
        and abs(src_stat.st_mtime - tgt_stat.st_mtime) < 1
        and _files_have_same_content(src_file, tgt_file)
    )

    if same_content:
        return

    if src_stat.st_mtime >= tgt_stat.st_mtime:
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


def _iter_files(root: Path):
    if not root.exists():
        return

    for file in root.rglob("*"):
        if file.is_file():
            yield file


def _needs_source_update(
    src_file: Path,
    target_file: Path,
) -> bool:
    src_stat = src_file.stat()
    tgt_stat = target_file.stat()

    return (
        src_stat.st_size != tgt_stat.st_size
        or src_stat.st_mtime > tgt_stat.st_mtime
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
