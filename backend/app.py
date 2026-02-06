# ================== IMPORTS ==================
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_cors import CORS
import sqlite3
import os
import uuid
import qrcode

# ================== PATHS ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")
QR_DIR = os.path.join(BASE_DIR, "qr")
os.makedirs(QR_DIR, exist_ok=True)

# DB persistante (Render + Local)
DB_PATH = os.environ.get("DATABASE_PATH") or os.path.join(BASE_DIR, "gpr.db")

# URL publique pour QR
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL")

# ================== APP ==================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gpr_secret_dev")

# Cookies session (connexion multi-appareils)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True
)

CORS(app, supports_credentials=True)

# ================== DB ==================
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

# ================== SCHEMA ==================
def ensure_schema():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS piece (
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
    CREATE TABLE IF NOT EXISTS historique (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        piece_id INTEGER,
        action TEXT,
        date_action TEXT,
        role TEXT,
        commentaire TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        role TEXT
    )
    """)

    conn.commit()
    conn.close()

# ================== USERS ==================
def ensure_default_users():
    conn = get_db()

    users = [
        ("main", generate_password_hash("main123"), "MAINT"),
        ("log", generate_password_hash("log123"), "LOG"),
    ]

    for u in users:
        conn.execute(
            "INSERT OR IGNORE INTO users(username,password_hash,role) VALUES (?,?,?)",
            u
        )

    conn.commit()
    conn.close()

# ================== LOG ==================
def log_action(piece_id, action, commentaire=""):
    conn = get_db()
    conn.execute("""
        INSERT INTO historique(piece_id, action, date_action, role, commentaire)
        VALUES (?, ?, datetime('now'), ?, ?)
    """, (piece_id, action, session.get("role", "PUBLIC"), commentaire))
    conn.commit()
    conn.close()

# ================== ROLE ==================
def require_role(*roles):
    def deco(fn):
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                return jsonify({"error": "Accès interdit"}), 403
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return deco

# Init DB
ensure_schema()
ensure_default_users()

# ================== AUTH ==================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=?",
        (data.get("username"),)
    ).fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], data.get("password")):
        session["username"] = user["username"]
        session["role"] = user["role"]
        return jsonify({"ok": True, "role": user["role"]})

    return jsonify({"error": "Identifiants invalides"}), 401


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

# ================== STATIC ==================
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/piece/<identifiant>")
def piece_page(identifiant):
    return send_from_directory(FRONTEND_DIR, "piece.html")

@app.route("/css/<path:f>")
def css_files(f):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), f)

@app.route("/js/<path:f>")
def js_files(f):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), f)

@app.route("/img/<path:f>")
def img_files(f):
    return send_from_directory(os.path.join(FRONTEND_DIR, "img"), f)

@app.route("/qr/<path:f>")
def qr_files(f):
    return send_from_directory(QR_DIR, f)

# ================== API ==================
@app.route("/api/pieces")
def list_pieces():
    conn = get_db()
    rows = conn.execute("SELECT * FROM piece ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/piece/<identifiant>")
def get_piece(identifiant):
    conn = get_db()
    piece = conn.execute(
        "SELECT * FROM piece WHERE identifiant=?",
        (identifiant,)
    ).fetchone()
    conn.close()

    if not piece:
        return jsonify({"error": "Introuvable"}), 404

    return jsonify(dict(piece))

# ================== MAINT ==================
@app.route("/api/piece", methods=["POST"])
@require_role("MAINT")
def add_piece():
    d = request.json or {}

    identifiant = f"P-{uuid.uuid4().hex[:8].upper()}"
    qr_filename = f"{identifiant}.png"

    base_url = (PUBLIC_BASE_URL or request.url_root).rstrip("/")
    qr_url = f"{base_url}/piece/{identifiant}"

    qrcode.make(qr_url).save(os.path.join(QR_DIR, qr_filename))

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO piece(
            identifiant,type_piece,statut,localisation,
            date_entree,origine,qr_filename,
            taux_endommagement,commentaire
        )
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        identifiant,
        d.get("type_piece"),
        d.get("statut"),
        None,
        d.get("date_entree"),
        d.get("origine"),
        qr_filename,
        int(d.get("taux_endommagement") or 0),
        d.get("commentaire")
    ))

    piece_id = cur.lastrowid
    conn.commit()
    conn.close()

    log_action(piece_id, "CREATION", "Création + QR (MAINT)")

    return jsonify({"ok": True, "identifiant": identifiant})

# ================== LOG ==================
@app.route("/api/piece/<int:piece_id>/localisation", methods=["POST"])
@require_role("LOG")
def update_localisation(piece_id):
    d = request.json or {}
    loc = d.get("localisation")
    com = d.get("commentaire", "")

    if not loc:
        return jsonify({"error": "Localisation obligatoire"}), 400

    conn = get_db()
    conn.execute(
        "UPDATE piece SET localisation=? WHERE id=?",
        (loc, piece_id)
    )
    conn.commit()
    conn.close()

    log_action(piece_id, "LOCALISATION", com or loc)

    return jsonify({"ok": True})

# ================== DEBUG ==================
@app.route("/api/debug/users")
def debug_users():
    conn = get_db()
    rows = conn.execute("SELECT username,role FROM users").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ================== RUN ==================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
