function addPiece() {
  fetch("/api/piece", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      identifiant: identifiant.value.trim(),
      type_piece: type.value.trim(),
      statut: statut.value,
      localisation: localisation.value.trim(),
      date_entree: date.value,
      origine: origine.value.trim(),
      taux_endommagement: parseInt(document.getElementById("taux").value || 0),
      commentaire: document.getElementById("commentaire").value.trim()
    })
  })
  .then(r => {
    if (!r.ok) throw new Error("Erreur ajout");
    return r.json();
  })
  .then(() => location.reload())
  .catch(() => alert("Erreur lors de l'ajout"));
}
