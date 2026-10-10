from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator


CancelFunc = Callable[[], bool]


IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}

IGNORED_FILE_NAMES = {
    ".ds_store",
    "thumbs.db",
    "desktop.ini",
}


@dataclass(frozen=True, slots=True)
class FileEntry:
    path: Path
    relative_path: Path
    size: int
    mtime: float


def should_ignore_name(name: str, is_dir: bool) -> bool:
    normalized_name = name.lower()

    if is_dir:
        return normalized_name in IGNORED_DIR_NAMES

    return (
        normalized_name in IGNORED_FILE_NAMES
        or normalized_name.startswith("~$")
    )


def iter_sync_files(
    root_path,
    cancel_func: CancelFunc | None = None,
) -> Iterator[FileEntry]:
    root = Path(root_path)

    if not root.exists():
        return

    stack = [root]

    while stack:
        if cancel_func and cancel_func():
            return

        folder = stack.pop()

        try:
            with os.scandir(folder) as entries:
                child_dirs: list[Path] = []

                for entry in entries:
                    if cancel_func and cancel_func():
                        return

                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if should_ignore_name(entry.name, is_dir=True):
                                continue

                            child_dirs.append(Path(entry.path))
                            continue

                        if not entry.is_file(follow_symlinks=False):
                            continue

                        if should_ignore_name(entry.name, is_dir=False):
                            continue

                        stat = entry.stat(follow_symlinks=False)
                        path = Path(entry.path)

                        yield FileEntry(
                            path=path,
                            relative_path=path.relative_to(root),
                            size=stat.st_size,
                            mtime=stat.st_mtime,
                        )

                    except OSError:
                        continue

                stack.extend(reversed(child_dirs))

        except OSError:
            continue


def iter_sync_paths(
    root_path,
    cancel_func: CancelFunc | None = None,
) -> Iterator[Path]:
    for entry in iter_sync_files(root_path, cancel_func=cancel_func):
        yield entry.path


def get_file_entry(root_path, relative_path) -> FileEntry | None:
    root = Path(root_path)
    relative = Path(relative_path)
    path = root / relative

    if not path.exists() or not path.is_file():
        return None

    if should_ignore_name(path.name, is_dir=False):
        return None

    try:
        stat = path.stat()
    except OSError:
        return None

    return FileEntry(
        path=path,
        relative_path=relative,
        size=stat.st_size,
        mtime=stat.st_mtime,
    )


def scan_sync_folder(
    root_path,
    cancel_func: CancelFunc | None = None,
) -> dict[str, int]:
    root = Path(root_path)

    if not root.exists():
        return {
            "files": 0,
            "folders": 0,
            "size": 0,
        }

    file_count = 0
    folder_count = 0
    total_size = 0
    stack = [root]

    while stack:
        if cancel_func and cancel_func():
            break

        folder = stack.pop()

        try:
            with os.scandir(folder) as entries:
                child_dirs: list[Path] = []

                for entry in entries:
                    if cancel_func and cancel_func():
                        break

                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if should_ignore_name(entry.name, is_dir=True):
                                continue

                            folder_count += 1
                            child_dirs.append(Path(entry.path))
                            continue

                        if not entry.is_file(follow_symlinks=False):
                            continue

                        if should_ignore_name(entry.name, is_dir=False):
                            continue

                        stat = entry.stat(follow_symlinks=False)
                        file_count += 1
                        total_size += stat.st_size

                    except OSError:
                        continue

                stack.extend(reversed(child_dirs))

        except OSError:
            continue

    return {
        "files": file_count,
        "folders": folder_count,
        "size": total_size,
    }
