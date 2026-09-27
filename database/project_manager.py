import sqlite3
from pathlib import Path

DB_FILE = Path("data") / "sync.db"


def get_connection():
    return sqlite3.connect(DB_FILE)


def add_project(
    project_name,
    source_path,
    target_path,
    auto_watch=0
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO projects(
            project_name,
            source_path,
            target_path,
            auto_watch
        )
        VALUES(?,?,?,?)
    """, (
        project_name,
        source_path,
        target_path,
        auto_watch
    ))

    conn.commit()
    conn.close()


def get_projects():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            project_name,
            source_path,
            target_path,
            auto_watch
        FROM projects
        ORDER BY id
    """)

    rows = cur.fetchall()

    conn.close()

    return rows

def update_project(
    project_id,
    source_path,
    target_path,
    auto_watch
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE projects
        SET
            source_path = ?,
            target_path = ?,
            auto_watch = ?
        WHERE id = ?
    """, (
        source_path,
        target_path,
        auto_watch,
        project_id
    ))

    conn.commit()
    conn.close()

def delete_project(project_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM projects
        WHERE id = ?
    """, (project_id,))

    conn.commit()
    conn.close()


def add_sync_log(
    project_name,
    action,
    file_path,
    status="SUCCESS"
):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO sync_log(
            project_name,
            action,
            file_path,
            status
        )
        VALUES(?,?,?,?)
    """, (
        project_name,
        action,
        file_path,
        status
    ))

    conn.commit()
    conn.close()
    
def get_sync_logs(limit=100):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute("""
        SELECT
            sync_time,
            project_name,
            action,
            file_path,
            status
        FROM sync_log
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()

    conn.close()

    return rows
    