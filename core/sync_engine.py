import json
from pathlib import Path
import shutil

from core.file_index import (
    safe_update_index_entry,
    safe_update_index_snapshot,
)
from core.file_scanner import get_file_entry, iter_sync_files
from core.recycle_manager import move_to_recycle_bin
from database.project_manager import add_sync_log


# ==========================
# 雙向同步狀態記錄
# ==========================
#
# 單向同步(backup / mirror)只需要比較來源、目的「現況」就能判斷該怎麼做。
#
# 雙向同步不行:如果一個檔案只存在於其中一邊，光看現況無法分辨究竟是
# 「另一邊新增了檔案，該同步過去」，還是「另一邊刪除了檔案，這邊也該跟著刪」。
# 兩種情況現況完全一樣，差別只在於「這個檔案以前有沒有被同步過」。
#
# 所以雙向同步需要一份「上次同步完成後，兩邊共同狀態」的記錄檔，
# 用來判斷檔案是新增還是刪除。

STATE_DIR = Path("data") / "sync_state"


def _state_file_path(project_name):

    STATE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    safe_name = "".join(
        c if c.isalnum() or c in ("-", "_") else "_"
        for c in project_name
    )

    return STATE_DIR / f"{safe_name}.json"


def _load_state(project_name):

    path = _state_file_path(project_name)

    if not path.exists():
        return {}

    try:

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:

        return {}


def _save_state(project_name, state):

    path = _state_file_path(project_name)

    with open(path, "w", encoding="utf-8") as f:

        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2
        )


def safe_copy(
    src_file,
    target_file,
    log_func=None
):
    """
    安全複製
    避免 WinError 32
    """

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


def _soft_delete(
    file_path,
    log_func=None
):
    """
    刪除一律先移入回收桶，不直接刪除實體檔案
    """

    try:

        move_to_recycle_bin(
            file_path
        )

        return True

    except Exception as e:

        if log_func:

            log_func(
                f"[回收桶失敗] {file_path.name} : {e}"
            )

        return False


def sync_folder(
    source_path,
    target_path,
    log_func=None,
    mode="backup",
    project_name="未命名專案",
    progress_func=None,
    cancel_func=None,
    changed_paths=None
):
    """
    backup 模式
        新增
        更新

    mirror 模式
        新增
        更新
        刪除(移入回收桶)

    two_way 模式（雙向同步）
        新增（來源 -> 目的、目的 -> 來源皆可）
        更新／衝突（兩邊都被改過時，以「較新的修改時間」為準覆蓋較舊的一邊）
        刪除（任一邊刪除，另一邊也移入回收桶，不做真正的硬刪除）

    progress_func(done, total, relative_path)
        每處理完一個檔案就呼叫一次，用來讓呼叫端（例如 GUI）更新進度條。
        可傳 None，代表不需要進度回報。
    """

    if mode == "two_way":

        return sync_folder_two_way(
            source_path,
            target_path,
            log_func=log_func,
            project_name=project_name,
            progress_func=progress_func,
            cancel_func=cancel_func,
            changed_paths=changed_paths
        )

    source = Path(source_path)
    target = Path(target_path)

    if not source.exists():

        raise FileNotFoundError(
            f"來源不存在：{source}"
        )

    target.mkdir(
        parents=True,
        exist_ok=True
    )

    copied = 0
    updated = 0
    deleted = 0

    def is_cancelled():
        return bool(cancel_func and cancel_func())

    def build_result(cancelled=False):
        return {

            "copied": copied,

            "updated": updated,

            "deleted": deleted,

            "cancelled": cancelled
        }

    changed_keys = _normalize_changed_paths(changed_paths)

    if changed_keys is None:

        # 先掃過一次，算出總檔案數，進度條才有分母可以算百分比
        source_files = list(
            iter_sync_files(
                source,
                cancel_func=is_cancelled
            )
        )

    else:

        source_files = [
            entry
            for relative in changed_keys
            if (
                entry := get_file_entry(source, relative)
            ) is not None
        ]

    if is_cancelled():

        if log_func:
            log_func("[停止] 同步已停止")

        return build_result(cancelled=True)

    mirror_delete_candidates = []

    if mode == "mirror":

        if changed_keys is None:

            mirror_delete_candidates = list(
                iter_sync_files(
                    target,
                    cancel_func=is_cancelled
                )
            )

        else:

            mirror_delete_candidates = [
                entry
                for relative in changed_keys
                if (
                    entry := get_file_entry(target, relative)
                ) is not None
            ]

        if is_cancelled():

            if log_func:
                log_func("[停止] 同步已停止")

            return build_result(cancelled=True)

    total_steps = (
        len(source_files)
        + len(mirror_delete_candidates)
    )

    done_steps = 0
    source_keys = {
        entry.relative_path.as_posix()
        for entry in source_files
    }
    target_entries = {
        entry.relative_path.as_posix(): entry
        for entry in mirror_delete_candidates
    }

    if changed_keys is None:
        safe_update_index_snapshot(
            project_name,
            "source",
            source,
            source_files,
        )

        if mode == "mirror":
            safe_update_index_snapshot(
                project_name,
                "target",
                target,
                mirror_delete_candidates,
            )

    def report(relative):

        nonlocal done_steps

        done_steps += 1

        if progress_func:

            progress_func(
                done_steps,
                max(total_steps, 1),
                str(relative)
            )

    # ==========================
    # 新增與更新
    # ==========================

    for src_entry in source_files:

        if is_cancelled():

            if log_func:
                log_func("[停止] 同步已停止")

            return build_result(cancelled=True)

        src_file = src_entry.path
        relative = src_entry.relative_path
        relative_key = relative.as_posix()

        target_file = target / relative
        target_entry = target_entries.get(relative_key)

        # --------------------------
        # 新增
        # --------------------------

        if mode == "mirror":
            target_exists = target_entry is not None
        else:
            target_exists = target_file.exists()

        if not target_exists:

            if safe_copy(
                src_file,
                target_file,
                log_func
            ):

                copied += 1

                if log_func:

                    log_func(
                        f"[新增] {relative}"
                    )

                add_sync_log(
                    project_name,
                    "ADD",
                    str(relative)
                )

        # --------------------------
        # 更新
        # --------------------------

        else:

            if target_entry:
                target_size = target_entry.size
                target_mtime = target_entry.mtime
            else:
                tgt_stat = target_file.stat()
                target_size = tgt_stat.st_size
                target_mtime = tgt_stat.st_mtime

            size_changed = (
                src_entry.size
                != target_size
            )

            time_changed = (
                src_entry.mtime
                > target_mtime
            )

            if size_changed or time_changed:

                if safe_copy(
                    src_file,
                    target_file,
                    log_func
                ):

                    updated += 1

                    if log_func:

                        log_func(
                            f"[更新] {relative}"
                        )

                    add_sync_log(
                        project_name,
                        "UPDATE",
                        str(relative)
                    )

        report(relative)

        if changed_keys is not None:
            safe_update_index_entry(
                project_name,
                "source",
                source,
                src_entry,
                relative,
            )

            safe_update_index_entry(
                project_name,
                "target",
                target,
                get_file_entry(target, relative),
                relative,
            )

    # ==========================
    # 鏡像模式刪除
    # ==========================

    if mode == "mirror":

        if changed_keys is not None:

            for relative_key in changed_keys:

                if relative_key in source_keys:
                    continue

                relative = Path(relative_key)
                target_entry = get_file_entry(target, relative)

                if target_entry is None:
                    safe_update_index_entry(
                        project_name,
                        "source",
                        source,
                        None,
                        relative,
                    )
                    safe_update_index_entry(
                        project_name,
                        "target",
                        target,
                        None,
                        relative,
                    )
                    continue

                if relative_key in target_entries:
                    continue

                mirror_delete_candidates.append(target_entry)
                target_entries[relative_key] = target_entry

        for target_entry in mirror_delete_candidates:

            if is_cancelled():

                if log_func:
                    log_func("[停止] 同步已停止")

                return build_result(cancelled=True)

            target_file = target_entry.path
            relative = target_entry.relative_path

            source_file = source / relative

            if relative.as_posix() not in source_keys:

                if _soft_delete(
                    target_file,
                    log_func
                ):

                    deleted += 1

                    if log_func:

                        log_func(
                            f"[回收桶] {relative}"
                        )

                    add_sync_log(
                        project_name,
                        "DELETE",
                        str(relative)
                    )

                if changed_keys is not None:
                    safe_update_index_entry(
                        project_name,
                        "source",
                        source,
                        None,
                        relative,
                    )
                    safe_update_index_entry(
                        project_name,
                        "target",
                        target,
                        None,
                        relative,
                    )

            report(relative)

    return build_result()


def sync_folder_two_way(
    source_path,
    target_path,
    log_func=None,
    project_name="未命名專案",
    progress_func=None,
    cancel_func=None,
    changed_paths=None
):
    """
    雙向同步

    對每個檔案(以相對路徑為 key)，分成三種狀況：

    1. 兩邊都有
        - 內容一樣（size、mtime 相同） -> 不動作
        - 內容不同（衝突）             -> 以「較新的修改時間」為準，覆蓋較舊的一邊

    2. 只有一邊有
        - 這個相對路徑「從未同步過」    -> 視為新增，複製到另一邊
        - 這個相對路徑「上次同步時兩邊都有」-> 代表對面把它刪了，
          這邊也跟著刪除（移入回收桶，不做硬刪除）

    3. 兩邊都沒有，但狀態記錄還留著
        -> 代表兩邊都已刪除過了，僅將它從狀態記錄中移除
    """

    source = Path(source_path)
    target = Path(target_path)

    if not source.exists():

        raise FileNotFoundError(
            f"來源不存在：{source}"
        )

    if not target.exists():

        raise FileNotFoundError(
            f"目的不存在：{target}"
        )

    copied_to_target = 0
    copied_to_source = 0
    updated = 0
    conflicts = 0
    deleted = 0

    def is_cancelled():
        return bool(cancel_func and cancel_func())

    def build_result(cancelled=False):
        return {

            "copied": copied_to_target + copied_to_source,

            "copied_to_target": copied_to_target,

            "copied_to_source": copied_to_source,

            "updated": updated,

            "conflicts": conflicts,

            "deleted": deleted,

            "cancelled": cancelled
        }

    state = _load_state(project_name)
    changed_keys = _normalize_changed_paths(changed_paths)
    new_state = dict(state) if changed_keys is not None else {}

    if changed_keys is None:

        source_files = {
            entry.relative_path.as_posix(): entry
            for entry in iter_sync_files(
                source,
                cancel_func=is_cancelled
            )
        }

    else:

        source_files = {
            relative: entry
            for relative in changed_keys
            if (
                entry := get_file_entry(source, relative)
            ) is not None
        }

    if is_cancelled():

        if log_func:
            log_func("[停止] 同步已停止")

        return build_result(cancelled=True)

    if changed_keys is None:

        target_files = {
            entry.relative_path.as_posix(): entry
            for entry in iter_sync_files(
                target,
                cancel_func=is_cancelled
            )
        }

    else:

        target_files = {
            relative: entry
            for relative in changed_keys
            if (
                entry := get_file_entry(target, relative)
            ) is not None
        }

    if is_cancelled():

        if log_func:
            log_func("[停止] 同步已停止")

        return build_result(cancelled=True)

    if changed_keys is None:

        all_relatives = (
            set(source_files)
            | set(target_files)
            | set(state)
        )

        safe_update_index_snapshot(
            project_name,
            "source",
            source,
            source_files.values(),
        )
        safe_update_index_snapshot(
            project_name,
            "target",
            target,
            target_files.values(),
        )

    else:

        all_relatives = changed_keys

    total_steps = max(len(all_relatives), 1)
    done_steps = 0

    for relative in sorted(all_relatives):

        if is_cancelled():

            if log_func:
                log_func("[停止] 同步已停止")

            return build_result(cancelled=True)

        done_steps += 1

        if progress_func:

            progress_func(
                done_steps,
                total_steps,
                relative
            )

        src_entry = source_files.get(relative)
        tgt_entry = target_files.get(relative)
        was_synced = relative in state

        # --------------------------
        # 兩邊都有
        # --------------------------

        if src_entry and tgt_entry:

            same_content = (
                src_entry.size == tgt_entry.size
                and abs(src_entry.mtime - tgt_entry.mtime) < 1
            )

            if same_content:

                new_state[relative] = {
                    "size": src_entry.size,
                    "mtime": max(
                        src_entry.mtime,
                        tgt_entry.mtime
                    )
                }

                continue

            # 內容不同 -> 衝突，較新的一邊覆蓋較舊的一邊

            src_file = src_entry.path
            tgt_file = tgt_entry.path

            if src_entry.mtime >= tgt_entry.mtime:

                if safe_copy(src_file, tgt_file, log_func):

                    updated += 1
                    conflicts += 1

                    if log_func:

                        log_func(
                            f"[衝突/以來源較新為準] {relative}"
                        )

                    add_sync_log(
                        project_name,
                        "CONFLICT_SOURCE_WINS",
                        relative
                    )

                stat_after = src_file.stat()

            else:

                if safe_copy(tgt_file, src_file, log_func):

                    updated += 1
                    conflicts += 1

                    if log_func:

                        log_func(
                            f"[衝突/以目的較新為準] {relative}"
                        )

                    add_sync_log(
                        project_name,
                        "CONFLICT_TARGET_WINS",
                        relative
                    )

                stat_after = tgt_file.stat()

            new_state[relative] = {
                "size": stat_after.st_size,
                "mtime": stat_after.st_mtime
            }

        # --------------------------
        # 只有來源有
        # --------------------------

        elif src_entry and not tgt_entry:

            if was_synced:

                # 目的那邊刪除過 -> 來源這邊也跟著移入回收桶

                if _soft_delete(src_entry.path, log_func):

                    deleted += 1

                    if log_func:

                        log_func(
                            f"[回收桶/來源] {relative}"
                        )

                    add_sync_log(
                        project_name,
                        "DELETE_SOURCE",
                        relative
                    )

                # 已刪除，不寫回 new_state
                new_state.pop(relative, None)

            else:

                src_file = src_entry.path
                target_file = target / relative

                if safe_copy(src_file, target_file, log_func):

                    copied_to_target += 1

                    if log_func:

                        log_func(
                            f"[新增至目的] {relative}"
                        )

                    add_sync_log(
                        project_name,
                        "ADD_TO_TARGET",
                        relative
                    )

                    stat_after = src_file.stat()

                    new_state[relative] = {
                        "size": stat_after.st_size,
                        "mtime": stat_after.st_mtime
                    }

        # --------------------------
        # 只有目的有
        # --------------------------

        elif tgt_entry and not src_entry:

            if was_synced:

                # 來源那邊刪除過 -> 目的這邊也跟著移入回收桶

                if _soft_delete(tgt_entry.path, log_func):

                    deleted += 1

                    if log_func:

                        log_func(
                            f"[回收桶/目的] {relative}"
                        )

                    add_sync_log(
                        project_name,
                        "DELETE_TARGET",
                        relative
                    )

                new_state.pop(relative, None)

            else:

                source_file = source / relative

                tgt_file = tgt_entry.path

                if safe_copy(tgt_file, source_file, log_func):

                    copied_to_source += 1

                    if log_func:

                        log_func(
                            f"[新增至來源] {relative}"
                        )

                    add_sync_log(
                        project_name,
                        "ADD_TO_SOURCE",
                        relative
                    )

                    stat_after = tgt_file.stat()

                    new_state[relative] = {
                        "size": stat_after.st_size,
                        "mtime": stat_after.st_mtime
                    }

        # 兩邊都沒有、但狀態記錄還留著 -> 兩邊早就都刪完了，
        # 不寫回 new_state 即等於把它從記錄中移除，不需要額外動作
        else:

            new_state.pop(relative, None)

    _save_state(project_name, new_state)

    if changed_keys is not None:

        for relative in changed_keys:
            safe_update_index_entry(
                project_name,
                "source",
                source,
                get_file_entry(source, relative),
                relative,
            )
            safe_update_index_entry(
                project_name,
                "target",
                target,
                get_file_entry(target, relative),
                relative,
            )

    return build_result()


def _normalize_changed_paths(changed_paths):
    if changed_paths is None:
        return None

    return {
        Path(path).as_posix()
        for path in changed_paths
        if str(path)
    }
