import sqlite3

conn = sqlite3.connect('flake.db')
cur = conn.cursor()

cur.execute("PRAGMA table_info(teachers)")
for col in cur.fetchall():
    print(col)

conn.close()
