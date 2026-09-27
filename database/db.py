import sqlite3
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

DB_FILE = DATA_DIR / "sync.db"


def initialize_database():

    conn = sqlite3.connect(DB_FILE)

    cur = conn.cursor()

    # ==========================
    # 專案資料表
    # ==========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT UNIQUE,
            source_path TEXT,
            target_path TEXT,
            auto_watch INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ==========================
    # 同步歷史紀錄
    # ==========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sync_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            action TEXT,
            file_path TEXT,
            status TEXT,
            sync_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ==========================
    # 升級舊版資料庫
    # ==========================

    try:

        cur.execute("""
            ALTER TABLE projects
            ADD COLUMN auto_watch INTEGER DEFAULT 0
        """)

        print("auto_watch 欄位已新增")

    except Exception:
        pass

    conn.commit()
    conn.close()

    print("SQLite 初始化完成")