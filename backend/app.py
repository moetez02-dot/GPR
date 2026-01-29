from flask import Flask, jsonify, request, send_from_directory, session
import sqlite3
import os
import qrcode
from werkzeug.security import check_password_hash

# ================== PATHS ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")
QR_DIR = os.path.join(BASE_DIR, "qr")
os.makedirs(QR_DIR, exist_ok=True)

# ================== APP ==================
app = Flask(__name__)
app.secret_key = "gpr_secret_key"

# ================== DATABASE ==================
def get_db():
    conn = sqlite3.connect("gpr.db")
    conn.row_factory = sqlite3.Row
    return conn

def log_action(piece_id, action, commentaire=""):
    conn = get_db()
    conn.execute("""
        INSERT INTO historique (piece_id, action, date_action, role, commentaire)
        VALUES (?, ?, datetime('now'), ?, ?)
    """, (
        piece_id,
        action,
        session.get("role", "UNKNOWN"),
        commentaire
    ))
    conn.commit()
    conn.close()

# ================== AUTH ==================
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
        session["role"] = user["role"]
        session["username"] = user["username"]
        return jsonify({"role": user["role"]})

    return jsonify({"error": "Identifiants invalides"}), 401


@app.route("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/me")
def me():
    if "role" not in session:
        return jsonify({"role": None})
    return jsonify({
        "role": session["role"],
        "username": session["username"]
    })

# ================== STATIC FILES ==================
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/piece/<identifiant>")
def piece_page(identifiant):
    return send_from_directory(FRONTEND_DIR, "piece.html")


@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), filename)


@app.route("/js/<path:filename>")
def js_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)


@app.route("/img/<path:filename>")
def img_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "img"), filename)


@app.route("/qr/<path:filename>")
def qr_files(filename):
    return send_from_directory(QR_DIR, filename)

# ================== PIECES ==================
@app.route("/api/piece", methods=["POST"])
def add_piece():
    if session.get("role") != "MAINT":
        return jsonify({"error": "Accès réservé au service maintenance"}), 403

    d = request.json
    identifiant = d["identifiant"]

    # -------- QR CODE AVEC URL --------
    qr_filename = f"{identifiant}.png"
    url = f"http://127.0.0.1:5000/piece/{identifiant}"
    qrcode.make(url).save(os.path.join(QR_DIR, qr_filename))

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO piece
        (identifiant, type_piece, statut, localisation, date_entree, origine, qr_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        identifiant,
        d.get("type_piece"),
        d.get("statut"),
        d.get("localisation"),
        d.get("date_entree"),
        d.get("origine"),
        qr_filename
    ))

    piece_id = cur.lastrowid
    conn.commit()
    conn.close()

    log_action(piece_id, "CREATION", "Création de la pièce et génération du QR")

    return jsonify({"ok": True})

@app.route("/api/pieces")
def list_pieces():
    conn = get_db()
    rows = conn.execute("SELECT * FROM piece").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/piece/<identifiant>")
def get_piece_by_identifiant(identifiant):
    conn = get_db()
    piece = conn.execute(
        "SELECT * FROM piece WHERE identifiant=?",
        (identifiant,)
    ).fetchone()
    conn.close()

    if not piece:
        return jsonify({"error": "Pièce introuvable"}), 404

    return jsonify(dict(piece))

# ================== HISTORIQUE ==================
@app.route("/api/historique/<int:piece_id>")
def historique_piece(piece_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT date_action, role, action, commentaire
        FROM historique
        WHERE piece_id=?
        ORDER BY date_action DESC
    """, (piece_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ================== KPI ==================
@app.route("/api/indicateurs")
def indicateurs():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM piece").fetchone()[0]
    reparable = conn.execute(
        "SELECT COUNT(*) FROM piece WHERE statut='reparable'"
    ).fetchone()[0]
    conn.close()
    return jsonify({
        "total": total,
        "reparable": reparable
    })
@app.route("/api/piece/<int:piece_id>/localisation", methods=["POST"])
def update_localisation(piece_id):
    if session.get("role") != "LOG":
        return jsonify({"error": "Accès réservé au service logistique"}), 403

    data = request.json
    new_loc = data.get("localisation")

    conn = get_db()
    piece = conn.execute(
        "SELECT localisation FROM piece WHERE id=?",
        (piece_id,)
    ).fetchone()

    if not piece:
        conn.close()
        return jsonify({"error": "Pièce introuvable"}), 404

    old_loc = piece["localisation"]

    conn.execute(
        "UPDATE piece SET localisation=? WHERE id=?",
        (new_loc, piece_id)
    )
    conn.commit()
    conn.close()

    log_action(
        piece_id,
        "MODIF_LOCALISATION",
        f"{old_loc} → {new_loc}"
    )

    return jsonify({"ok": True})

# ================== RUN ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

