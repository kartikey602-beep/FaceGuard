// Shared browser helpers keep API handling and formatting consistent.
window.FaceGuard = (() => {
  async function api(path, options = {}) {
    let response;
    try {
      response = await fetch(path, options);
    } catch (error) {
      throw new Error("Could not reach the FaceGuard backend. Check that the server is running.");
    }

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : null;
    if (!response.ok) {
      const detail = payload?.detail;
      const rawMessage = Array.isArray(detail)
        ? detail.map((item) => item.msg || "Invalid value").join("; ")
        : (detail || `Request failed (HTTP ${response.status}).`);
      const knownMessages = {
        DATABASE_ERROR: "The database could not complete this request.",
        EMPLOYEE_ID_ALREADY_EXISTS: "That employee ID is already in use.",
        EMPLOYEE_ID_ALREADY_EXISTS_OR_INVALID_STATUS: "The employee ID is already in use or the status is invalid.",
        AREA_NAME_ALREADY_EXISTS_OR_INVALID_STATUS: "The area name is already in use or the status is invalid.",
        PERMISSION_ALREADY_EXISTS: "This person already has permission for the area.",
        PERSONNEL_NOT_FOUND: "That personnel record could not be found.",
        PERSONNEL_INACTIVE: "This person is inactive. Activate them before granting access.",
        AREA_NOT_FOUND: "That area could not be found.",
        AREA_INACTIVE: "This area is inactive and cannot grant access.",
        AREA_NAME_REQUIRED: "Enter a name for the area.",
        ACCESS_LOG_NOT_FOUND: "That access log entry could not be found.",
        FACE_ENGINE_UNAVAILABLE: "The face recognition service is not ready. Check the backend setup.",
        NO_FIELDS_TO_UPDATE: "Make at least one change before saving.",
      };
      throw new Error(knownMessages[rawMessage] || String(rawMessage));
    }
    return payload;
  }

  function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);
  }

  function statusBadge(status) {
    const active = status === "ACTIVE";
    return `<span class="badge ${active ? "badge-active" : "badge-inactive"}">${active ? "Active" : "Inactive"}</span>`;
  }

  function resultBadge(result) {
    const granted = result === "ACCESS_GRANTED";
    return `<span class="badge ${granted ? "badge-granted" : "badge-denied"}">${granted ? "Granted" : "Denied"}</span>`;
  }

  function formatDate(value) {
    if (!value) return "—";
    const normalized = /Z$|[+-]\d\d:\d\d$/.test(value) ? value : `${value.replace(" ", "T")}Z`;
    const date = new Date(normalized);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  }

  function formatScore(value) {
    if (value === null || value === undefined) return "—";
    const score = Number(value);
    return (Object.is(score, -0) ? 0 : score).toFixed(4);
  }

  function showNotice(element, message, kind = "error") {
    if (!element) return;
    element.textContent = message;
    element.hidden = false;
    element.classList.toggle("notice-error", kind === "error");
    element.classList.toggle("notice-success", kind === "success");
  }

  function clearNotice(element) {
    if (element) { element.hidden = true; element.textContent = ""; }
  }

  function toast(message, kind = "success") {
    let region = document.querySelector(".toast-region");
    if (!region) {
      region = document.createElement("div");
      region.className = "toast-region";
      region.setAttribute("role", "status");
      document.body.append(region);
    }
    const item = document.createElement("div");
    item.className = "toast";
    item.dataset.kind = kind;
    item.textContent = message;
    region.append(item);
    window.setTimeout(() => item.remove(), 4200);
  }

  function setButtonLoading(button, loading, label = "Loading…") {
    if (!button) return;
    if (loading) {
      button.dataset.originalText = button.textContent.trim();
      button.disabled = true;
      button.textContent = label;
    } else {
      button.disabled = false;
      if (button.dataset.originalText) button.textContent = button.dataset.originalText;
      delete button.dataset.originalText;
    }
  }

  document.querySelectorAll("[data-nav]").forEach((link) => {
    if (link.dataset.nav === document.body.dataset.page) link.classList.add("active");
  });
  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => document.getElementById(button.dataset.closeDialog)?.close());
  });

  const health = document.querySelector("#api-status");
  if (health) {
    api("/api/health").then((body) => {
      health.innerHTML = `<span class="status-dot"></span>${escapeHTML(body.status === "ok" ? "API connected" : body.message)}`;
      health.dataset.state = "ok";
    }).catch(() => {
      health.innerHTML = '<span class="status-dot"></span>API unavailable';
      health.dataset.state = "error";
    });
  }

  return { api, escapeHTML, statusBadge, resultBadge, formatDate, formatScore, showNotice, clearNotice, toast, setButtonLoading };
})();
