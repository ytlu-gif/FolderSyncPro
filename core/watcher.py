import threading
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from core.sync_engine import sync_folder


class SyncEventHandler(FileSystemEventHandler):

    def __init__(
        self,
        source_path,
        target_path,
        log_func=None,
        mode="backup",
        project_name="未命名專案",
        sync_lock=None,
        debounce_seconds=1.0,
        result_func=None
    ):

        self.source_path = source_path
        self.target_path = target_path
        self.log_func = log_func
        self.mode = mode
        self.project_name = project_name
        self.result_func = result_func

        # 雙向同步時，來源、目的兩邊各自的 Observer 會共用同一把鎖，
        # 避免「同步寫入目的」又觸發「目的的監控事件」而互相連環觸發
        self.sync_lock = sync_lock or threading.Lock()
        self.debounce_seconds = debounce_seconds
        self._last_sync_time = 0

    def on_any_event(self, event):

        if event.is_directory:
            return

        now = time.time()

        # 短時間內的重複事件（例如複製大量檔案時）先擋掉，
        # 避免同一批變動觸發好幾次完整掃描
        if now - self._last_sync_time < self.debounce_seconds:
            return

        if not self.sync_lock.acquire(blocking=False):
            # 已經有一次同步在跑，這次事件先跳過即可，
            # 因為進行中的那次同步本來就會把最新狀態一起處理掉
            return

        try:

            self._last_sync_time = time.time()

            result = sync_folder(
                self.source_path,
                self.target_path,
                self.log_func,
                mode=self.mode,
                project_name=self.project_name
            )

            if self.log_func:

                self.log_func(
                    f"[監控同步] {event.src_path}"
                )

            if self.result_func:

                self.result_func(result)

        except Exception as e:

            if self.log_func:

                self.log_func(
                    f"[監控錯誤] {e}"
                )

        finally:

            self.sync_lock.release()


class FolderWatcher:

    def __init__(
        self,
        source_path,
        target_path,
        log_func=None,
        mode="backup",
        project_name="未命名專案",
        result_func=None
    ):

        self.source_path = source_path
        self.target_path = target_path
        self.log_func = log_func
        self.mode = mode
        self.project_name = project_name
        self.result_func = result_func

        self.observer = Observer()

        self._sync_lock = threading.Lock()

    def start(self):

        handler = SyncEventHandler(
            self.source_path,
            self.target_path,
            self.log_func,
            mode=self.mode,
            project_name=self.project_name,
            sync_lock=self._sync_lock,
            result_func=self.result_func
        )

        self.observer.schedule(
            handler,
            self.source_path,
            recursive=True
        )

        # 雙向同步時，目的資料夾的變動也必須能觸發同步，
        # 否則「目的 -> 來源」這個方向只能靠手動按「開始同步」
        if self.mode == "two_way":

            self.observer.schedule(
                handler,
                self.target_path,
                recursive=True
            )

        self.observer.start()

        if self.log_func:

            self.log_func(
                "即時監控已啟動"
            )

    def stop(self):

        self.observer.stop()
        self.observer.join()

        if self.log_func:

            self.log_func(
                "即時監控已停止"
            )
