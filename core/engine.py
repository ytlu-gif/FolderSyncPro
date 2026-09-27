from pathlib import Path

from core.comparer import FolderComparer
from core.executor import SyncExecutor
from core.resolver import SyncResolver


class SyncEngine:
    """
    FolderSyncPro V2

    第一版 Engine

    功能仍與 V1 相同
    只是把流程拆成四個模組
    """

    def __init__(
        self,
        source_path,
        target_path,
        mode="backup",
        project_name="未命名專案",
        log_func=None,
    ):

        self.source = Path(source_path)
        self.target = Path(target_path)

        self.mode = mode
        self.project_name = project_name
        self.log_func = log_func

    def sync(self):

        comparer = FolderComparer(
            self.source,
            self.target
        )

        actions = comparer.compare()

        resolver = SyncResolver(
            mode=self.mode
        )

        actions = resolver.resolve(actions)

        executor = SyncExecutor(
            project_name=self.project_name,
            log_func=self.log_func,
            target_root=self.target
        )

        return executor.execute(actions)
