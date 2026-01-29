const parts = window.location.pathname.split("/");
const identifiant = parts[parts.length - 1];
let pieceId = null;

function loadPiece() {
  fetch(`/api/piece/${identifiant}`)
    .then(r => r.json())
    .then(p => {
      if (p.error) return;

      pieceId = p.id;

      document.getElementById("titre").innerText = `Pièce : ${p.identifiant}`;
      document.getElementById("type").innerText = p.type_piece || "";
      document.getElementById("statut").innerText = p.statut || "";
      document.getElementById("loc").innerText = p.localisation || "";
      document.getElementById("date").innerText = p.date_entree || "";
      document.getElementById("origine").innerText = p.origine || "";

      loadHistorique(p.id);
      checkRole();
    });
}

function loadHistorique(id) {
  fetch(`/api/historique/${id}`)
    .then(r => r.json())
    .then(h => {
      let txt = "";
      h.forEach(e => {
        txt += `${e.date_action} | ${e.role} | ${e.action} | ${e.commentaire}\n`;
      });
      document.getElementById("hist").innerText = txt || "Aucun historique";
    });
}

function checkRole() {
  fetch("/api/me")
    .then(r => r.json())
    .then(u => {
      if (u.role === "LOG") {
        document.getElementById("logBlock").style.display = "block";
      }
    });
}

function updateLoc() {
  fetch(`/api/piece/${pieceId}/localisation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      localisation: document.getElementById("newLoc").value
    })
  })
  .then(r => r.json())
  .then(res => {
    if (res.ok) {
      document.getElementById("locMsg").innerText = "Localisation mise à jour";
      loadPiece();
    } else {
      document.getElementById("locMsg").innerText = res.error;
    }
  });
}

loadPiece();
