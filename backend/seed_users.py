import sqlite3
from werkzeug.security import generate_password_hash

users = [
    ("main", "MAINT", "main123"),
    ("log", "LOG", "log123"),
    ("achat", "ACHAT", "achat123"),
    ("inge", "INGE", "inge123")
]

conn = sqlite3.connect("gpr.db")
cur = conn.cursor()

for u, r, p in users:
    cur.execute("""
        INSERT OR IGNORE INTO users
        (username, role, password_hash)
        VALUES (?, ?, ?)
    """, (u, r, generate_password_hash(p)))

conn.commit()
conn.close()
print("Utilisateurs créés")
