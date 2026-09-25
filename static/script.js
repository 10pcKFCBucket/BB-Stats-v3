// STEP 3: sorting and filtering, built on top of step 2's render logic.
//
// The key idea: keep the *original* data in one variable, and re-render
// from it every time the user sorts or filters. We never mutate the
// original array in place — we always sort/filter a copy. That way
// "clear the search box" or "click a different column" can always start
// fresh from the same source of truth instead of fighting stale data.

let allPlayers = [];          // the full list, loaded once from the API
let sortKey = null;           // which field we're currently sorted by
let sortDirection = 1;        // 1 = ascending, -1 = descending

async function loadStats() {
  const tableBody = document.getElementById("stats-body");

  try {
    // Only this line changed from step 2/3: instead of fetching a static
    // JSON file, we're fetching from our own Flask route. Same fetch(),
    // same .json(), same shape of data coming back — the server is just
    // building that JSON from a database query instead of reading a
    // file off disk. Everything below this line didn't need to change.
    const response = await fetch("/api/players");
    const players = await response.json();

    // Add a computed "average" field to each player up front, so sorting
    // by AVG has a real number to compare (we'll still *display* it as
    // ".347", but we sort on the underlying number).
    allPlayers = players.map((player) => ({
      ...player,
      average2: player.atBats === 0 ? 0 : player.hits / player.atBats,
    }));

    render(allPlayers);
    setupSorting();
    setupFiltering();
  } catch (error) {
    console.error("Couldn't load stats:", error);
    tableBody.innerHTML = `<tr><td colspan="8" class="loading">Couldn't load stats. Check the console.</td></tr>`;
  }
}

function render(players) {
  const tableBody = document.getElementById("stats-body");

  if (players.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="8" class="loading">No players match that search.</td></tr>`;
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
        <td>${player.walks}</td>
        <td>${player.homeRuns}</td>
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
        sortDirection = 1;
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

loadStats();
