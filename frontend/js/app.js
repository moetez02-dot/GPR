// ================== ELEMENTS ==================
const loginForm = document.getElementById("loginForm");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");

const userInfo = document.getElementById("userInfo");
const roleSpan = document.getElementById("role");
const logoutBtn = document.getElementById("logoutBtn");

const addForm = document.getElementById("addForm");
const list = document.getElementById("list");

// Champs ajout pièce
const identifiant = document.getElementById("identifiant");
const type = document.getElementById("type");
const statut = document.getElementById("statut");
const localisation = document.getElementById("localisation");
const date = document.getElementById("date");
const origine = document.getElementById("origine");
const taux = document.getElementById("taux");
const commentaire = document.getElementById("commentaire");

// ================== AUTH ==================
function checkMe() {
  fetch("/api/me")
    .then(r => r.json())
    .then(data => {
      if (!data.role) {
        userInfo.style.display = "none";
        addForm.style.display = "none";
      } else {
        userInfo.style.display = "block";
        roleSpan.textContent = data.role;

        // MAINT uniquement
        if (data.role === "MAINT") {
          addForm.style.display = "block";
        } else {
          addForm.style.display = "none";
        }

        loadPieces();
        loadIndicateurs();
      }
    });
}

if (loginForm) {
  loginForm.onsubmit = (e) => {
    e.preventDefault();
    fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: usernameInput.value,
        password: passwordInput.value
      })
    })
      .then(r => {
        if (!r.ok) throw new Error("Login invalide");
        return r.json();
      })
      .then(() => {
        location.reload();
      })
      .catch(() => alert("Identifiants incorrects"));
  };
}

if (logoutBtn) {
  logoutBtn.onclick = () => {
    fetch("/api/logout").then(() => location.reload());
  };
}

// ================== AJOUT PIECE ==================
function addPiece() {
  fetch("/api/piece", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      identifiant: identifiant.value,
      type_piece: type.value,
      statut: statut.value,
      localisation: localisation.value,
      date_entree: date.value,
      origine: origine.value,
      taux_endommagement: taux.value,
      commentaire: commentaire.value
    })
  })
    .then(r => {
      if (!r.ok) throw new Error("Erreur ajout");
      return r.json();
    })
    .then(() => {
      addForm.reset();
      loadPieces();
      loadIndicateurs();
    })
    .catch(() => alert("Erreur lors de l’ajout"));
}

// ================== LISTE PIECES ==================
function loadPieces() {
  fetch("/api/pieces")
    .then(r => r.json())
    .then(data => {
      list.innerHTML = "";
      data.forEach(p => {
        list.innerHTML += `
          <tr>
            <td>${p.id}</td>
            <td>${p.identifiant}</td>
            <td>${p.statut}</td>
            <td>
              <img src="/qr/${p.qr_filename}" width="70">
            </td>
            <td>
              <a href="/piece/${p.identifiant}">Voir</a>
            </td>
          </tr>
        `;
      });
    });
}

// ================== INDICATEURS ==================
function loadIndicateurs() {
  fetch("/api/indicateurs")
    .then(r => r.json())
    .then(kpi => {
      document.getElementById("total").textContent = kpi.total;
      document.getElementById("reparable").textContent = kpi.reparable;
    });
}

// ================== INIT ==================
checkMe();
