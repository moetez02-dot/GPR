from flask import Flask, jsonify, request, send_from_directory, session
import sqlite3, os, qrcode
from werkzeug.security import check_password_hash

# ================== PATHS ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")
QR_DIR = os.path.join(BASE_DIR, "qr")
DB_PATH = os.path.join(BASE_DIR, "gpr.db")

os.makedirs(QR_DIR, exist_ok=True)

# ================== APP ==================
app = Flask(__name__)
app.secret_key = "GPR_SECRET_KEY"

# ================== DB ==================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_action(piece_id, action, commentaire=""):
    conn = get_db()
    conn.execute("""
        INSERT INTO historique(piece_id, action, date_action, commentaire)
        VALUES (?, ?, datetime('now'), ?)
    """, (piece_id, action, commentaire))
    conn.commit()
    conn.close()

# ================== AUTH ==================
@app.route("/api/login", methods=["POST"])
def login():
    d = request.json
    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username=?",
        (d["username"],)
    ).fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], d["password"]):
        session["username"] = user["username"]
        session["role"] = user["role"]
        return jsonify({"role": user["role"]})

    return jsonify({"error": "Login incorrect"}), 401

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
def css(f): return send_from_directory(FRONTEND_DIR + "/css", f)

@app.route("/js/<path:f>")
def js(f): return send_from_directory(FRONTEND_DIR + "/js", f)

@app.route("/img/<path:f>")
def img(f): return send_from_directory(FRONTEND_DIR + "/img", f)

@app.route("/qr/<path:f>")
def qr(f): return send_from_directory(QR_DIR, f)

# ================== MAINT ==================
@app.route("/api/piece", methods=["POST"])
def add_piece():
    if session.get("role") != "MAINT":
        return jsonify({"error": "MAINT only"}), 403

    d = request.json
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO piece
        (identifiant, type_piece, statut, date_entree, origine, taux_endommagement, commentaire)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        d["identifiant"],
        d["type_piece"],
        d["statut"],
        d["date_entree"],
        d["origine"],
        d["taux_endommagement"],
        d["commentaire"]
    ))
    piece_id = cur.lastrowid
    conn.commit()
    conn.close()

    log_action(piece_id, "CREATION", "Création par MAINT")
    return jsonify({"ok": True})

# ================== LOG ==================
@app.route("/api/piece/<int:piece_id>/localisation", methods=["POST"])
def set_localisation(piece_id):
    if session.get("role") != "LOG":
        return jsonify({"error": "LOG only"}), 403

    loc = request.json.get("localisation")
    conn = get_db()

    piece = conn.execute(
        "SELECT identifiant FROM piece WHERE id=?",
        (piece_id,)
    ).fetchone()

    if not piece:
        return jsonify({"error": "Pièce introuvable"}), 404

    identifiant = piece["identifiant"]
    qr_filename = f"{identifiant}.png"

    qr_url = f"{request.host_url.rstrip('/')}/piece/{identifiant}"
    qrcode.make(qr_url).save(os.path.join(QR_DIR, qr_filename))

    conn.execute("""
        UPDATE piece SET localisation=?, qr_filename=?
        WHERE id=?
    """, (loc, qr_filename, piece_id))

    conn.commit()
    conn.close()

    log_action(piece_id, "LOCALISATION", loc)
    return jsonify({"ok": True})

# ================== CONSULTATION ==================
@app.route("/api/pieces")
def pieces():
    conn = get_db()
    rows = conn.execute("SELECT * FROM piece ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/piece/<identifiant>")
def get_piece(identifiant):
    conn = get_db()
    p = conn.execute(
        "SELECT * FROM piece WHERE identifiant=?",
        (identifiant,)
    ).fetchone()
    conn.close()
    if not p:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(p))

@app.route("/api/historique/<int:pid>")
def hist(pid):
    conn = get_db()
    h = conn.execute("""
        SELECT date_action, action, commentaire
        FROM historique WHERE piece_id=?
        ORDER BY date_action DESC
    """, (pid,)).fetchall()
    conn.close()
    return jsonify([dict(x) for x in h])

@app.route("/api/indicateurs")
def indicateurs():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM piece").fetchone()[0]
    rep = conn.execute("SELECT COUNT(*) FROM piece WHERE statut='reparable'").fetchone()[0]
    non = conn.execute("SELECT COUNT(*) FROM piece WHERE statut='non_reparable'").fetchone()[0]
    can = conn.execute("SELECT COUNT(*) FROM piece WHERE statut='cannibalisable'").fetchone()[0]
    conn.close()
    return jsonify({
        "total": total,
        "reparable": rep,
        "non_reparable": non,
        "cannibalisable": can
    })

# ================== RUN ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
