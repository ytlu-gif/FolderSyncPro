from pathlib import Path
import shutil

from core.models import ActionType, SyncResult
from core.recycle_manager import move_to_recycle_bin
from database.project_manager import add_sync_log


def safe_copy(
    src_file,
    target_file,
    log_func=None
):
    """
    安全複製
    避免 WinError 32
    """

    src_file = Path(src_file)
    target_file = Path(target_file)

    try:

        target_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            src_file,
            target_file
        )

        return True

    except PermissionError:

        if log_func:

            log_func(
                f"[跳過] 檔案被占用：{src_file.name}"
            )

        return False

    except Exception as e:

        if log_func:

            log_func(
                f"[錯誤] {src_file.name} : {e}"
            )

        return False


class SyncExecutor:
    """
    執行 Resolver 決定好的 SyncAction。

    Executor 是唯一真正碰檔案系統的 V2 模組：

        ADD / UPDATE -> copy2
        DELETE       -> recycle bin

    目前回傳 dict，以維持 GUI 對 sync_folder() 的既有期待格式。
    """

    def __init__(
        self,
        project_name="未命名專案",
        log_func=None,
        target_root=None
    ):

        self.project_name = project_name
        self.log_func = log_func
        self.target_root = (
            Path(target_root)
            if target_root is not None
            else None
        )

    def execute(self, actions):

        result = SyncResult()

        for action in actions:

            if action.action == ActionType.ADD:
                self._copy_action(
                    action,
                    result,
                    log_label="新增",
                    db_action="ADD",
                    counter="copied"
                )

            elif action.action == ActionType.UPDATE:
                self._copy_action(
                    action,
                    result,
                    log_label="更新",
                    db_action="UPDATE",
                    counter="updated"
                )

            elif action.action == ActionType.DELETE:
                self._delete_action(
                    action,
                    result
                )

            elif action.action == ActionType.CONFLICT:
                result.conflicts += 1
                self._log(
                    f"[衝突] {action.source.relative_path}"
                )

            else:
                result.skipped += 1
                self._log(
                    f"[略過] {action.source.relative_path}"
                )

        return self._to_legacy_dict(result)

    def _copy_action(
        self,
        action,
        result,
        log_label,
        db_action,
        counter
    ):

        source_file = action.source.path
        target_file = self._resolve_target_path(action)

        if target_file is None:

            message = (
                f"無法決定目的路徑："
                f"{action.source.relative_path}"
            )

            result.errors.append(message)
            self._log(f"[錯誤] {message}")

            return

        if safe_copy(
            source_file,
            target_file,
            self.log_func
        ):

            current_count = getattr(
                result,
                counter
            )

            setattr(
                result,
                counter,
                current_count + 1
            )

            self._log(
                f"[{log_label}] {action.source.relative_path}"
            )

            add_sync_log(
                self.project_name,
                db_action,
                str(action.source.relative_path)
            )

    def _delete_action(
        self,
        action,
        result
    ):

        target_file = self._resolve_delete_path(action)

        if target_file is None:

            message = (
                f"無法決定刪除路徑："
                f"{action.source.relative_path}"
            )

            result.errors.append(message)
            self._log(f"[回收桶失敗] {message}")

            return

        try:

            move_to_recycle_bin(
                target_file
            )

            result.deleted += 1

            relative = self._relative_label(
                action,
                target_file
            )

            self._log(
                f"[回收桶] {relative}"
            )

            add_sync_log(
                self.project_name,
                "DELETE",
                str(relative)
            )

        except Exception as e:

            result.errors.append(str(e))
            self._log(
                f"[回收桶失敗] {e}"
            )

    def _resolve_target_path(self, action):

        if action.target is not None:
            return action.target.path

        if self.target_root is None:
            return None

        return (
            self.target_root
            / action.source.relative_path
        )

    def _resolve_delete_path(self, action):

        if action.target is not None:
            return action.target.path

        if self.target_root is None:
            return action.source.path

        return (
            self.target_root
            / action.source.relative_path
        )

    def _relative_label(
        self,
        action,
        target_file
    ):

        if action.target is not None:
            return action.target.relative_path

        if self.target_root is not None:

            try:
                return Path(target_file).relative_to(
                    self.target_root
                )

            except ValueError:
                pass

        return action.source.relative_path

    def _log(self, message):

        if self.log_func:
            self.log_func(message)

    def _to_legacy_dict(self, result):

        return {
            "copied": result.copied,
            "updated": result.updated,
            "deleted": result.deleted,
            "skipped": result.skipped,
            "conflicts": result.conflicts,
            "errors": result.errors,
        }
