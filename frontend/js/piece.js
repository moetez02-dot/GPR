const identifiant = window.location.pathname.split("/").pop();

// Charger la pièce
fetch(`/api/piece/${identifiant}`)
  .then(r => r.json())
  .then(piece => {
    if (piece.error) {
      alert("Pièce introuvable");
      return;
    }

    document.getElementById("identifiant").textContent = piece.identifiant || "-";
    document.getElementById("type").textContent = piece.type_piece || "-";
    document.getElementById("statut").textContent = piece.statut || "-";
    document.getElementById("localisation").textContent = piece.localisation || "-";
    document.getElementById("date").textContent = piece.date_entree || "-";
    document.getElementById("origine").textContent = piece.origine || "-";
    document.getElementById("taux").textContent =
      piece.taux_endommagement !== null ? piece.taux_endommagement : "-";
    document.getElementById("commentaire").textContent = piece.commentaire || "-";

    // Historique
    fetch(`/api/historique/${piece.id}`)
      .then(r => r.json())
      .then(hist => {
        const ul = document.getElementById("hist");
        ul.innerHTML = "";
        hist.forEach(h => {
          const li = document.createElement("li");
          li.textContent =
            `${h.date_action} — ${h.role} — ${h.action} (${h.commentaire || ""})`;
          ul.appendChild(li);
        });
      });
  });
