from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Iterable

from core.file_scanner import FileEntry


INDEX_DB_FILE = Path("data") / "sync_index.db"


class FileIndex:
    def __init__(self, db_path: Path | str = INDEX_DB_FILE):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialize(self) -> None:
        conn = self._connect()

        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS indexed_files (
                    project_name TEXT NOT NULL,
                    side TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (
                        project_name,
                        side,
                        root_path,
                        relative_path
                    )
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_indexed_files_root
                ON indexed_files(project_name, side, root_path)
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS usn_journal_state (
                    project_name TEXT NOT NULL,
                    side TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    volume_root TEXT NOT NULL,
                    journal_id INTEGER NOT NULL,
                    next_usn INTEGER NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (project_name, side, root_path)
                )
            """)

            conn.commit()

        finally:
            conn.close()

    def replace_snapshot(
        self,
        project_name: str,
        side: str,
        root_path,
        entries: Iterable[FileEntry],
    ) -> None:
        root = str(Path(root_path))
        now = time.time()

        conn = self._connect()

        try:
            conn.execute(
                """
                DELETE FROM indexed_files
                WHERE project_name = ?
                  AND side = ?
                  AND root_path = ?
                """,
                (project_name, side, root),
            )

            conn.executemany(
                """
                INSERT INTO indexed_files (
                    project_name,
                    side,
                    root_path,
                    relative_path,
                    size,
                    mtime,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        project_name,
                        side,
                        root,
                        entry.relative_path.as_posix(),
                        entry.size,
                        entry.mtime,
                        now,
                    )
                    for entry in entries
                ),
            )

            conn.commit()

        finally:
            conn.close()

    def upsert_entry(
        self,
        project_name: str,
        side: str,
        root_path,
        entry: FileEntry,
    ) -> None:
        root = str(Path(root_path))
        now = time.time()

        conn = self._connect()

        try:
            conn.execute(
                """
                INSERT INTO indexed_files (
                    project_name,
                    side,
                    root_path,
                    relative_path,
                    size,
                    mtime,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (
                    project_name,
                    side,
                    root_path,
                    relative_path
                )
                DO UPDATE SET
                    size = excluded.size,
                    mtime = excluded.mtime,
                    updated_at = excluded.updated_at
                """,
                (
                    project_name,
                    side,
                    root,
                    entry.relative_path.as_posix(),
                    entry.size,
                    entry.mtime,
                    now,
                ),
            )

            conn.commit()

        finally:
            conn.close()

    def remove_path(
        self,
        project_name: str,
        side: str,
        root_path,
        relative_path,
    ) -> None:
        root = str(Path(root_path))
        relative = Path(relative_path).as_posix()

        conn = self._connect()

        try:
            conn.execute(
                """
                DELETE FROM indexed_files
                WHERE project_name = ?
                  AND side = ?
                  AND root_path = ?
                  AND relative_path = ?
                """,
                (project_name, side, root, relative),
            )

            conn.commit()

        finally:
            conn.close()

    def get_paths(
        self,
        project_name: str,
        side: str,
        root_path,
    ) -> set[str]:
        root = str(Path(root_path))

        conn = self._connect()

        try:
            rows = conn.execute(
                """
                SELECT relative_path
                FROM indexed_files
                WHERE project_name = ?
                  AND side = ?
                  AND root_path = ?
                """,
                (project_name, side, root),
            ).fetchall()

        finally:
            conn.close()

        return {row[0] for row in rows}

    def get_usn_cursor(
        self,
        project_name: str,
        side: str,
        root_path,
    ):
        root = str(Path(root_path))

        conn = self._connect()

        try:
            return conn.execute(
                """
                SELECT volume_root, journal_id, next_usn
                FROM usn_journal_state
                WHERE project_name = ?
                  AND side = ?
                  AND root_path = ?
                """,
                (project_name, side, root),
            ).fetchone()

        finally:
            conn.close()

    def set_usn_cursor(
        self,
        project_name: str,
        side: str,
        root_path,
        volume_root: str,
        journal_id: int,
        next_usn: int,
    ) -> None:
        root = str(Path(root_path))
        now = time.time()

        conn = self._connect()

        try:
            conn.execute(
                """
                INSERT INTO usn_journal_state (
                    project_name,
                    side,
                    root_path,
                    volume_root,
                    journal_id,
                    next_usn,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (project_name, side, root_path)
                DO UPDATE SET
                    volume_root = excluded.volume_root,
                    journal_id = excluded.journal_id,
                    next_usn = excluded.next_usn,
                    updated_at = excluded.updated_at
                """,
                (
                    project_name,
                    side,
                    root,
                    volume_root,
                    journal_id,
                    next_usn,
                    now,
                ),
            )
            conn.commit()

        finally:
            conn.close()


def safe_update_index_snapshot(
    project_name: str,
    side: str,
    root_path,
    entries: Iterable[FileEntry],
) -> None:
    try:
        FileIndex().replace_snapshot(project_name, side, root_path, entries)
    except Exception:
        pass


def safe_update_index_entry(
    project_name: str,
    side: str,
    root_path,
    entry: FileEntry | None,
    relative_path,
) -> None:
    try:
        index = FileIndex()

        if entry is None:
            index.remove_path(project_name, side, root_path, relative_path)
        else:
            index.upsert_entry(project_name, side, root_path, entry)

    except Exception:
        pass


def get_usn_cursor(project_name, side, root_path):
    try:
        return FileIndex().get_usn_cursor(
            project_name,
            side,
            root_path,
        )
    except Exception:
        return None


def safe_set_usn_cursor(
    project_name,
    side,
    root_path,
    volume_root,
    journal_id,
    next_usn,
):
    try:
        FileIndex().set_usn_cursor(
            project_name,
            side,
            root_path,
            volume_root,
            journal_id,
            next_usn,
        )
    except Exception:
        pass
