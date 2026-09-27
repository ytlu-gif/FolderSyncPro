"""
FolderSyncPro
Main Entry Point

Author: 盧裕倉
"""

import sys
from pathlib import Path

# 專案根目錄
BASE_DIR = Path(__file__).resolve().parent

# 加入模組路徑
sys.path.append(str(BASE_DIR))

from gui.dashboard import DashboardApp
from database.db import initialize_database
from database.project_manager import add_project


def startup():
    """
    系統啟動流程
    """

    print("=" * 60)
    print("FolderSyncPro 啟動中...")
    print("=" * 60)

    # 初始化資料庫
    initialize_database()

    # 建立測試專案（避免重覆新增造成錯誤）
    try:
        add_project(
            "測試專案",
            r"D:\Research",
            r"E:\Backup"
        )
    except Exception:
        pass

    # 啟動 GUI
    app = DashboardApp()
    app.mainloop()


if __name__ == "__main__":
    startup()