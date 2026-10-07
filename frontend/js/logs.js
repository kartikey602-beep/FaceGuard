const { api, escapeHTML, resultBadge, formatDate, formatScore, showNotice } = window.FaceGuard;
let logRows = [];
let areaRows = [];

async function loadLogs() {
  const target = document.querySelector("#logs-table");
  target.innerHTML = '<p class="loading-state">Loading access logs…</p>';
  try {
    const areaId = document.querySelector("#filter-area").value;
    const result = document.querySelector("#filter-result").value;
    const date = document.querySelector("#filter-date").value;
    const params = new URLSearchParams();
    if (areaId) params.set("area_id", areaId);
    if (result) params.set("result", result);
    if (date) params.set("date", date);
    logRows = await api(`/api/logs${params.size ? `?${params}` : ""}`);
    renderLogs();
    document.querySelector("#logs-error").hidden = true;
  } catch (error) {
    target.innerHTML = '<p class="empty-state error-state">Access logs could not be loaded.</p>';
    showNotice(document.querySelector("#logs-error"), error.message);
  }
}

function renderLogs() {
  const search = document.querySelector("#filter-person").value.trim().toLowerCase();
  const shown = logRows.filter((log) => `${log.person_name || ""} ${log.employee_id || ""}`.toLowerCase().includes(search));
  document.querySelector("#log-count").textContent = `${shown.length} event${shown.length === 1 ? "" : "s"}${shown.length !== logRows.length ? ` · ${logRows.length} loaded` : ""}`;
  if (!shown.length) {
    document.querySelector("#logs-table").innerHTML = `<p class="empty-state">${logRows.length ? "No events match this person search." : "No access attempts match these filters."}</p>`;
    return;
  }
  document.querySelector("#logs-table").innerHTML = `<table class="data-table"><thead><tr><th>Timestamp</th><th>Person</th><th>Area</th><th>Result</th><th>Match score</th><th>Reason</th></tr></thead><tbody>${shown.map((log) => `
    <tr><td class="timestamp">${escapeHTML(formatDate(log.timestamp))}</td><td class="name-cell">${escapeHTML(log.person_name || "Unknown")}${log.employee_id ? `<span class="sub-cell">${escapeHTML(log.employee_id)}</span>` : ""}</td><td>${escapeHTML(log.area_name)}</td><td>${resultBadge(log.result)}</td><td class="score">${escapeHTML(formatScore(log.match_score))}</td><td>${escapeHTML(log.reason || "—")}</td></tr>`).join("")}</tbody></table>`;
}

async function loadAreas() {
  try {
    areaRows = await api("/api/areas");
    document.querySelector("#filter-area").innerHTML = '<option value="">All areas</option>' + areaRows.map((area) => `<option value="${area.id}">${escapeHTML(area.name)}</option>`).join("");
  } catch (error) { showNotice(document.querySelector("#logs-error"), error.message); }
}

document.querySelector("#refresh-logs").addEventListener("click", loadLogs);
document.querySelector("#filter-area").addEventListener("change", loadLogs);
document.querySelector("#filter-result").addEventListener("change", loadLogs);
document.querySelector("#filter-date").addEventListener("change", loadLogs);
document.querySelector("#filter-person").addEventListener("input", renderLogs);
document.querySelector("#clear-filters").addEventListener("click", () => {
  document.querySelector("#filter-area").value = "";
  document.querySelector("#filter-result").value = "";
  document.querySelector("#filter-date").value = "";
  document.querySelector("#filter-person").value = "";
  loadLogs();
});

loadAreas().then(loadLogs);
