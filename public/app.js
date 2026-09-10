const DATA_URL = "./data/roma.json";

const translations = {
  en: {
    liveData: "Data dashboard",
    channelLabel: "CHANNEL",
    heroTitle: "AS Roma, match by match.",
    heroDescription: "Results, fixtures, standings and squad information in one place.",
    lastMatch: "LAST MATCH",
    nextMatch: "NEXT MATCH",
    tournamentState: "TOURNAMENT STATE",
    serieA: "Serie A",
    clubProfile: "CLUB PROFILE",
    fixtures: "FIXTURES",
    recentAndUpcoming: "Recent and upcoming",
    recentResults: "Recent results",
    upcomingFixtures: "Upcoming fixtures",
    squad: "SQUAD",
    firstTeam: "First team",
    dataCredit: "Data from football-data.org and TheSportsDB",
    noMatch: "No match data available.",
    noFixtures: "No fixtures available.",
    noSquad: "No squad data available.",
    home: "HOME",
    away: "AWAY",
    venue: "Venue",
    position: "Position",
    points: "points",
    record: "Record",
    played: "Played",
    form: "Form",
    unknown: "Unknown",
    updated: "Updated"
  },
  bg: {
    liveData: "Табло с данни",
    channelLabel: "КАНАЛ",
    heroTitle: "АС Рома, мач след мач.",
    heroDescription: "Резултати, програма, класиране и състав на едно място.",
    lastMatch: "ПОСЛЕДЕН МАЧ",
    nextMatch: "СЛЕДВАЩ МАЧ",
    tournamentState: "СЪСТОЯНИЕ НА ТУРНИРА",
    serieA: "Серия А",
    clubProfile: "ПРОФИЛ НА КЛУБА",
    fixtures: "ПРОГРАМА",
    recentAndUpcoming: "Последни и предстоящи",
    recentResults: "Последни резултати",
    upcomingFixtures: "Предстоящи мачове",
    squad: "СЪСТАВ",
    firstTeam: "Първи отбор",
    dataCredit: "Данни от football-data.org и TheSportsDB",
    noMatch: "Няма налични данни за мача.",
    noFixtures: "Няма налична програма.",
    noSquad: "Няма налични данни за състава.",
    home: "ДОМАКИН",
    away: "ГОСТ",
    venue: "Стадион",
    position: "Позиция",
    points: "точки",
    record: "Баланс",
    played: "Изиграни",
    form: "Форма",
    unknown: "Неизвестно",
    updated: "Обновено"
  }
};

const state = {
  language: "en",
  data: null
};

const elements = {};

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  bindEvents();
  loadData();
});

function cacheElements() {
  elements.error = document.getElementById("error-message");
  elements.updatedAt = document.getElementById("updated-at");

  elements.lastMatch = document.getElementById("last-match");
  elements.lastCompetition = document.getElementById("last-match-competition");
  elements.lastStatus = document.getElementById("last-match-status");

  elements.nextMatch = document.getElementById("next-match");
  elements.nextCompetition = document.getElementById("next-match-competition");
  elements.nextStatus = document.getElementById("next-match-status");

  elements.standingSummary = document.getElementById("standing-summary");
  elements.clubProfile = document.getElementById("club-profile");

  elements.recentFixtures = document.getElementById("recent-fixtures");
  elements.upcomingFixtures = document.getElementById("upcoming-fixtures");
  elements.fixtureCount = document.getElementById("fixture-count");

  elements.squadList = document.getElementById("squad-list");
  elements.squadCount = document.getElementById("squad-count");
  elements.squadSection = document.getElementById("squad-section");
}

function bindEvents() {
  document.querySelectorAll("[data-language]").forEach((button) => {
    button.addEventListener("click", () => {
      state.language = button.dataset.language;

      document.querySelectorAll("[data-language]").forEach((item) => {
        item.classList.toggle(
          "is-active",
          item.dataset.language === state.language
        );
      });

      applyTranslations();

      if (state.data) {
        renderAll(state.data);
      }
    });
  });
}

async function loadData() {
  try {
    const response = await fetch(DATA_URL, {
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error(`Data request failed with HTTP ${response.status}`);
    }

    state.data = await response.json();
    hideError();
    applyTranslations();
    renderAll(state.data);
  } catch (error) {
    console.error(error);
    showError(
      "Could not load AS Roma data. The first generated data snapshot may not have been published yet."
    );
  }
}

function applyTranslations() {
  const dictionary = translations[state.language];

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;

    if (dictionary[key]) {
      element.textContent = dictionary[key];
    }
  });
}

function renderAll(data) {
  renderUpdatedAt(data);
  renderLastMatch(data.last_match);
  renderNextMatch(data.next_match);
  renderStanding(data.standings?.serie_a?.roma);
  renderClubProfile(data);
  renderFixtures(data);

  const showSquad = data.meta?.show_squad ?? false;

  if (elements.squadSection) {
    elements.squadSection.classList.toggle("is-hidden", !showSquad);
  }

  if (showSquad) {
    renderSquad(data.squad);
  }
}

function renderUpdatedAt(data) {
  const generatedAt = data.meta?.generated_at_utc;

  if (!generatedAt) {
    elements.updatedAt.textContent = "—";
    return;
  }

  const date = new Date(generatedAt);

  elements.updatedAt.textContent = `${t("updated")}: ${formatDateTime(date)}`;
}

function renderLastMatch(match) {
  elements.lastCompetition.textContent = getCompetitionName(match);
  elements.lastStatus.textContent = match?.status || "FINISHED";

  if (!match) {
    elements.lastMatch.innerHTML = emptyState(t("noMatch"));
    return;
  }

  elements.lastMatch.innerHTML = renderMatchContent(match, false);
}

function renderNextMatch(match) {
  elements.nextCompetition.textContent = getCompetitionName(match);
  elements.nextStatus.textContent = match?.status || "SCHEDULED";

  if (!match) {
    elements.nextMatch.innerHTML = emptyState(t("noMatch"));
    return;
  }

  elements.nextMatch.innerHTML = renderMatchContent(match, true);
}

function renderMatchContent(match, isUpcoming) {
  const homeTeam = match.home_team?.name || t("unknown");
  const awayTeam = match.away_team?.name || t("unknown");
  const score = getScore(match);
  const date = match.utc_date ? new Date(match.utc_date) : null;

  return `
    <p class="match-date">${date ? formatDateTime(date) : "—"}</p>
    <div class="match-teams">
      <div class="match-team">
        <span>${escapeHtml(homeTeam)}</span>
        <span class="team-note">${t("home")}</span>
      </div>
      <div class="match-score ${isUpcoming ? "pending" : ""}">
        ${escapeHtml(score)}
      </div>
      <div class="match-team">
        <span>${escapeHtml(awayTeam)}</span>
        <span class="team-note">${t("away")}</span>
      </div>
    </div>
    ${
      isUpcoming
        ? `<p class="match-venue">${escapeHtml(
            `${t("venue")}: ${getVenue(match)}`
          )}</p>`
        : ""
    }
  `;
}

function renderStanding(standing) {
  if (!standing) {
    elements.standingSummary.innerHTML = emptyState(t("noMatch"));
    return;
  }

  const position = standing.position ?? "—";
  const points = standing.points ?? "—";
  const played = standing.played_games ?? "—";
  const won = standing.won ?? "—";
  const draw = standing.draw ?? "—";
  const lost = standing.lost ?? "—";
  const form = standing.form || "—";

  elements.standingSummary.innerHTML = `
    <div class="standing-position">${escapeHtml(String(position))}</div>
    <div>
      <p class="standing-label">${t("position")}</p>
      <p class="standing-points">
        ${escapeHtml(String(points))} ${t("points")}
      </p>
      <div class="standing-record">
        <span class="stat-pill">${t("played")}: ${escapeHtml(String(played))}</span>
        <span class="stat-pill">${t("record")}: ${escapeHtml(String(won))}-${escapeHtml(String(draw))}-${escapeHtml(String(lost))}</span>
        <span class="stat-pill">${t("form")}: ${escapeHtml(String(form))}</span>
      </div>
    </div>
  `;
}

function renderClubProfile(data) {
  const team = data.team?.football_data || {};
  const artwork = data.team?.artwork || {};

  const crest = team.crest || artwork.badge || artwork.logo || "";
  const venue = team.venue || artwork.stadium || t("unknown");
  const founded = team.founded || "—";

  elements.clubProfile.innerHTML = `
    ${
      crest
        ? `<img class="club-crest" src="${escapeAttribute(crest)}" alt="AS Roma logo">`
        : `<div class="club-crest club-crest-placeholder">ROMA</div>`
    }
    <div class="club-profile-text">
      <strong>${escapeHtml(getLocalizedTeamName())}</strong>
      <span>${escapeHtml(`${t("venue")}: ${venue}`)}</span>
      <span>${escapeHtml(`Founded: ${founded}`)}</span>
    </div>
  `;
}

function renderFixtures(data) {
  const recent = data.recent_matches || [];
  const upcoming = data.upcoming_matches || [];

  elements.fixtureCount.textContent = `${recent.length + upcoming.length} ${state.language === "bg" ? "мачове" : "matches"}`;

  elements.recentFixtures.innerHTML = recent.length
    ? recent.map((match) => renderFixtureRow(match, false)).join("")
    : emptyState(t("noFixtures"));

  elements.upcomingFixtures.innerHTML = upcoming.length
    ? upcoming.map((match) => renderFixtureRow(match, true)).join("")
    : emptyState(t("noFixtures"));
}

function renderFixtureRow(match, upcoming) {
  const date = match.utc_date ? new Date(match.utc_date) : null;
  const opponent = getOpponent(match);
  const score = getScore(match);

  return `
    <div class="fixture-row">
      <span class="fixture-date">${date ? formatDate(date) : "—"}</span>
      <span class="fixture-opponents">
        <strong>${escapeHtml(opponent)}</strong>
        <span>${escapeHtml(getCompetitionName(match))}</span>
      </span>
      <span class="fixture-score ${upcoming ? "pending" : ""}">
        ${escapeHtml(upcoming ? "vs" : score)}
      </span>
    </div>
  `;
}

function renderSquad(squad) {
  if (!Array.isArray(squad) || squad.length === 0) {
    elements.squadCount.textContent = "—";
    elements.squadList.innerHTML = emptyState(t("noSquad"));
    return;
  }

  elements.squadCount.textContent = `${squad.length} ${state.language === "bg" ? "играчи" : "players"}`;

  elements.squadList.innerHTML = squad
    .map((player) => {
      const number = player.shirt_number ?? "—";
      const position = player.position || t("unknown");
      const nationality = player.nationality || "";

      return `
        <article class="player-card">
          <span class="player-number">${escapeHtml(String(number))}</span>
          <span>
            <strong class="player-name">${escapeHtml(player.name || t("unknown"))}</strong>
            <small class="player-info">${escapeHtml(position)}${nationality ? ` · ${escapeHtml(nationality)}` : ""}</small>
          </span>
        </article>
      `;
    })
    .join("");
}

function getScore(match) {
  const fullTime = match.score?.full_time || {};
  const home = fullTime.home;
  const away = fullTime.away;

  if (home === null || home === undefined || away === null || away === undefined) {
    return "—";
  }

  return `${home} – ${away}`;
}

function getOpponent(match) {
  const home = match.home_team?.name || "";
  const away = match.away_team?.name || "";

  if (isRoma(home)) {
    return away;
  }

  return home;
}

function getVenue(match) {
  return match.venue || match.stadium || "—";
}

function getCompetitionName(match) {
  return (
    match?.competition?.name ||
    (state.language === "bg" ? "Състезание" : "Competition")
  );
}

function getLocalizedTeamName() {
  return state.language === "bg" ? "АС Рома" : "AS Roma";
}

function isRoma(name) {
  return /roma/i.test(name || "");
}

function formatDate(date) {
  return new Intl.DateTimeFormat(
    state.language === "bg" ? "bg-BG" : "en-GB",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "Europe/Rome"
    }
  ).format(date);
}

function formatDateTime(date) {
  return new Intl.DateTimeFormat(
    state.language === "bg" ? "bg-BG" : "en-GB",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Europe/Rome"
    }
  ).format(date);
}

function emptyState(message) {
  return `<p class="empty-state">${escapeHtml(message)}</p>`;
}

function showError(message) {
  elements.error.textContent = message;
  elements.error.classList.remove("is-hidden");
}

function hideError() {
  elements.error.classList.add("is-hidden");
  elements.error.textContent = "";
}

function t(key) {
  return translations[state.language][key] || key;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
