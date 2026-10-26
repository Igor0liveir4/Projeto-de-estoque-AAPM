import sqlite3

conn = sqlite3.connect('banco.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
rows = cur.fetchall()
print([r[0] for r in rows])
conn.close()
