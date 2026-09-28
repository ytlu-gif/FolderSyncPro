import json
from pathlib import Path
import shutil

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
    cancel_func=None
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
            cancel_func=cancel_func
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

    # 先掃過一次，算出總檔案數，進度條才有分母可以算百分比
    source_files = [
        f for f in source.rglob("*")
        if f.is_file()
    ]

    mirror_delete_candidates = []

    if mode == "mirror":

        mirror_delete_candidates = [
            f for f in target.rglob("*")
            if f.is_file()
        ]

    total_steps = (
        len(source_files)
        + len(mirror_delete_candidates)
    )

    done_steps = 0

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

    for src_file in source_files:

        if is_cancelled():

            if log_func:
                log_func("[停止] 同步已停止")

            return build_result(cancelled=True)

        relative = src_file.relative_to(source)

        target_file = target / relative

        # --------------------------
        # 新增
        # --------------------------

        if not target_file.exists():

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

            src_stat = src_file.stat()
            tgt_stat = target_file.stat()

            size_changed = (
                src_stat.st_size
                != tgt_stat.st_size
            )

            time_changed = (
                src_stat.st_mtime
                > tgt_stat.st_mtime
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

    # ==========================
    # 鏡像模式刪除
    # ==========================

    if mode == "mirror":

        for target_file in mirror_delete_candidates:

            if is_cancelled():

                if log_func:
                    log_func("[停止] 同步已停止")

                return build_result(cancelled=True)

            relative = target_file.relative_to(target)

            source_file = source / relative

            if not source_file.exists():

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

            report(relative)

    return build_result()


def sync_folder_two_way(
    source_path,
    target_path,
    log_func=None,
    project_name="未命名專案",
    progress_func=None,
    cancel_func=None
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

    state = _load_state(project_name)

    source_files = {
        f.relative_to(source).as_posix(): f
        for f in source.rglob("*")
        if f.is_file()
    }

    target_files = {
        f.relative_to(target).as_posix(): f
        for f in target.rglob("*")
        if f.is_file()
    }

    all_relatives = (
        set(source_files)
        | set(target_files)
        | set(state)
    )

    copied_to_target = 0
    copied_to_source = 0
    updated = 0
    conflicts = 0
    deleted = 0

    new_state = {}

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

        src_file = source_files.get(relative)
        tgt_file = target_files.get(relative)
        was_synced = relative in state

        # --------------------------
        # 兩邊都有
        # --------------------------

        if src_file and tgt_file:

            src_stat = src_file.stat()
            tgt_stat = tgt_file.stat()

            same_content = (
                src_stat.st_size == tgt_stat.st_size
                and abs(src_stat.st_mtime - tgt_stat.st_mtime) < 1
            )

            if same_content:

                new_state[relative] = {
                    "size": src_stat.st_size,
                    "mtime": max(
                        src_stat.st_mtime,
                        tgt_stat.st_mtime
                    )
                }

                continue

            # 內容不同 -> 衝突，較新的一邊覆蓋較舊的一邊

            if src_stat.st_mtime >= tgt_stat.st_mtime:

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

        elif src_file and not tgt_file:

            if was_synced:

                # 目的那邊刪除過 -> 來源這邊也跟著移入回收桶

                if _soft_delete(src_file, log_func):

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

            else:

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

        elif tgt_file and not src_file:

            if was_synced:

                # 來源那邊刪除過 -> 目的這邊也跟著移入回收桶

                if _soft_delete(tgt_file, log_func):

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

            else:

                source_file = source / relative

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

    _save_state(project_name, new_state)

    return build_result()
