const LANG = { current: "en" };

async function loadData() {
  const res = await fetch("data/roma.json");
  if (!res.ok) {
    console.error("Failed to load data");
    return;
  }
  const data = await res.json();
  renderLastMatch(data);
  renderNextMatch(data);
  renderStandings(data);
  renderSquad(data);
}

function renderLastMatch(data) {
  const container = document.getElementById("last-match-card");
  const m = data.last_match;
  if (!m) {
    container.textContent = "No match data yet.";
    return;
  }
  const lang = LANG.current;
  // Very basic text rendering for v1; later we’ll use card images.
  container.innerHTML = `
    <p><strong>Competition:</strong> ${m.league?.name || "—"}</p>
    <p><strong>Date:</strong> ${m.starting_at}</p>
    <p><strong>Result:</strong> ${formatScore(m, lang)}</p>
  `;
}

function renderNextMatch(data) {
  const container = document.getElementById("next-match-card");
  const m = data.next_match;
  if (!m) {
    container.textContent = "No upcoming match.";
    return;
  }
  container.innerHTML = `
    <p><strong>Competition:</strong> ${m.league?.name || "—"}</p>
    <p><strong>Date:</strong> ${m.starting_at}</p>
    <p><strong>Fixture:</strong> ${formatFixture(m)}</p>
  `;
}

function renderStandings(data) {
  const container = document.getElementById("standings-card");
  if (!data.standings?.length) {
    container.textContent = "No standings data.";
    return;
  }
  const rows = data.standings
    .map(s => {
      const r = s.row;
      if (!r) return null;
      return `${s.competition_name_en}: ${r.position} – ${r.points} pts`;
    })
    .filter(Boolean);
  container.innerHTML = rows.map(r => `<p>${r}</p>`).join("");
}

function renderSquad(data) {
  const container = document.getElementById("squad-list");
  if (!data.squad?.length) {
    container.textContent = "No squad data.";
    return;
  }
  const items = data.squad.map(entry => {
    const p = entry.player;
    const pos = entry.position?.name || "—";
    const num = entry.squad_number ?? "—";
    return `
      <div class="player-item">
        <strong>${p.display_name}</strong><br>
        <small>${pos} • #${num}</small>
      </div>
    `;
  });
  container.innerHTML = items.join("");
}

function formatScore(m, lang) {
  const home = m.participants?.find(p => p.meta?.home);
  const away = m.participants?.find(p => !p.meta?.home);
  if (!home || !away) return "—";
  return `${home.name} ${home.result?.goals} – ${away.result?.goals} ${away.name}`;
}

function formatFixture(m) {
  const home = m.participants?.find(p => p.meta?.home);
  const away = m.participants?.find(p => !p.meta?.home);
  if (!home || !away) return "—";
  return `${home.name} vs ${away.name}`;
}

document.getElementById("lang-en").addEventListener("click", () => {
  LANG.current = "en";
  document.getElementById("lang-en").classList.add("active");
  document.getElementById("lang-bg").classList.remove("active");
  loadData();
});

document.getElementById("lang-bg").addEventListener("click", () => {
  LANG.current = "bg";
  document.getElementById("lang-bg").classList.add("active");
  document.getElementById("lang-en").classList.remove("active");
  loadData();
});

document.addEventListener("DOMContentLoaded", loadData);
