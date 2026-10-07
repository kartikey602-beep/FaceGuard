const { api, escapeHTML, statusBadge, showNotice, clearNotice, toast, setButtonLoading } = window.FaceGuard;
const areaDialog = document.querySelector("#area-dialog");
const areaForm = document.querySelector("#area-form");
const areaNotice = document.querySelector("#areas-notice");
const permissionDialog = document.querySelector("#permissions-dialog");
const permissionForm = document.querySelector("#permission-form");
const permissionError = document.querySelector("#permissions-error");
let areas = [];
let people = [];
let currentArea = null;
let permissions = [];

async function loadAreas() {
  const target = document.querySelector("#area-list");
  target.innerHTML = '<p class="loading-state">Loading areas…</p>';
  try {
    const [areaRows, personnelRows] = await Promise.all([api("/api/areas"), api("/api/personnel")]);
    areas = areaRows;
    people = personnelRows;
    const permissionRows = await Promise.all(areas.map((area) => api(`/api/areas/${area.id}/permissions`)));
    areas = areas.map((area, index) => ({ ...area, authorizedCount: permissionRows[index].filter((person) => person.status === "ACTIVE").length }));
    renderAreas();
    clearNotice(areaNotice);
  } catch (error) {
    target.innerHTML = '<p class="empty-state error-state">Area information could not be loaded.</p>';
    showNotice(areaNotice, error.message);
  }
}

function renderAreas() {
  const target = document.querySelector("#area-list");
  if (!areas.length) {
    target.innerHTML = '<div class="panel"><p class="empty-state">No areas have been created yet.</p></div>';
    return;
  }
  target.innerHTML = areas.map((area) => `<article class="area-card"><div class="area-card-head"><div><h3>${escapeHTML(area.name)}</h3><p>${escapeHTML(area.description || "No description provided.")}</p></div>${statusBadge(area.status)}</div><div class="area-count"><strong>${area.authorizedCount}</strong><span>active authorized personnel</span></div><div class="area-card-actions"><button class="small-button" data-action="edit" data-id="${area.id}">Edit area</button><button class="small-button" data-action="toggle" data-id="${area.id}">${area.status === "ACTIVE" ? "Deactivate" : "Activate"}</button><button class="small-button" data-action="permissions" data-id="${area.id}">Manage access</button></div></article>`).join("");
}

function openAreaForm(area = null) {
  clearNotice(document.querySelector("#area-form-error"));
  areaForm.reset();
  areaForm.elements.id.value = area?.id || "";
  document.querySelector("#area-dialog-title").textContent = area ? "Edit area" : "Add area";
  if (area) {
    areaForm.elements.name.value = area.name;
    areaForm.elements.description.value = area.description || "";
    areaForm.elements.status.value = area.status;
  }
  areaDialog.showModal();
}

document.querySelector("#add-area").addEventListener("click", () => openAreaForm());
document.querySelector("#area-list").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const area = areas.find((item) => item.id === Number(button.dataset.id));
  if (!area) return;
  if (button.dataset.action === "edit") return openAreaForm(area);
  if (button.dataset.action === "permissions") return openPermissions(area);
  button.disabled = true;
  try {
    await api(`/api/areas/${area.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: area.status === "ACTIVE" ? "INACTIVE" : "ACTIVE" }) });
    toast(`${area.name} status updated.`);
    await loadAreas();
  } catch (error) { showNotice(areaNotice, error.message); button.disabled = false; }
});

areaForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const errorBox = document.querySelector("#area-form-error");
  clearNotice(errorBox);
  const submit = areaForm.querySelector('[type="submit"]');
  setButtonLoading(submit, true, "Saving…");
  const data = Object.fromEntries(new FormData(areaForm).entries());
  const id = data.id;
  delete data.id;
  if (!data.description) data.description = null;
  try {
    await api(id ? `/api/areas/${id}` : "/api/areas", { method: id ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    areaDialog.close();
    toast(id ? "Area updated." : "Area created.");
    await loadAreas();
  } catch (error) { showNotice(errorBox, error.message); }
  finally { setButtonLoading(submit, false); }
});

async function openPermissions(area) {
  currentArea = area;
  document.querySelector("#permissions-title").textContent = `Access · ${area.name}`;
  clearNotice(permissionError);
  permissionDialog.showModal();
  await loadPermissions();
}

async function loadPermissions() {
  const list = document.querySelector("#permission-list");
  list.innerHTML = '<p class="loading-state">Loading permissions…</p>';
  try {
    permissions = await api(`/api/areas/${currentArea.id}/permissions`);
    const activePeople = people.filter((person) => person.status === "ACTIVE" && !permissions.some((permission) => permission.personnel_id === person.id));
    permissionForm.elements.personnel_id.innerHTML = '<option value="">Choose a person</option>' + activePeople.map((person) => `<option value="${person.id}">${escapeHTML(person.name)} · ${escapeHTML(person.employee_id)}</option>`).join("");
    permissionForm.querySelector("button[type=submit]").disabled = currentArea.status !== "ACTIVE" || activePeople.length === 0;
    if (currentArea.status !== "ACTIVE") showNotice(permissionError, "Activate this area before adding permissions.");
    else clearNotice(permissionError);
    if (!permissions.length) {
      list.innerHTML = '<p class="empty-state">No permission links are assigned to this area.</p>';
      return;
    }
    list.innerHTML = permissions.map((person) => `<div class="permission-row"><div><strong>${escapeHTML(person.name)}</strong><small>${escapeHTML(person.employee_id)} · ${escapeHTML(person.department || "No department")} · ${escapeHTML(person.status)}</small></div><button class="small-button danger" data-revoke="${person.personnel_id}" type="button">Revoke</button></div>`).join("");
  } catch (error) {
    list.innerHTML = '<p class="empty-state error-state">Permissions could not be loaded.</p>';
    showNotice(permissionError, error.message);
  }
}

permissionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const personnelId = permissionForm.elements.personnel_id.value;
  if (!personnelId || !currentArea) return;
  const button = permissionForm.querySelector("button[type=submit]");
  setButtonLoading(button, true, "Adding…");
  try {
    await api(`/api/areas/${currentArea.id}/permissions/${personnelId}`, { method: "POST" });
    await loadPermissions();
    await loadAreas();
    toast("Area permission added.");
  } catch (error) { showNotice(permissionError, error.message); }
  finally {
    setButtonLoading(button, false);
    const remaining = people.some((person) => person.status === "ACTIVE" && !permissions.some((permission) => permission.personnel_id === person.id));
    button.disabled = currentArea.status !== "ACTIVE" || !remaining;
  }
});

document.querySelector("#permission-list").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-revoke]");
  if (!button || !currentArea) return;
  button.disabled = true;
  try {
    await api(`/api/areas/${currentArea.id}/permissions/${button.dataset.revoke}`, { method: "DELETE" });
    await loadPermissions();
    await loadAreas();
    toast("Area permission removed.");
  } catch (error) { showNotice(permissionError, error.message); button.disabled = false; }
});

loadAreas();

