import sqlite3
from datetime import datetime

DB_NAME = "announcements.db"

def init_announcements_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Main announcements table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_by_role TEXT NOT NULL,   -- 'admin' or 'teacher'
            created_at TEXT NOT NULL,        -- ISO string
            audience_role TEXT NOT NULL,     -- 'student', 'teacher', 'all'
            batch TEXT,                      -- e.g. 'M-22'
            department TEXT,
            section TEXT,
            course_code TEXT,                -- for teacher→class announcements
            type TEXT NOT NULL,              -- 'text' or 'assignment'
            due_at TEXT                      -- ISO string or NULL
        )
    """)

    # Attachments metadata (files can remain in static/uploads)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS announcement_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            announcement_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            url TEXT NOT NULL,
            mime_type TEXT,
            FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE
        )
    """)

    # Comments (discussion)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS announcement_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            announcement_id INTEGER NOT NULL,
            author_id TEXT NOT NULL,
            author_role TEXT NOT NULL,       -- 'student'/'teacher'/'admin'
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE
        )
    """)

    # Submissions (assignment turn‑in)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS announcement_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            announcement_id INTEGER NOT NULL,
            student_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            url TEXT NOT NULL,
            mime_type TEXT,
            submitted_at TEXT NOT NULL,
            FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print(f"{DB_NAME} initialized.")

if __name__ == "__main__":
    init_announcements_db()
