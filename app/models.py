import sqlite3

def init_db():
    conn = sqlite3.connect('paydod.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS shipments (
            id TEXT PRIMARY KEY,
            client_name TEXT,
            amount REAL,
            status TEXT,
            tracking_code TEXT
        )
    ''')
    conn.commit()
    conn.close()
