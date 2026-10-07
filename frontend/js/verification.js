const { api, escapeHTML, formatDate, formatScore, showNotice, clearNotice, setButtonLoading } = window.FaceGuard;
const imageInput = document.querySelector("#verify-image");
const imagePreview = document.querySelector("#image-preview");
const placeholder = document.querySelector("#image-placeholder");
const video = document.querySelector("#camera-preview");
const verifyButton = document.querySelector("#verify-button");
const errorBox = document.querySelector("#verification-error");
let selectedImage = null;
let cameraStream = null;
let previewUrl = null;

async function loadAreaOptions() {
  const selector = document.querySelector("#verify-area");
  try {
    const areas = await api("/api/areas");
    selector.innerHTML = '<option value="">Choose an access area</option>' + areas.map((area) => `<option value="${area.id}">${escapeHTML(area.name)} · ${escapeHTML(area.status)}</option>`).join("");
  } catch (error) {
    selector.innerHTML = '<option value="">Areas unavailable</option>';
    showNotice(errorBox, error.message);
  }
  updateVerifyButton();
}

function setSelectedImage(file) {
  selectedImage = file;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  imagePreview.src = previewUrl;
  imagePreview.hidden = false;
  placeholder.hidden = true;
  video.hidden = true;
  document.querySelector("#image-name").textContent = file.name || "Captured camera frame";
  clearNotice(errorBox);
  resetResult();
  updateVerifyButton();
}

function resetResult(title = "Ready for verification", description = "Choose an area and image to receive a decision from the FaceGuard backend.") {
  const card = document.querySelector("#verification-result");
  card.className = "result-card result-idle";
  card.innerHTML = `<div class="result-symbol">◎</div><p class="eyebrow">VERIFICATION RESULT</p><h2>${escapeHTML(title)}</h2><p>${escapeHTML(description)}</p>`;
}

function updateVerifyButton() {
  verifyButton.disabled = !selectedImage || !document.querySelector("#verify-area").value || verifyButton.dataset.loading === "true";
}

function stopCamera() {
  if (cameraStream) cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  video.srcObject = null;
  video.hidden = true;
  document.querySelector("#start-camera").hidden = false;
  document.querySelector("#capture-frame").hidden = true;
  document.querySelector("#stop-camera").hidden = true;
  if (!selectedImage) placeholder.hidden = false;
}

imageInput.addEventListener("change", () => {
  const file = imageInput.files?.[0];
  if (file) { stopCamera(); setSelectedImage(file); }
});
document.querySelector("#verify-area").addEventListener("change", updateVerifyButton);
document.querySelector("#verify-area").addEventListener("change", () => resetResult());

document.querySelector("#start-camera").addEventListener("click", async () => {
  clearNotice(errorBox);
  try {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("Camera access is unavailable in this browser or page context.");
    selectedImage = null;
    imagePreview.hidden = true;
    placeholder.hidden = false;
    document.querySelector("#image-name").textContent = "No image selected";
    resetResult();
    updateVerifyButton();
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
    video.srcObject = cameraStream;
    video.hidden = false;
    imagePreview.hidden = true;
    placeholder.hidden = true;
    document.querySelector("#start-camera").hidden = true;
    document.querySelector("#capture-frame").hidden = false;
    document.querySelector("#stop-camera").hidden = false;
    await video.play();
  } catch (error) {
    stopCamera();
    showNotice(errorBox, `Camera unavailable: ${error.message || "Allow camera permission and try again."}`);
  }
});

document.querySelector("#stop-camera").addEventListener("click", stopCamera);
document.querySelector("#capture-frame").addEventListener("click", () => {
  if (!video.videoWidth || !video.videoHeight) {
    showNotice(errorBox, "The camera is still starting. Try capturing again in a moment.");
    return;
  }
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  canvas.toBlob((blob) => {
    if (blob) setSelectedImage(new File([blob], "camera-capture.jpg", { type: "image/jpeg" }));
  }, "image/jpeg", 0.92);
  stopCamera();
});

function showDecision(decision) {
  const granted = decision.result === "ACCESS_GRANTED";
  const card = document.querySelector("#verification-result");
  const person = decision.person;
  const detail = (label, value) => `<div class="result-detail"><span>${label}</span><span>${escapeHTML(value ?? "—")}</span></div>`;
  card.className = `result-card ${granted ? "result-granted" : "result-denied"}`;
  card.innerHTML = `<div class="result-symbol">${granted ? "✓" : "×"}</div><p class="eyebrow">VERIFICATION RESULT</p><h2>ACCESS ${granted ? "GRANTED" : "DENIED"}</h2><div class="result-details">${granted ? detail("Person", person?.name) + detail("Employee ID", person?.employee_id) : ""}${detail("Area", decision.area?.name || "—")}${!granted ? detail("Reason", decision.reason || "ACCESS_DENIED") : ""}${detail("Match score · cosine distance", formatScore(decision.match_score))}${detail("Timestamp", formatDate(decision.timestamp))}</div>`;
}

verifyButton.addEventListener("click", async () => {
  if (!selectedImage || !document.querySelector("#verify-area").value) return;
  clearNotice(errorBox);
  const form = new FormData();
  form.append("area_id", document.querySelector("#verify-area").value);
  form.append("image", selectedImage, selectedImage.name || "face-image.jpg");
  verifyButton.dataset.loading = "true";
  setButtonLoading(verifyButton, true, "Checking face…");
  resetResult("Checking access…", "The backend is processing the image and checking the selected area's authorized gallery.");
  try {
    const decision = await api("/api/access/verify", { method: "POST", body: form });
    showDecision(decision);
  } catch (error) {
    const messages = { INVALID_IMAGE: "The image could not be read. Choose another image.", NO_FACE_DETECTED: "No face was detected. Use a clear image showing one face.", MULTIPLE_FACES_DETECTED: "More than one face was detected. Use an image containing one person.", AREA_INACTIVE: "This area is inactive and cannot grant access.", FACE_ENGINE_UNAVAILABLE: "The face recognition service is not ready. Check the backend setup." };
    showNotice(errorBox, messages[error.message] || error.message);
    resetResult("Could not complete verification", "Review the error message and try again with a valid image and active area.");
  } finally {
    verifyButton.dataset.loading = "false";
    setButtonLoading(verifyButton, false);
    updateVerifyButton();
  }
});

window.addEventListener("beforeunload", () => {
  stopCamera();
  if (previewUrl) URL.revokeObjectURL(previewUrl);
});
loadAreaOptions();
