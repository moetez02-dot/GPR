const id = location.pathname.split("/").pop()

fetch("/api/piece/"+id).then(r=>r.json()).then(p=>{
 type.textContent=p.type_piece
 statut.textContent=p.statut
 loc.textContent=p.localisation
 date.textContent=p.date_entree
 origine.textContent=p.origine
 taux.textContent=p.taux_endommagement
 com.textContent=p.commentaire

 fetch("/api/historique/"+p.id)
 .then(r=>r.json())
 .then(h=>{
  h.forEach(e=>{
   hist.innerHTML+=`<li>${e.date_action} - ${e.role} - ${e.commentaire}</li>`
  })
 })
})
