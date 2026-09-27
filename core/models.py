from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional


# ======================================
# 同步模式
# ======================================

class SyncMode(Enum):
    BACKUP = auto()
    MIRROR = auto()
    BIDIRECTIONAL = auto()


# ======================================
# 動作種類
# ======================================

class ActionType(Enum):
    ADD = auto()
    UPDATE = auto()
    DELETE = auto()
    CONFLICT = auto()
    RENAME = auto()
    SKIP = auto()


# ======================================
# 檔案資訊
# ======================================

@dataclass(slots=True)
class FileInfo:

    path: Path
    relative_path: Path
    size: int
    mtime: float

    hash: Optional[str] = None


# ======================================
# 同步動作
# ======================================

@dataclass(slots=True)
class SyncAction:

    action: ActionType

    source: FileInfo

    target: Optional[FileInfo] = None

    reason: str = ""

    resolved: bool = False


# ======================================
# 執行結果
# ======================================

@dataclass(slots=True)
class SyncResult:

    copied: int = 0

    updated: int = 0

    deleted: int = 0

    skipped: int = 0

    conflicts: int = 0

    errors: list[str] = field(default_factory=list)