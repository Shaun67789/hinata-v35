import sqlite3
import time

conn = sqlite3.connect(':memory:')
c = conn.cursor()
c.execute('CREATE TABLE t (id INTEGER, created_at TEXT)')
now = time.strftime('%Y-%m-%d %H:%M:%S')
c.execute('INSERT INTO t VALUES (1, ?)', (now,))

c.execute("SELECT ? < datetime('now', '-1 day')", (now,))
print('Using datetime("now"):', c.fetchone()[0])

c.execute("SELECT ? < datetime('now', 'localtime', '-1 day')", (now,))
print('Using datetime("now", "localtime"):', c.fetchone()[0])

c.execute("SELECT datetime('now')")
print('UTC now:', c.fetchone()[0])
print('Local now:', now)
