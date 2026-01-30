from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash
import sqlite3, os, qrcode

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")
DB_PATH = os.path.join(BASE_DIR, "gpr.db")
QR_DIR = os.path.join(BASE_DIR, "qr")
os.makedirs(QR_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "DEV_ONLY_CHANGE_ME"

# ---------- DB ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_schema():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS piece(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifiant TEXT UNIQUE NOT NULL,
        type_piece TEXT,
        statut TEXT,
        localisation TEXT,
        date_entree TEXT,
        origine TEXT,
        qr_filename TEXT,
        taux_endommagement INTEGER,
        commentaire TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS historique(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        piece_id INTEGER,
        action TEXT,
        date_action TEXT,
        role TEXT,
        commentaire TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        role TEXT
    )
    """)

    conn.commit()
    conn.close()

ensure_schema()

def log_action(piece_id, action, commentaire=""):
    conn = get_db()
    conn.execute("""
        INSERT INTO historique(piece_id, action, date_action, role, commentaire)
        VALUES (?, ?, datetime('now'), ?, ?)
    """, (piece_id, action, session.get("role", "SYSTEM"), commentaire))
    conn.commit()
    conn.close()

def require_role(role):
    def deco(fn):
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                return jsonify({"error": "Accès interdit"}), 403
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return deco

# ---------- AUTH ----------
@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE username=?", (d["username"],)).fetchone()
    conn.close()

    if u and check_password_hash(u["password_hash"], d["password"]):
        session["username"] = u["username"]
        session["role"] = u["role"]
        return jsonify({"ok": True, "role": u["role"]})

    return jsonify({"error": "Login invalide"}), 401

@app.route("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/me")
def me():
    return jsonify({
        "username": session.get("username"),
        "role": session.get("role")
    })

# ---------- STATIC ----------
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/piece/<identifiant>")
def piece_page(identifiant):
    return send_from_directory(FRONTEND_DIR, "piece.html")

@app.route("/css/<path:f>")
def css(f):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), f)

@app.route("/js/<path:f>")
def js(f):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), f)

@app.route("/img/<path:f>")
def img(f):
    return send_from_directory(os.path.join(FRONTEND_DIR, "img"), f)

@app.route("/qr/<path:f>")
def qr(f):
    return send_from_directory(QR_DIR, f)

# ---------- API ----------
@app.route("/api/pieces")
def pieces():
    conn = get_db()
    rows = conn.execute("SELECT * FROM piece ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/piece/<identifiant>")
def piece(identifiant):
    conn = get_db()
    p = conn.execute("SELECT * FROM piece WHERE identifiant=?", (identifiant,)).fetchone()
    conn.close()
    if not p:
        return jsonify({"error": "introuvable"}), 404
    return jsonify(dict(p))

@app.route("/api/piece", methods=["POST"])
@require_role("MAINT")
def add_piece():
    d = request.json
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO piece(
            identifiant, type_piece, statut, localisation,
            date_entree, origine, qr_filename,
            taux_endommagement, commentaire
        )
        VALUES (?, ?, ?, NULL, ?, ?, NULL, ?, ?)
    """, (
        d["identifiant"], d["type_piece"], d["statut"],
        d["date_entree"], d["origine"],
        d["taux_endommagement"], d["commentaire"]
    ))
    pid = cur.lastrowid
    conn.commit()
    conn.close()

    log_action(pid, "CREATION", "Créée par MAINT")
    return jsonify({"ok": True})

@app.route("/api/piece/<int:pid>/localisation", methods=["POST"])
@require_role("LOG")
def set_loc(pid):
    loc = request.json["localisation"]
    conn = get_db()
    p = conn.execute("SELECT identifiant FROM piece WHERE id=?", (pid,)).fetchone()

    if not p:
        return jsonify({"error": "introuvable"}), 404

    qr_file = f"{p['identifiant']}.png"
    qrcode.make(f"{request.host_url}piece/{p['identifiant']}").save(os.path.join(QR_DIR, qr_file))

    conn.execute("""
        UPDATE piece SET localisation=?, qr_filename=?
        WHERE id=?
    """, (loc, qr_file, pid))
    conn.commit()
    conn.close()

    log_action(pid, "LOCALISATION", loc)
    return jsonify({"ok": True})

@app.route("/api/historique/<int:pid>")
def hist(pid):
    conn = get_db()
    rows = conn.execute("""
        SELECT date_action, role, action, commentaire
        FROM historique WHERE piece_id=?
        ORDER BY date_action DESC
    """, (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/indicateurs")
def kpis():
    conn = get_db()
    r = conn.execute("""
        SELECT
        COUNT(*) total,
        SUM(statut='reparable') reparable,
        SUM(statut='non_reparable') non_reparable,
        SUM(statut='cannibalisable') cannibalisable
        FROM piece
    """).fetchone()
    conn.close()
    return jsonify(dict(r))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
