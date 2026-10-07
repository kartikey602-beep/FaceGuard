// The dashboard derives its summary from the real personnel, area, and log APIs.
const { api, escapeHTML, statusBadge, resultBadge, formatDate, formatScore, showNotice } = window.FaceGuard;

function renderRecentLogs(logs) {
  const target = document.querySelector("#recent-events");
  if (!logs.length) {
    target.innerHTML = '<p class="empty-state">No access attempts have been recorded yet.</p>';
    return;
  }
  target.innerHTML = `<table class="data-table"><thead><tr><th>Time</th><th>Person</th><th>Area</th><th>Result</th><th>Match score</th></tr></thead><tbody>${logs.slice(0, 6).map((log) => `
    <tr><td class="timestamp">${escapeHTML(formatDate(log.timestamp))}</td><td class="name-cell">${escapeHTML(log.person_name || "Unknown")}${log.employee_id ? `<span class="sub-cell">${escapeHTML(log.employee_id)}</span>` : ""}</td><td>${escapeHTML(log.area_name)}</td><td>${resultBadge(log.result)}</td><td class="score">${escapeHTML(formatScore(log.match_score))}</td></tr>`).join("")}</tbody></table>`;
}

async function loadDashboard() {
  const error = document.querySelector("#dashboard-error");
  try {
    const [people, areas, logs] = await Promise.all([
      api("/api/personnel"), api("/api/areas"), api("/api/logs"),
    ]);
    const today = new Date().toISOString().slice(0, 10);
    const todaysLogs = logs.filter((log) => String(log.timestamp).slice(0, 10) === today);
    document.querySelector("#stat-personnel").textContent = people.length;
    document.querySelector("#stat-active-personnel").textContent = `${people.filter((person) => person.status === "ACTIVE").length} active`;
    document.querySelector("#stat-granted").textContent = todaysLogs.filter((log) => log.result === "ACCESS_GRANTED").length;
    document.querySelector("#stat-denied").textContent = todaysLogs.filter((log) => log.result === "ACCESS_DENIED").length;
    document.querySelector("#stat-areas").textContent = areas.filter((area) => area.status === "ACTIVE").length;
    document.querySelector("#stat-area-total").textContent = `${areas.length} configured area${areas.length === 1 ? "" : "s"}`;
    renderRecentLogs(logs);
  } catch (requestError) {
    showNotice(error, requestError.message);
    document.querySelector("#recent-events").innerHTML = '<p class="empty-state error-state">Dashboard data could not be loaded. Check the API connection.</p>';
  }
}

loadDashboard();
