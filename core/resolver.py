from core.models import ActionType, SyncAction, SyncMode


class SyncResolver:
    """
    決定哪些 SyncAction 應該執行。

    Resolver 不碰檔案。

    Resolver 不做 Copy。

    它只決定：

        執行

        忽略

        衝突（下一版）
    """

    def __init__(self, mode="backup"):

        if isinstance(mode, str):
            mode = mode.upper()

            if mode == "BACKUP":
                self.mode = SyncMode.BACKUP

            elif mode == "MIRROR":
                self.mode = SyncMode.MIRROR

            elif mode == "BIDIRECTIONAL":
                self.mode = SyncMode.BIDIRECTIONAL

            else:
                self.mode = SyncMode.BACKUP

        else:
            self.mode = mode

    def resolve(self, actions):

        resolved = []

        for action in actions:

            if action.action == ActionType.ADD:
                resolved.append(action)

            elif action.action == ActionType.UPDATE:
                resolved.append(action)

            elif action.action == ActionType.DELETE:

                if self.mode == SyncMode.MIRROR:
                    resolved.append(action)

            else:

                resolved.append(action)

        return resolved