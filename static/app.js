/* ═══════════════════════════════════════════════════════════════════════
   NiziPOS Dashboard — Client-Side Application Logic
   ═══════════════════════════════════════════════════════════════════════ */

// ── SocketIO Connection ──────────────────────────────────────────────

const socket = io();
let selectedImageFile = null;
let apiKey = null;

// ── Authentication ───────────────────────────────────────────────────

function getStoredApiKey() {
    return localStorage.getItem("nizipos_api_key");
}

function saveApiKey() {
    const input = document.getElementById("apiKeyInput");
    const key = input.value.trim();
    if (key.length < 10) {
        showToast("Invalid API Key format", "error");
        return;
    }
    localStorage.setItem("nizipos_api_key", key);
    apiKey = key;
    document.getElementById("setupModal").classList.remove("active");
    showToast("API Key saved!", "success");
    addLog("API Key updated manually.", "info");
    
    // Retry initial status
    refreshStatus();
}

function showSetupModal() {
    document.getElementById("setupModal").classList.add("active");
}

// ── SocketIO Connection ──────────────────────────────────────────────

socket.on("connect", () => {
    addLog("WebSocket connected.", "info");
});

socket.on("disconnect", () => {
    addLog("WebSocket disconnected.", "error");
});

socket.on("device_status", (data) => {
    updateStatusUI(data.connected, data.port);
});

socket.on("command_result", (data) => {
    if (data.success) {
        addLog(`Command OK: ${data.command}`, "success");
    } else {
        addLog(`Command FAIL: ${data.command} — ${data.error}`, "error");
    }
});

// ── Status UI ────────────────────────────────────────────────────────

function updateStatusUI(connected, port) {
    const badge = document.getElementById("statusBadge");
    const text = document.getElementById("statusText");
    const portLabel = document.getElementById("portLabel");

    if (connected) {
        badge.classList.add("connected");
        text.textContent = "Connected";
        portLabel.textContent = port ? `(${port})` : "";
        addLog(`Device connected on ${port}`, "success");
        showToast("Device connected!", "success");
    } else {
        badge.classList.remove("connected");
        text.textContent = "Disconnected";
        portLabel.textContent = "";
    }
}

// ── API Calls ────────────────────────────────────────────────────────

async function api(method, url, body = null) {
    if (!apiKey) {
        apiKey = getStoredApiKey();
    }
    
    if (!apiKey && url !== "/api/auth-token") {
        showSetupModal();
        return { success: false, error: "API Key required" };
    }

    const opts = { 
        method, 
        headers: {
            "X-API-Key": apiKey
        } 
    };
    if (body && !(body instanceof FormData)) {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(body);
    } else if (body instanceof FormData) {
        opts.body = body;
    }
    try {
        const res = await fetch(url, opts);
        if (res.status === 401) {
            apiKey = null;
            localStorage.removeItem("nizipos_api_key");
            showSetupModal();
            return { success: false, error: "Unauthorized" };
        }
        return await res.json();
    } catch (err) {
        return { success: false, error: err.message };
    }
}

// ── Connection ───────────────────────────────────────────────────────

async function connectDevice() {
    const port = document.getElementById("comPort").value.trim() || null;
    addLog("Connecting..." + (port ? ` (${port})` : " (auto-detect)"), "info");
    const btn = document.getElementById("btnConnect");
    btn.disabled = true;
    btn.textContent = "⏳ Connecting...";

    const res = await api("POST", "/api/connect", port ? { port } : {});

    btn.disabled = false;
    btn.textContent = "⚡ Connect";

    if (res.success) {
        showToast("Connected to " + res.port, "success");
    } else {
        addLog("Connection failed: " + res.error, "error");
        showToast(res.error, "error");
    }
}

async function disconnectDevice() {
    const res = await api("POST", "/api/disconnect");
    if (res.success) {
        addLog("Disconnected.", "info");
        showToast("Device disconnected.", "info");
        updateStatusUI(false, null);
    }
}

// ── Commands ─────────────────────────────────────────────────────────

async function sendCmd(cmd) {
    addLog(`Sending: ${cmd}`, "info");
    const res = await api("POST", "/api/command", { command: cmd });
    if (res.success) {
        addLog(`✓ ${cmd}`, "success");
        showToast(`${cmd} sent`, "success");
    } else {
        addLog(`✕ ${cmd}: ${res.error}`, "error");
        showToast(res.error, "error");
    }
}

function sendText() {
    const t = document.getElementById("textTitle").value;
    const s = document.getElementById("textSubtitle").value;
    const m = document.getElementById("textMessage").value;
    if (!t && !s && !m) { showToast("Fill in at least one field", "warning"); return; }
    sendCmd(`TEXT**${t}**${s}**${m}`);
}

function sendQR() {
    const a = document.getElementById("qrAmount").value;
    const s = document.getElementById("qrScanText").value;
    const p = document.getElementById("qrPayload").value;
    if (!p) { showToast("QR Payload is required", "warning"); return; }
    sendCmd(`QR**${a}**${s}**${p}`);
}

function sendStatus(type, id1, id2) {
    const v1 = document.getElementById(id1).value;
    const v2 = document.getElementById(id2).value;
    sendCmd(`${type}**${v1}**${v2}`);
}

function sendRaw() {
    const cmd = document.getElementById("rawCommand").value.trim();
    if (!cmd) { showToast("Enter a command first", "warning"); return; }
    sendCmd(cmd);
}

// ── Settings ─────────────────────────────────────────────────────────

async function setSetting(key, value) {
    addLog(`Setting ${key} = ${value}`, "info");
    const body = {};
    body[key] = parseInt(value, 10);
    const res = await api("POST", "/api/settings", body);
    if (res.success) {
        addLog(`✓ ${key} set to ${value}`, "success");
        showToast(`${key} → ${value}`, "success");
    } else {
        addLog(`✕ ${key}: ${res.error}`, "error");
        showToast(res.error, "error");
    }
}

// ── Image Upload ─────────────────────────────────────────────────────

const dropZone = document.getElementById("dropZone");

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) previewImage(file);
});

function handleImageSelect(e) {
    const file = e.target.files[0];
    if (file) previewImage(file);
}

function previewImage(file) {
    if (!file.type.match("image/jpeg")) {
        showToast("Only JPEG images are supported", "warning");
        return;
    }
    selectedImageFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById("imagePreview").innerHTML =
            `<img src="${e.target.result}" class="preview-img" style="max-height:120px;border-radius:8px;">
             <div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px;">${file.name} (${(file.size / 1024).toFixed(1)} KB)</div>`;
    };
    reader.readAsDataURL(file);
    document.getElementById("btnUploadImg").disabled = false;
}

async function uploadImage() {
    if (!selectedImageFile) { showToast("No image selected", "warning"); return; }
    const btn = document.getElementById("btnUploadImg");
    btn.disabled = true;
    btn.textContent = "⏳ Uploading...";
    addLog(`Uploading ${selectedImageFile.name} (${(selectedImageFile.size / 1024).toFixed(1)} KB)`, "info");

    const fd = new FormData();
    fd.append("image", selectedImageFile);
    fd.append("size", document.getElementById("screenSize").value);

    const res = await api("POST", "/api/upload-image", fd);

    btn.disabled = false;
    btn.textContent = "Upload to Device";

    if (res.success) {
        addLog("✓ Image uploaded successfully", "success");
        showToast("Image uploaded!", "success");
    } else {
        addLog(`✕ Image upload: ${res.error}`, "error");
        showToast(res.error, "error");
    }
}

// ── Logging ──────────────────────────────────────────────────────────

function addLog(message, type = "info") {
    const area = document.getElementById("logArea");
    const now = new Date();
    const ts = now.toTimeString().split(" ")[0];
    const entry = document.createElement("div");
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `<span class="timestamp">[${ts}]</span> ${escapeHtml(message)}`;
    area.appendChild(entry);
    area.scrollTop = area.scrollHeight;

    // Keep last 200 entries
    while (area.children.length > 200) {
        area.removeChild(area.firstChild);
    }
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// ── Toast Notifications ──────────────────────────────────────────────

function showToast(message, type = "info", duration = 3000) {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    const icons = { success: "✓", error: "✕", warning: "⚠", info: "ℹ" };
    toast.innerHTML = `<span>${icons[type] || "ℹ"}</span> ${escapeHtml(message)}`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(8px)";
        toast.style.transition = "0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

async function refreshStatus() {
    const res = await api("GET", "/api/status");
    if (res && res.success !== false) updateStatusUI(res.connected, res.port);
}

(async () => {
    apiKey = getStoredApiKey();
    if (!apiKey) {
        showSetupModal();
    } else {
        refreshStatus();
    }
})();
