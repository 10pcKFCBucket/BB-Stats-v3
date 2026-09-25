// Two dropdowns now: one for year, one for league within that year
// (or "All Leagues" / "Career" as special cases). The year dropdown
// drives what options appear in the league dropdown.

let allPlayers = [];          // the full list, loaded once from the API
let sortKey = null;           // which field we're currently sorted by
let sortDirection = 1;        // 1 = ascending, -1 = descending
let seasonsByYear = new Map(); // year -> [{id, league}, ...], filled in by loadSeasons

async function init() {
  await loadSeasons();
  setupSorting();
  setupFiltering();
  document.getElementById("year-select").addEventListener("change", () => {
    populateLeagueOptions();
    loadStats();
  });
  document.getElementById("league-select").addEventListener("change", loadStats);
  await loadStats();
}

async function loadSeasons() {
  const yearSelect = document.getElementById("year-select");

  try {
    const response = await fetch("/api/seasons");
    const seasons = await response.json();

    // Group by year so the league dropdown can be rebuilt from this
    // whenever the year changes, without fetching again.
    seasonsByYear = new Map();
    seasons.forEach((season) => {
      if (!seasonsByYear.has(season.year)) seasonsByYear.set(season.year, []);
      seasonsByYear.get(season.year).push(season);
    });

    yearSelect.innerHTML = "";

    const careerOption = document.createElement("option");
    careerOption.value = "career";
    careerOption.textContent = "Career";
    yearSelect.appendChild(careerOption);

    // Map preserves insertion order, and the API already returns
    // seasons most-recent-year-first, so this loop naturally lists
    // years newest to oldest.
    for (const year of seasonsByYear.keys()) {
      const option = document.createElement("option");
      option.value = year;
      option.textContent = year;
      yearSelect.appendChild(option);
    }

    // Default to the most recent actual year, not "Career" — the
    // career option is opt-in, not the default view.
    if (seasonsByYear.size > 0) {
      yearSelect.value = [...seasonsByYear.keys()][0];
    }

    populateLeagueOptions();
  } catch (error) {
    console.error("Couldn't load seasons:", error);
  }
}

function populateLeagueOptions() {
  const yearSelect = document.getElementById("year-select");
  const leagueSelect = document.getElementById("league-select");
  const year = yearSelect.value;

  leagueSelect.innerHTML = "";

  if (year === "career") {
    // A league selection is meaningless in career mode — one games,
    // one disabled placeholder option so it's clearly not usable
    // rather than confusingly still clickable.
    const option = document.createElement("option");
    option.textContent = "N/A";
    leagueSelect.appendChild(option);
    leagueSelect.disabled = true;
    return;
  }

  leagueSelect.disabled = false;
  const leaguesInYear = seasonsByYear.get(Number(year)) || [];

  if (leaguesInYear.length > 1) {
    const allOption = document.createElement("option");
    allOption.value = "all";
    allOption.textContent = "All Leagues";
    leagueSelect.appendChild(allOption);
  }

  leaguesInYear.forEach((season) => {
    const option = document.createElement("option");
    option.value = season.id;
    option.textContent = season.league;
    leagueSelect.appendChild(option);
  });
}

async function loadStats() {
  const tableBody = document.getElementById("stats-body");
  const yearSelect = document.getElementById("year-select");
  const leagueSelect = document.getElementById("league-select");

  let queryParam;
  if (yearSelect.value === "career") {
    queryParam = "career=1";
  } else if (leagueSelect.value === "all") {
    queryParam = `year=${yearSelect.value}`;
  } else {
    queryParam = `season_id=${leagueSelect.value}`;
  }

  try {
    const response = await fetch(`/api/players?${queryParam}`);
    const players = await response.json();

    allPlayers = players.map((player) => ({
      ...player,
      average2: player.atBats === 0 ? 0 : player.hits / player.atBats,
    }));

    // Re-apply whatever sort/search is already active, rather than a
    // plain render() — this keeps your sort column and search text in
    // place when you switch seasons instead of resetting them.
    applySortAndFilter();
  } catch (error) {
    console.error("Couldn't load stats:", error);
    tableBody.innerHTML = `<tr><td colspan="17" class="loading">Couldn't load stats. Check the console.</td></tr>`;
  }
}


function render(players) {
  const tableBody = document.getElementById("stats-body");

  if (players.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="17" class="loading">No players match that search.</td></tr>`;
    return;
  }

  const rows = players
    .map((player) => `
      <tr>
        <td class="player-name">${player.name}</td>
        <td>${player.games}</td>
        <td>${player.plateAppearances}</td>
        <td>${player.atBats}</td>
        <td>${player.hits}</td>
        <td>${player.singles}</td>
        <td>${player.doubles}</td>
        <td>${player.triples}</td>
        <td>${player.homeRuns}</td>
        <td>${player.walks}</td>
        <td>${player.rbi}</td>
        <td>${player.runs}</td>
        <td>${player.totalBases}</td>
        <td>${player.average}</td>
        <td>${player.obp}</td>
        <td>${player.slg}</td>
        <td>${player.ops}</td>
      </tr>
    `)
    .join("");

  tableBody.innerHTML = rows;
}

function formatAverage(average) {
  return average.toFixed(3).replace(/^0/, "");
}

// --- Sorting ---------------------------------------------------------

function setupSorting() {
  const headers = document.querySelectorAll("#stats-table th.sortable");

  headers.forEach((header) => {
    header.addEventListener("click", () => {
      const key = header.dataset.key; // reads the data-key="..." attribute from the HTML

      if (sortKey === key) {
        // Clicking the same column again flips the direction instead of
        // re-sorting the same way twice.
        sortDirection *= -1;
      } else {
        sortKey = key;
        sortDirection = -1;
      }

      updateSortIndicators(headers, header);
      applySortAndFilter();
    });
  });
}

function updateSortIndicators(allHeaders, activeHeader) {
  allHeaders.forEach((h) => h.classList.remove("sort-asc", "sort-desc"));
  activeHeader.classList.add(sortDirection === 1 ? "sort-asc" : "sort-desc");
}

// --- Filtering ---------------------------------------------------------

function setupFiltering() {
  const searchInput = document.getElementById("player-search");

  searchInput.addEventListener("input", () => {
    applySortAndFilter();
  });
}

// Re-derives the visible list from allPlayers every time, applying
// whatever filter text and sort settings are currently active — this is
// the "always start fresh from the source of truth" idea from the top
// of the file, in practice.
function applySortAndFilter() {
  const searchInput = document.getElementById("player-search");
  const query = searchInput.value.trim().toLowerCase();

  let visible = allPlayers.filter((player) =>
    player.name.toLowerCase().includes(query)
  );

  if (sortKey) {
    visible = [...visible].sort((a, b) => {
      const valA = a[sortKey];
      const valB = b[sortKey];

      if (typeof valA === "string") {
        return valA.localeCompare(valB) * sortDirection;
      }
      return (valA - valB) * sortDirection;
    });
  }

  render(visible);
}

init();
