// script.js — MH-CET College Predictor frontend logic

const API = "";   // empty string = same origin (works for both dev and prod)

// ── Populate dropdowns from /meta ────────
async function loadMeta() {
  try {
    const res  = await fetch(`${API}/meta`);
    const data = await res.json();

    // Categories
    const catSel = document.getElementById("category");
    catSel.innerHTML = data.categories
      .map(c => `<option value="${c}">${c}</option>`)
      .join("");

    // Districts
    const distSel = document.getElementById("district");
    data.districts.forEach(d => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      distSel.appendChild(opt);
    });

    // Branches
    const branchSel = document.getElementById("branch");
    data.branches.forEach(b => {
      const opt = document.createElement("option");
      opt.value = b;
      opt.textContent = b;
      branchSel.appendChild(opt);
    });
  } catch (e) {
    console.error("Failed to load meta:", e);
  }
}

// ── Main predict call ─────────────────────────────────────────────
async function predict() {
  const percentile = parseFloat(document.getElementById("percentile").value);
  if (!percentile || percentile < 0 || percentile > 100) {
    alert("Please enter a valid percentile between 0 and 100.");
    return;
  }

  const category  = document.getElementById("category").value;
  const gender    = document.getElementById("gender").value;
  const cap_round = document.getElementById("cap_round").value;
  const district  = document.getElementById("district").value;
  const branch    = document.getElementById("branch").value;

  const btn = document.querySelector(".predict-btn");
  btn.textContent = "Searching…";
  btn.disabled = true;

  try {
    const params = new URLSearchParams({
      percentile,
      category,
      gender,
      cap_round,
      ...(district && { district }),
      ...(branch   && { branch }),
    });

    const res  = await fetch(`${API}/predict?${params}`);
    const data = await res.json();

    renderResults(data);
  } catch (e) {
    alert("Could not connect to server. Make sure the backend is running.");
    console.error(e);
  } finally {
    btn.textContent = "Show colleges →";
    btn.disabled = false;
  }
}

// ── Render results ─────
function renderResults(data) {
  const section  = document.getElementById("results-section");
  const grid     = document.getElementById("results-grid");
  const noRes    = document.getElementById("no-results");
  const countEl  = document.getElementById("results-count");
  const titleEl  = document.getElementById("results-title");

  section.style.display = "block";
  section.scrollIntoView({ behavior: "smooth", block: "start" });

  if (!data.results || data.results.length === 0) {
    grid.innerHTML = "";
    noRes.style.display = "block";
    countEl.textContent = "";
    return;
  }

  noRes.style.display = "none";
  countEl.textContent = `${data.count} college${data.count !== 1 ? "s" : ""} found`;
  titleEl.textContent = `Results for ${data.input.percentile} percentile`;

  grid.innerHTML = data.results.map(c => `
    <div class="college-card">
      <div class="card-top">
        <div class="college-name">${c.college_name}</div>
        <span class="badge ${c.chance}">${c.chance}</span>
      </div>
      <div class="card-meta">
        <span>📍 ${c.district}</span>
        <span>🎓 ${c.branch}</span>
      </div>
      <div class="cutoff-row">
        <span class="cutoff-label">Closing Cutoff (${c.category} · CAP ${c.cap_round})</span>
        <span class="cutoff-value">${c.cutoff_percentile.toFixed(2)}</span>
      </div>
    </div>
  `).join("");
}

// ── Allow Enter key on percentile input ──────────────
document.addEventListener("DOMContentLoaded", () => {
  loadMeta();
  document.getElementById("percentile")
    .addEventListener("keydown", e => { if (e.key === "Enter") predict(); });
});
