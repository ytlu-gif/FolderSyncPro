from pathlib import Path

from core.models import (
    ActionType,
    FileInfo,
    SyncAction,
)


class FolderComparer:
    """
    FolderSyncPro V2

    第一版比較器

    目前仍沿用 V1 的判斷方式

        1. 新增
        2. 更新
        3. 刪除候選

    下一版加入

        Hash
        Rename
        Conflict
    """

    def __init__(self, source: Path, target: Path):

        self.source = Path(source)
        self.target = Path(target)

    def compare(self):

        actions = []

        for src_file in self.source.rglob("*"):

            if not src_file.is_file():
                continue

            relative = src_file.relative_to(self.source)

            target_file = self.target / relative

            src_stat = src_file.stat()

            src_info = FileInfo(
                path=src_file,
                relative_path=relative,
                size=src_stat.st_size,
                mtime=src_stat.st_mtime,
            )

            # -----------------------------
            # ADD
            # -----------------------------

            if not target_file.exists():

                actions.append(
                    SyncAction(
                        action=ActionType.ADD,
                        source=src_info,
                        target=None,
                        reason="Target file does not exist",
                    )
                )

                continue

            tgt_stat = target_file.stat()

            tgt_info = FileInfo(
                path=target_file,
                relative_path=relative,
                size=tgt_stat.st_size,
                mtime=tgt_stat.st_mtime,
            )

            size_changed = (
                src_info.size != tgt_info.size
            )

            time_changed = (
                src_info.mtime > tgt_info.mtime
            )

            # -----------------------------
            # UPDATE
            # -----------------------------

            if size_changed or time_changed:

                actions.append(
                    SyncAction(
                        action=ActionType.UPDATE,
                        source=src_info,
                        target=tgt_info,
                        reason="Size or modified time changed",
                    )
                )

        # -----------------------------
        # DELETE candidates
        # -----------------------------

        for target_file in self.target.rglob("*"):

            if not target_file.is_file():
                continue

            relative = target_file.relative_to(self.target)

            source_file = self.source / relative

            if source_file.exists():
                continue

            tgt_stat = target_file.stat()

            tgt_info = FileInfo(
                path=target_file,
                relative_path=relative,
                size=tgt_stat.st_size,
                mtime=tgt_stat.st_mtime,
            )

            actions.append(
                SyncAction(
                    action=ActionType.DELETE,
                    source=tgt_info,
                    target=tgt_info,
                    reason="Source file does not exist",
                )
            )

        return actions
