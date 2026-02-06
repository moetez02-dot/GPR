import sqlite3

conn = sqlite3.connect("gpr.db")
conn.row_factory = sqlite3.Row

cols = [r["name"] for r in conn.execute("PRAGMA table_info(historique)").fetchall()]

if "role" not in cols:
    conn.execute("ALTER TABLE historique ADD COLUMN role TEXT DEFAULT 'SYSTEM'")
    print("✅ Colonne role ajoutée")
else:
    print("ℹ Colonne role déjà présente")

conn.commit()
conn.close()
