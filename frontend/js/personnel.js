const { api, escapeHTML, statusBadge, showNotice, clearNotice, toast, setButtonLoading } = window.FaceGuard;
const dialog = document.querySelector("#personnel-dialog");
const form = document.querySelector("#personnel-form");
const notice = document.querySelector("#personnel-notice");
const formError = document.querySelector("#personnel-form-error");
let personnel = [];
let registeringId = null;

async function loadPersonnel() {
  const target = document.querySelector("#personnel-table");
  target.innerHTML = '<p class="loading-state">Loading personnel…</p>';
  try {
    personnel = await api("/api/personnel");
    renderPersonnel();
    clearNotice(notice);
  } catch (error) {
    target.innerHTML = '<p class="empty-state error-state">Personnel could not be loaded.</p>';
    showNotice(notice, error.message);
  }
}

function renderPersonnel() {
  const search = document.querySelector("#personnel-search").value.trim().toLowerCase();
  const shown = personnel.filter((person) => [person.employee_id, person.name, person.department, person.role].join(" ").toLowerCase().includes(search));
  document.querySelector("#personnel-count").textContent = `${shown.length} of ${personnel.length} personnel`;
  if (!shown.length) {
    document.querySelector("#personnel-table").innerHTML = `<p class="empty-state">${personnel.length ? "No personnel match this search." : "No personnel records yet. Add a person to get started."}</p>`;
    return;
  }
  document.querySelector("#personnel-table").innerHTML = `<table class="data-table"><thead><tr><th>Employee ID</th><th>Name</th><th>Department</th><th>Role</th><th>Status</th><th>Actions</th></tr></thead><tbody>${shown.map((person) => `
    <tr><td>${escapeHTML(person.employee_id)}</td><td class="name-cell">${escapeHTML(person.name)}</td><td>${escapeHTML(person.department || "—")}</td><td>${escapeHTML(person.role || "—")}</td><td>${statusBadge(person.status)}</td><td><div class="row-actions"><button class="small-button" data-action="edit" data-id="${person.id}">Edit</button><button class="small-button" data-action="toggle" data-id="${person.id}">${person.status === "ACTIVE" ? "Deactivate" : "Activate"}</button><button class="small-button" data-action="face" data-id="${person.id}">Register face</button></div></td></tr>`).join("")}</tbody></table>`;
}

function openForm(person = null) {
  clearNotice(formError);
  form.reset();
  form.elements.id.value = person?.id || "";
  document.querySelector("#personnel-dialog-title").textContent = person ? "Edit personnel" : "Add personnel";
  if (person) {
    for (const field of ["employee_id", "name", "department", "role", "status"]) form.elements[field].value = person[field] ?? "";
  }
  dialog.showModal();
}

document.querySelector("#add-personnel").addEventListener("click", () => openForm());
document.querySelector("#personnel-search").addEventListener("input", renderPersonnel);
document.querySelector("#personnel-table").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const person = personnel.find((item) => item.id === Number(button.dataset.id));
  if (!person) return;
  if (button.dataset.action === "edit") return openForm(person);
  if (button.dataset.action === "face") {
    registeringId = person.id;
    document.querySelector("#face-file").click();
    return;
  }
  if (button.dataset.action === "toggle") {
    button.disabled = true;
    try {
      await api(`/api/personnel/${person.id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: person.status === "ACTIVE" ? "INACTIVE" : "ACTIVE" }) });
      toast(`${person.name} status updated.`);
      await loadPersonnel();
    } catch (error) { showNotice(notice, error.message); button.disabled = false; }
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearNotice(formError);
  const button = form.querySelector('[type="submit"]');
  setButtonLoading(button, true, "Saving…");
  const values = Object.fromEntries(new FormData(form).entries());
  const id = values.id;
  delete values.id;
  for (const key of ["department", "role"]) if (!values[key]) values[key] = null;
  try {
    await api(id ? `/api/personnel/${id}` : "/api/personnel", { method: id ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
    dialog.close();
    toast(id ? "Personnel record updated." : "Personnel record created.");
    await loadPersonnel();
  } catch (error) { showNotice(formError, error.message); }
  finally { setButtonLoading(button, false); }
});

document.querySelector("#face-file").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file || !registeringId) return;
  const body = new FormData();
  body.append("image", file);
  try {
    const response = await api(`/api/personnel/${registeringId}/register-face`, { method: "POST", body });
    toast(`Face registered with ${response.model_name}.`);
    clearNotice(notice);
  } catch (error) {
    const friendly = { INVALID_IMAGE: "Choose a readable image file.", NO_FACE_DETECTED: "No face was detected in this image.", MULTIPLE_FACES_DETECTED: "Use an image containing only one face.", PERSONNEL_INACTIVE: "Activate this person before registering a face." };
    showNotice(notice, friendly[error.message] || error.message);
  } finally { event.target.value = ""; registeringId = null; }
});

loadPersonnel();

