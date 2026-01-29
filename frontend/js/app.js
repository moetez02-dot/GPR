function login() {
    fetch("/api/login", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            username: loginUser.value,
            password: loginPass.value
        })
    })
    .then(r=>r.json())
    .then(d=>{
        if(d.role) init(d.role);
        else loginError.innerText="Erreur";
    });
}

function logout(){ fetch("/api/logout").then(()=>location.reload()); }

function init(role){
    loginCard.style.display="none";
    appContent.style.display="block";
    roleDisplay.innerText=role;
    maintenanceBlock.style.display= role==="MAINT" ? "block":"none";
    load();
}

fetch("/api/me").then(r=>r.json()).then(d=>{ if(d.role) init(d.role); });

pieceForm?.addEventListener("submit",e=>{
    e.preventDefault();
    fetch("/api/piece",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            identifiant: identifiant.value,
            type_piece: type_piece.value,
            statut: statut.value,
            localisation: localisation.value,
            date_entree: date_entree.value,
            origine: origine.value
        })
    }).then(()=>{pieceForm.reset();load();});
});

function load(){
    fetch("/api/pieces").then(r=>r.json()).then(data=>{
        tablePieces.innerHTML="";
        data.forEach(p=>{
            tablePieces.innerHTML+=`
            <tr>
                <td>${p.id}</td>
                <td>${p.identifiant}</td>
                <td>${p.statut}</td>
                <td>${p.qr_filename ? `<img src="/qr/${p.qr_filename}" width="50">`:"-"}</td>
                <td><button onclick="hist(${p.id})">Voir</button></td>
            </tr>`;
        });
    });

    fetch("/api/indicateurs").then(r=>r.json()).then(k=>{
        kpi.innerText = `Total: ${k.total} | Réparables: ${k.reparable}`;
    });
}

function hist(id){
    fetch(`/api/historique/${id}`)
    .then(r=>r.json())
    .then(h=>{
        let txt="Historique:\n";
        h.forEach(e=>{
            txt+=`${e.date_action} | ${e.role} | ${e.action} | ${e.commentaire}\n`;
        });
        alert(txt);
    });
}
