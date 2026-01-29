from flask import Flask, jsonify, request, send_from_directory, session
import sqlite3, os, qrcode
from werkzeug.security import check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")
QR_DIR = os.path.join(BASE_DIR, "qr")
DB_PATH = os.path.join(BASE_DIR, "gpr.db")

os.makedirs(QR_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "CHANGE_ME_IN_PROD"

# ---------- DB ----------
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
        return jsonify({"role": u["role"]})
    return jsonify({"error":"Login invalide"}), 401

@app.route("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok":True})

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
def css(f): return send_from_directory(FRONTEND_DIR+"/css", f)

@app.route("/js/<path:f>")
def js(f): return send_from_directory(FRONTEND_DIR+"/js", f)

@app.route("/img/<path:f>")
def img(f): return send_from_directory(FRONTEND_DIR+"/img", f)

@app.route("/qr/<path:f>")
def qr(f): return send_from_directory(QR_DIR, f)

# ---------- PIECES ----------
@app.route("/api/piece", methods=["POST"])
def add_piece():
    if session.get("role") != "MAINT":
        return jsonify({"error":"MAINT uniquement"}),403

    d = request.json
    identifiant = d["identifiant"]

    qr_name = f"{identifiant}.png"
    qr_url = f"{request.host_url.rstrip('/')}/piece/{identifiant}"
    qrcode.make(qr_url).save(os.path.join(QR_DIR, qr_name))

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO piece
        (identifiant, type_piece, statut, localisation, date_entree, origine,
         taux_endommagement, commentaire, qr_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        identifiant,
        d["type_piece"],
        d["statut"],
        d["localisation"],
        d["date_entree"],
        d["origine"],
        d["taux_endommagement"],
        d["commentaire"],
        qr_name
    ))
    pid = cur.lastrowid
    conn.commit()
    conn.close()

    log_action(pid, "CREATION", f"{d['taux_endommagement']}% | {d['commentaire']}")
    return jsonify({"ok":True})

@app.route("/api/pieces")
def pieces():
    conn = get_db()
    rows = conn.execute("SELECT * FROM piece").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/piece/<identifiant>")
def piece(identifiant):
    conn = get_db()
    p = conn.execute("SELECT * FROM piece WHERE identifiant=?", (identifiant,)).fetchone()
    conn.close()
    if not p: return jsonify({"error":"Pièce introuvable"}),404
    return jsonify(dict(p))

# ---------- HISTORIQUE ----------
@app.route("/api/historique/<int:pid>")
def hist(pid):
    conn = get_db()
    rows = conn.execute("""
        SELECT date_action, role, action, commentaire
        FROM historique WHERE piece_id=?
        ORDER BY date_action DESC
    """,(pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ---------- LOG ----------
@app.route("/api/piece/<int:pid>/localisation", methods=["POST"])
def update_loc(pid):
    if session.get("role") != "LOG":
        return jsonify({"error":"LOG uniquement"}),403

    loc = request.json["localisation"]
    conn = get_db()
    old = conn.execute("SELECT localisation FROM piece WHERE id=?", (pid,)).fetchone()
    conn.execute("UPDATE piece SET localisation=? WHERE id=?", (loc,pid))
    conn.commit()
    conn.close()

    log_action(pid,"LOCALISATION",f"{old['localisation']} → {loc}")
    return jsonify({"ok":True})

# ---------- KPI ----------
@app.route("/api/indicateurs")
def kpi():
    conn = get_db()
    t = conn.execute("SELECT COUNT(*) FROM piece").fetchone()[0]
    r = conn.execute("SELECT COUNT(*) FROM piece WHERE statut='reparable'").fetchone()[0]
    conn.close()
    return jsonify({"total":t,"reparable":r})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
