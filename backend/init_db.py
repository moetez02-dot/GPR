import sqlite3

conn = sqlite3.connect("gpr.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    role TEXT,
    password_hash TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS piece (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    identifiant TEXT UNIQUE,
    type_piece TEXT,
    statut TEXT,
    localisation TEXT,
    date_entree TEXT,
    origine TEXT,
    qr_filename TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS historique (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    piece_id INTEGER,
    action TEXT,
    date_action TEXT,
    role TEXT,
    commentaire TEXT
)
""")

conn.commit()
conn.close()
print("DB prête")
