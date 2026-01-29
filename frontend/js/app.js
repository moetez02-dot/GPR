const roleSpan = document.getElementById("role");
const list = document.getElementById("list");

// ================== SESSION ==================
fetch("/api/me").then(r => r.json()).then(u => {
  if (!u.role) return;
  roleSpan.textContent = u.role;
  loadPieces();
});

// ================== AJOUT PIECE (MAINT) ==================
function addPiece() {
  fetch("/api/piece", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      identifiant: identifiant.value,
      type_piece: type.value,
      statut: statut.value,
      date_entree: date.value,
      origine: origine.value,
      taux_endommagement: taux.value,
      commentaire: commentaire.value
    })
  })
  .then(r => r.json())
  .then(res => {
    if (res.error) alert(res.error);
    else location.reload();
  });
}

// ================== LOCALISATION (LOG) ==================
function updateLoc(id) {
  const val = document.getElementById("loc-" + id).value;

  fetch(`/api/piece/${id}/localisation`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ localisation: val })
  })
  .then(r => r.json())
  .then(res => {
    if (res.error) alert(res.error);
    else location.reload();
  });
}

// ================== LISTE ==================
function loadPieces() {
  fetch("/api/pieces").then(r => r.json()).then(data => {
    list.innerHTML = "";
    data.forEach(p => {
      list.innerHTML += `
      <tr>
        <td>${p.id}</td>
        <td>${p.identifiant}</td>
        <td>${p.statut}</td>
        <td>${p.localisation || "—"}</td>
        <td>${p.qr_filename ? `<img src="/qr/${p.qr_filename}" width="60">` : "—"}</td>
        <td><a href="/piece/${p.identifiant}">Voir</a></td>
        <td>
          <input id="loc-${p.id}" placeholder="Localisation">
          <button onclick="updateLoc(${p.id})">Valider</button>
        </td>
      </tr>`;
    });
  });
}
