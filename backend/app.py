from flask import Flask, jsonify, request, send_from_directory, session
import sqlite3, os, qrcode
from werkzeug.security import check_password_hash

# ================= PATHS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")
QR_DIR = os.path.join(BASE_DIR, "qr")
DB_PATH = os.path.join(BASE_DIR, "gpr.db")
os.makedirs(QR_DIR, exist_ok=True)

# ================= APP =================
app = Flask(__name__)
app.secret_key = "GPR_SECRET_PROD"

# ================= DB =================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_action(piece_id, action, commentaire=""):
    conn = get_db()
    conn.execute("""
        INSERT INTO historique (piece_id, action, date_action, role, commentaire)
        VALUES (?, ?, datetime('now'), ?, ?)
    """, (piece_id, action, session.get("role","SYSTEM"), commentaire))
    conn.commit()
    conn.close()

# ================= AUTH =================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=?",
        (data["username"],)
    ).fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], data["password"]):
        session["username"] = user["username"]
        session["role"] = user["role"]
        return jsonify({"role": user["role"]})

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

# ================= STATIC =================
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

# ================= PIECES =================
@app.route("/api/piece", methods=["POST"])
def add_piece():
    if session.get("role") != "MAINT":
        return jsonify({"error": "Accès MAINT"}), 403

    d = request.json
    identifiant = d["identifiant"]

    qr_filename = f"{identifiant}.png"
    qr_url = f"{request.host_url.rstrip('/')}/piece/{identifiant}"
    qrcode.make(qr_url).save(os.path.join(QR_DIR, qr_filename))

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO piece
        (identifiant, type_piece, statut, localisation, date_entree, origine,
         qr_filename, taux_endommagement, commentaire)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        identifiant,
        d.get("type_piece"),
        d.get("statut"),
        d.get("localisation"),
        d.get("date_entree"),
        d.get("origine"),
        qr_filename,
        d.get("taux_endommagement"),
        d.get("commentaire")
    ))
    piece_id = cur.lastrowid
    conn.commit()
    conn.close()

    log_action(piece_id, "CREATION", "Création pièce + QR")

    return jsonify({"ok": True})

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
        return jsonify({"error": "Pièce introuvable"}), 404

    return jsonify(dict(piece))

# ================= HISTORIQUE =================
@app.route("/api/historique/<int:piece_id>")
def historique(piece_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT date_action, role, action, commentaire
        FROM historique
        WHERE piece_id=?
        ORDER BY date_action DESC
    """, (piece_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ================= KPI =================
@app.route("/api/indicateurs")
def indicateurs():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM piece").fetchone()[0]
    reparable = conn.execute(
        "SELECT COUNT(*) FROM piece WHERE statut='reparable'"
    ).fetchone()[0]
    conn.close()
    return jsonify({"total": total, "reparable": reparable})

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
