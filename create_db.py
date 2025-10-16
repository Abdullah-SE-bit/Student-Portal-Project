import sqlite3

def init_db():
    conn = sqlite3.connect('flake.db')
    cur = conn.cursor()
    
    # Create tables if not exist
    cur.execute('''CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL)''')
    
    # Add one default record for testing (only if not exists)
    cur.execute("INSERT OR IGNORE INTO teachers (teacher_id, password) VALUES (?, ?)", ("T123", "pass123"))
    cur.execute("INSERT OR IGNORE INTO students (student_id, password) VALUES (?, ?)", ("S123", "pass123"))
    cur.execute("INSERT OR IGNORE INTO admins (admin_id, password) VALUES (?, ?)", ("A123", "admin123"))
    
    conn.commit()
    conn.close()

# Initialize DB at start
init_db()
