let role = null;
const $ = id => document.getElementById(id);

async function api(url, opt={}) {
  const r = await fetch(url, opt);
  const d = await r.json();
  if (!r.ok) throw d;
  return d;
}

async function refresh() {
  const me = await api("/api/me");
  role = me.role;

  $("login").style.display = role ? "none" : "";
  $("main").style.display = role ? "" : "none";
  $("who").textContent = role || "";

  if (role) {
    loadKpis();
    loadPieces();
  }
}

async function login() {
  try {
    await api("/api/login", {
      method:"POST",
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        username:$("user").value,
        password:$("pass").value
      })
    });
    refresh();
  } catch {
    alert("Login incorrect");
  }
}

async function logout() {
  await api("/api/logout");
  refresh();
}

async function loadKpis() {
  const k = await api("/api/indicateurs");
  $("kpis").textContent =
    `Total ${k.total} | Rep ${k.reparable} | Non rep ${k.non_reparable} | Cann ${k.cannibalisable}`;
}

async function addPiece() {
  await api("/api/piece", {
    method:"POST",
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      identifiant:$("id").value,
      type_piece:$("type").value,
      statut:$("statut").value,
      date_entree:$("date").value,
      origine:$("origine").value,
      taux_endommagement:$("taux").value,
      commentaire:$("com").value
    })
  });
  loadPieces();
}

async function setLoc(pid) {
  const v = document.getElementById("loc_"+pid).value;
  await api(`/api/piece/${pid}/localisation`, {
    method:"POST",
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({localisation:v})
  });
  loadPieces();
}

async function loadPieces() {
  const data = await api("/api/pieces");
  const b = $("rows");
  b.innerHTML = "";
  data.forEach(p=>{
    b.innerHTML += `
      <tr>
        <td>${p.id}</td>
        <td>${p.identifiant}</td>
        <td>${p.statut}</td>
        <td>${p.localisation||"—"}</td>
        <td>${p.qr_filename ? `<img src="/qr/${p.qr_filename}" width="60">` : "—"}</td>
        <td><a href="/piece/${p.identifiant}">Voir</a></td>
        ${role==="LOG" ? `<td><input id="loc_${p.id}"><button onclick="setLoc(${p.id})">OK</button></td>` : ""}
      </tr>
    `;
  });
}

document.addEventListener("DOMContentLoaded", refresh);
