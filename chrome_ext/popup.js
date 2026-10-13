const { baseUrl: BASE_URL, requestTimeoutMs: TIMEOUT, perPage: PER_PAGE } = self.LINKVERSITY;

const MAX_RECENT_DESTINATIONS = 4;
const MAX_RECENT_SAVES = 20;
const DUPLICATE_WINDOW_MS = 7 * 24 * 60 * 60 * 1000; // 7 days
const AUTO_CLOSE_SECONDS = 4;

const ELEMENT_IDS = [
  "login-section", "login-msg", "login-btn", "save-section", "logout-btn",
  "path-select", "section-select", "save-btn", "save-hint", "status-msg",
  "retry-btn", "page-favicon", "page-title-input", "page-url", "page-warning",
  "recents-label", "recents", "success-banner", "success-text", "open-link",
  "save-elsewhere", "close-countdown", "account"
];

const el = {};
const state = {
  tab: null,
  paths: [],
  pathsTotal: 0,
  sections: [],
  recents: [],      // recent destinations: path/section pairs
  recentSaves: [],  // saved urls (used for duplicate hints)
  saving: false,
  success: false,
  autoClose: true,
  tickTimer: null
};

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

document.addEventListener("DOMContentLoaded", init);

async function init() {
  ELEMENT_IDS.forEach((id) => { el[id] = document.getElementById(id); });
  bindEvents();

  state.tab = await getActiveTab();

  const stored = await chrome.storage.local.get([
    "api_token", "recent_destinations", "recent_saves"
  ]);
  state.recents = Array.isArray(stored.recent_destinations) ? stored.recent_destinations : [];
  state.recentSaves = Array.isArray(stored.recent_saves) ? stored.recent_saves : [];
  renderRecents();
  renderPageInfo();

  if (stored.api_token) {
    showSaveSection();
  } else {
    showLoginSection();
  }
}

function bindEvents() {
  el["login-btn"].addEventListener("click", onLogin);
  el["logout-btn"].addEventListener("click", onLogout);
  el["retry-btn"].addEventListener("click", () => loadPaths(1, false));
  el["save-elsewhere"].addEventListener("click", () => {
    exitSuccess();
    el["section-select"].focus();
  });
  el["page-favicon"].addEventListener("error", () => {
    el["page-favicon"].classList.add("hidden");
  });
  el["success-banner"].addEventListener("mouseenter", pauseAutoClose);

  el["path-select"].addEventListener("change", () => onPathChange());
  el["section-select"].addEventListener("change", () => {
    exitSuccess();
    if (el["section-select"].value) {
      chrome.storage.local.set({ last_section_id: Number(el["section-select"].value) });
    }
    renderSaveButton();
  });
  el["save-btn"].addEventListener("click", onSave);

  document.addEventListener("keydown", onKeyDown);
}

function onKeyDown(e) {
  if (e.key === "Escape") {
    if (state.success) window.close();
    return;
  }
  if (e.key !== "Enter" || e.altKey) return;

  // Buttons and links activate natively on Enter — never double-fire them
  // (that would save twice when the focused save button is pressed).
  const target = e.target;
  const tag = target && target.tagName ? String(target.tagName).toLowerCase() : "";
  if (tag === "button" || tag === "a") return;

  // Enter anywhere else in the popup = save (or dismiss the success banner).
  if (state.success) {
    e.preventDefault();
    window.close();
    return;
  }
  if (!el["save-btn"].disabled && !el["save-section"].classList.contains("hidden")) {
    e.preventDefault();
    onSave();
  }
}

// ---------------------------------------------------------------- session ---

async function getToken() {
  const { api_token } = await chrome.storage.local.get(["api_token"]);
  return api_token || null;
}

async function onLogin() {
  el["login-btn"].disabled = true;
  el["login-msg"].textContent = "Waiting for authorization…";

  chrome.runtime.sendMessage({ action: "login" }, (response) => {
    el["login-btn"].disabled = false;

    if (chrome.runtime.lastError) {
      el["login-msg"].textContent = "Could not start login. Try again.";
      return;
    }
    if (response && response.success) {
      showSaveSection();
    } else {
      el["login-msg"].textContent = (response && response.error) || "Login failed. Please try again.";
    }
  });
}

async function onLogout() {
  await chrome.storage.local.remove(["api_token", "last_path_id", "last_section_id"]);
  setStatus("", "");
  showLoginSection();
}

function showLoginSection(message) {
  exitSuccess();
  el["login-section"].classList.remove("hidden");
  el["save-section"].classList.add("hidden");
  stopTabWatch();
  if (message) el["login-msg"].textContent = message;
}

async function showSaveSection() {
  el["login-section"].classList.add("hidden");
  el["save-section"].classList.remove("hidden");
  // The tab may have changed while the auth window was open.
  state.tab = (await getActiveTab()) || state.tab;
  renderPageInfo();
  startTabWatch();
  updateAccountLabel();
  await loadPaths(1, false);
  maybeFocusPrimary();
}

async function updateAccountLabel() {
  const { logged_in_at } = await chrome.storage.local.get(["logged_in_at"]);
  el["account"].textContent = logged_in_at ? "Signed in" : "";
}

/** Session expired / invalid token: send the user back to the login screen. */
function sessionExpired(message) {
  chrome.storage.local.remove(["api_token"], () => showLoginSection(message));
}

// ------------------------------------------------------------------- tab ----

async function getActiveTab() {
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    return tabs && tabs[0] ? tabs[0] : null;
  } catch (e) {
    return null;
  }
}

function currentUrl() {
  return state.tab && state.tab.url ? state.tab.url : "";
}

function isSavable(url) {
  return /^https?:\/\//i.test(url);
}

// The active tab can change while the popup is open — keep the shown page and
// the save button in sync.
let tabWatchTimer = null;

function startTabWatch() {
  stopTabWatch();
  tabWatchTimer = setInterval(refreshTab, 1500);
}

function stopTabWatch() {
  if (tabWatchTimer) {
    clearInterval(tabWatchTimer);
    tabWatchTimer = null;
  }
}

async function refreshTab() {
  const tab = await getActiveTab();
  if (!tab) return;
  const changed = !state.tab || tab.url !== state.tab.url || tab.title !== state.tab.title;
  state.tab = tab;
  if (changed) renderPageInfo();
}

function renderPageInfo() {
  const url = currentUrl();
  const title = (state.tab && state.tab.title) || "";
  const input = el["page-title-input"];

  // Don't clobber what the user is typing.
  if (document.activeElement !== input) {
    input.value = title;
  }
  renderFavicon();

  if (!url) {
    el["page-url"].textContent = "";
    el["page-warning"].textContent = "This page's address is unavailable.";
    el["page-warning"].classList.remove("hidden");
    renderSaveButton();
    return;
  }

  el["page-url"].textContent = url;

  if (isSavable(url)) {
    el["page-warning"].classList.add("hidden");
  } else {
    el["page-warning"].textContent = "Only http/https pages can be saved.";
    el["page-warning"].classList.remove("hidden");
  }

  // A new page means the old info line (duplicate hint, counts) is stale.
  if (el["status-msg"].classList.contains("info")) setStatus("", "");
  maybeShowDuplicateHint();
  renderSaveButton();
}

function renderFavicon() {
  const img = el["page-favicon"];
  const fav = state.tab && state.tab.favIconUrl;
  if (isSavable(currentUrl()) && fav && /^https?:/i.test(fav)) {
    if (img.getAttribute("src") !== fav) img.setAttribute("src", fav);
    img.classList.remove("hidden");
  } else {
    img.removeAttribute("src");
    img.classList.add("hidden");
  }
}

// ------------------------------------------------------------- save button --

function currentPathObj() {
  const id = Number(el["path-select"].value);
  return state.paths.find((p) => p.id === id) || null;
}

function currentSectionObj() {
  const id = Number(el["section-select"].value);
  return state.sections.find((s) => s.id === id) || null;
}

function renderSaveButton() {
  const btn = el["save-btn"];
  const hint = el["save-hint"];

  if (state.saving) {
    btn.disabled = true;
    btn.classList.remove("done");
    btn.classList.add("loading");
    btn.textContent = "Saving…";
    hint.textContent = "";
    return;
  }
  if (state.success) {
    btn.disabled = true;
    btn.classList.remove("loading");
    btn.classList.add("done");
    btn.textContent = "Saved ✓";
    hint.textContent = "";
    return;
  }

  btn.classList.remove("loading");
  btn.classList.remove("done");
  const sectionId = Number(el["section-select"].value);
  const ready = Boolean(sectionId) && isSavable(currentUrl());
  btn.disabled = !ready;

  const section = currentSectionObj();
  const path = currentPathObj();
  // "Save “To read”" reads better than "Save to To read" when the section
  // name happens to start with a verb.
  btn.textContent = ready && section ? `Save “${section.title}”` : "Save link";
  hint.textContent = ready && path ? `in ${path.title}` : "";
  updateActiveChip();
}

function maybeFocusPrimary() {
  // With a remembered destination the very first Enter press saves the link.
  if (!el["save-btn"].disabled && !state.success) {
    el["save-btn"].focus();
  }
}

// --------------------------------------------------------------- recents ----

function renderRecents() {
  const wrap = el["recents"];
  const label = el["recents-label"];
  wrap.innerHTML = "";

  if (!state.recents.length) {
    wrap.classList.add("hidden");
    label.classList.add("hidden");
    return;
  }

  state.recents.slice(0, MAX_RECENT_DESTINATIONS).forEach((r) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = `${r.pathTitle} › ${r.sectionTitle}`;
    chip.title = `Save to ${r.pathTitle} › ${r.sectionTitle}`;
    chip.dataset.pathId = String(r.pathId);
    chip.dataset.sectionId = String(r.sectionId);
    chip.addEventListener("click", () => applyDestination(r.pathId, r.sectionId));
    wrap.appendChild(chip);
  });

  wrap.classList.remove("hidden");
  label.classList.remove("hidden");
  updateActiveChip();
}

function updateActiveChip() {
  const pathId = Number(el["path-select"].value);
  const sectionId = Number(el["section-select"].value);
  Array.from(el["recents"].children).forEach((chip) => {
    const active =
      state.success === false &&
      Number(chip.dataset.pathId) === pathId &&
      Number(chip.dataset.sectionId) === sectionId;
    chip.classList[active ? "add" : "remove"]("active");
  });
}

async function applyDestination(pathId, sectionId) {
  if (!state.paths.some((p) => p.id === pathId)) {
    setStatus("That path no longer exists.", "info");
    return;
  }
  exitSuccess();
  el["path-select"].value = String(pathId);
  chrome.storage.local.set({ last_path_id: pathId, last_section_id: sectionId });
  await loadSections(pathId, sectionId);
  maybeFocusPrimary();
}

function rememberDestination(pathObj, sectionObj) {
  if (!pathObj || !sectionObj) return;
  const entry = {
    pathId: pathObj.id,
    pathTitle: pathObj.title,
    sectionId: sectionObj.id,
    sectionTitle: sectionObj.title,
    url: pathObj.url || "",
    at: Date.now()
  };
  state.recents = [entry, ...state.recents.filter((r) => r.sectionId !== entry.sectionId)]
    .slice(0, MAX_RECENT_DESTINATIONS);
  persistHistory();
  renderRecents();
}

function rememberSave(url, pathObj, sectionObj) {
  const entry = {
    url,
    pathId: pathObj ? pathObj.id : null,
    pathTitle: pathObj ? pathObj.title : "path",
    sectionId: sectionObj ? sectionObj.id : null,
    sectionTitle: sectionObj ? sectionObj.title : "section",
    at: Date.now()
  };
  state.recentSaves = [entry, ...state.recentSaves.filter((s) => s.url !== url)]
    .slice(0, MAX_RECENT_SAVES);
  persistHistory();
}

function persistHistory() {
  chrome.storage.local.set({
    recent_destinations: state.recents,
    recent_saves: state.recentSaves
  });
}

function findRecentSave(url) {
  return state.recentSaves.find(
    (s) => s.url === url && Date.now() - s.at < DUPLICATE_WINDOW_MS
  );
}

function maybeShowDuplicateHint() {
  if (state.success || el["status-msg"].textContent) return false;
  const dup = findRecentSave(currentUrl());
  if (!dup) return false;
  setStatus(`Already saved to ${dup.pathTitle} › ${dup.sectionTitle} · ${timeAgo(dup.at)}`, "info");
  return true;
}

function timeAgo(ts) {
  const seconds = Math.max(1, Math.round((Date.now() - ts) / 1000));
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

// ------------------------------------------------------------------ api -----

function setStatus(text, type) {
  el["status-msg"].textContent = text;
  el["status-msg"].className = "status" + (type ? " " + type : "");
}

async function api(pathname, { method = "GET", params = {}, data } = {}) {
  const token = await getToken();
  if (!token) {
    throw new ApiError("Not logged in.", 401);
  }

  const query = new URLSearchParams({ token });
  Object.entries(params).forEach(([key, value]) => query.set(key, value));

  // The token is sent three ways so it works against both the currently
  // deployed API (reads it from the query/body) and a future one that only
  // accepts the Authorization header:
  //   1. Authorization: Bearer header
  //   2. ?token=… query string (GET and POST)
  //   3. "token" field in the JSON body (POST)
  const headers = { Authorization: `Bearer ${token}` };
  const bodyData = data ? { token, ...data } : undefined;
  if (bodyData) headers["Content-Type"] = "application/json";

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT);

  let resp;
  try {
    resp = await fetch(
      `${BASE_URL}${pathname}?${query.toString()}`,
      {
        method,
        headers,
        body: bodyData ? JSON.stringify(bodyData) : undefined,
        signal: controller.signal
      }
    );
  } catch (e) {
    throw new ApiError(e && e.name === "AbortError" ? "Request timed out." : "Network error.", 0);
  } finally {
    clearTimeout(timer);
  }

  let payload = null;
  try {
    payload = await resp.json();
  } catch (e) {
    /* non-JSON response */
  }

  if (!resp.ok) {
    throw new ApiError((payload && payload.error) || `Request failed (${resp.status}).`, resp.status);
  }
  // Some endpoints return 200 together with an error payload.
  if (payload && payload.error) {
    throw new ApiError(payload.error, resp.status);
  }
  return payload;
}

function handleApiError(err, fallback) {
  if (err instanceof ApiError && err.status === 401) {
    sessionExpired("Your session expired. Please log in again.");
    return;
  }
  setStatus(err instanceof ApiError ? err.message : fallback, "error");
}

// --------------------------------------------------------------- paths ------

async function loadPaths(page, append) {
  const select = el["path-select"];
  el["retry-btn"].classList.add("hidden");
  if (!append) {
    state.paths = [];
    select.innerHTML = '<option value="">Loading paths…</option>';
    select.disabled = true;
    setStatus("", "");
  } else {
    select.disabled = true;
  }

  try {
    const data = await api("/slack/api/paths", {
      params: { page, per_page: PER_PAGE }
    });
    // The API returns {items, total, pages, current_page}; tolerate a plain
    // array too in case the payload format ever changes back.
    const items = Array.isArray(data) ? data : (data.items || []);
    const total = Array.isArray(data) ? items.length : (data.total || items.length);

    state.paths = append ? state.paths.concat(items) : items;
    state.pathsTotal = total;

    renderPaths();

    let restored = false;
    const { last_path_id } = await chrome.storage.local.get(["last_path_id"]);
    if (!append && last_path_id && state.paths.some((p) => p.id === last_path_id)) {
      select.value = String(last_path_id);
      await loadSections(last_path_id, undefined);
      restored = Boolean(el["section-select"].value);
    }

    // A single path (and section) means no choices at all: just save.
    if (!restored && !append && state.paths.length === 1) {
      select.value = String(state.paths[0].id);
      chrome.storage.local.set({ last_path_id: state.paths[0].id });
      await loadSections(state.paths[0].id, undefined);
      restored = Boolean(el["section-select"].value);
    }

    if (!maybeShowDuplicateHint()) {
      const remaining = state.pathsTotal - state.paths.length;
      if (remaining > 0 && !el["status-msg"].textContent) {
        setStatus(`Showing ${state.paths.length} of ${state.pathsTotal} paths.`, "info");
      }
    }
  } catch (err) {
    select.innerHTML = '<option value="">No paths available</option>';
    handleApiError(err, "Error loading paths.");
    if (!(err instanceof ApiError && err.status === 401)) {
      el["retry-btn"].classList.remove("hidden");
    }
  } finally {
    select.disabled = state.paths.length === 0;
    renderSaveButton();
  }
}

function renderPaths() {
  const select = el["path-select"];
  select.innerHTML = "";

  if (!state.paths.length) {
    select.innerHTML = '<option value="">No paths yet</option>';
    select.disabled = true;
    setStatus("Create a path on Linkversity first.", "info");
    return;
  }

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Choose a path…";
  select.appendChild(placeholder);

  state.paths.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = String(p.id);
    const count = typeof p.section_count === "number" ? ` (${p.section_count})` : "";
    opt.textContent = `${p.title}${count}`;
    opt.dataset.url = p.url || "";
    select.appendChild(opt);
  });
}

async function onPathChange() {
  const pathId = Number(el["path-select"].value);
  el["section-select"].innerHTML = '<option value="">Select a section</option>';
  el["section-select"].disabled = true;
  exitSuccess();
  renderSaveButton();

  if (!pathId) {
    setStatus("", "");
    return;
  }

  chrome.storage.local.set({ last_path_id: pathId, last_section_id: null });
  await loadSections(pathId, null);
  maybeFocusPrimary();
}

/**
 * Load sections for a path.
 * @param {number} pathId
 * @param {number|undefined|null} restoreId section to pre-select; `undefined`
 *        means "use the last saved one", `null` means "none".
 */
async function loadSections(pathId, restoreId) {
  const sectionSelect = el["section-select"];
  sectionSelect.disabled = true;
  sectionSelect.innerHTML = '<option value="">Loading sections…</option>';
  state.sections = [];
  setStatus("", "");

  try {
    const sections = await api("/slack/api/sections", { params: { path_id: pathId } });
    sectionSelect.innerHTML = "";

    if (!sections.length) {
      sectionSelect.innerHTML = '<option value="">No sections in this path</option>';
      setStatus("Add a section to this path first.", "info");
      return;
    }

    state.sections = sections;

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Choose a section…";
    sectionSelect.appendChild(placeholder);

    sections.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = String(s.id);
      const count = typeof s.link_count === "number" ? ` (${s.link_count})` : "";
      opt.textContent = `${s.title}${count}`;
      sectionSelect.appendChild(opt);
    });

    let target = restoreId;
    if (target === undefined) {
      const stored = await chrome.storage.local.get(["last_section_id"]);
      target = stored.last_section_id;
    }

    if (target && sections.some((s) => s.id === target)) {
      sectionSelect.value = String(target);
    } else if (sections.length === 1) {
      // Only one place to put it — pick it automatically.
      sectionSelect.value = String(sections[0].id);
    }
  } catch (err) {
    state.sections = [];
    sectionSelect.innerHTML = '<option value="">Select a path first</option>';
    handleApiError(err, "Error loading sections.");
  } finally {
    sectionSelect.disabled = false;
    renderSaveButton();
  }
}

// ---------------------------------------------------- success / auto close --

function startAutoClose() {
  stopAutoClose();
  state.autoClose = true;
  let left = AUTO_CLOSE_SECONDS;
  el["close-countdown"].textContent = `Closing in ${left}s`;
  state.tickTimer = setInterval(() => {
    left -= 1;
    el["close-countdown"].textContent = left > 0 ? `Closing in ${left}s` : "Closing…";
    if (left <= 0) {
      stopAutoClose();
      if (state.autoClose) window.close();
    }
  }, 1000);
}

function stopAutoClose() {
  if (state.tickTimer) {
    clearInterval(state.tickTimer);
    state.tickTimer = null;
  }
}

/** Hovering the banner (reading it, reaching for a button) pauses the close. */
function pauseAutoClose() {
  if (!state.success) return;
  state.autoClose = false;
  stopAutoClose();
  el["close-countdown"].textContent = "Saved";
}

function exitSuccess() {
  stopAutoClose();
  state.autoClose = false;
  state.success = false;
  el["success-banner"].classList.add("hidden");
  renderSaveButton();
}

// ---------------------------------------------------------------- save ------

async function onSave() {
  if (state.saving || state.success) return;

  // Re-read the tab right before saving so we never save a stale/wrong URL.
  await refreshTab();

  const sectionId = Number(el["section-select"].value);
  const url = currentUrl();
  if (!sectionId) return;
  if (!isSavable(url)) {
    setStatus("This page can't be saved.", "error");
    renderSaveButton();
    return;
  }

  const title = el["page-title-input"].value.trim();

  state.saving = true;
  el["logout-btn"].disabled = true;
  setStatus("", "");
  renderSaveButton();

  try {
    await api("/slack/api/save-link", {
      method: "POST",
      data: { url, section_id: sectionId, title: title || undefined }
    });

    const pathObj = currentPathObj();
    const sectionObj = currentSectionObj();
    onSuccess(url, pathObj, sectionObj);
  } catch (err) {
    state.saving = false;
    el["logout-btn"].disabled = false;
    renderSaveButton();
    handleApiError(err, "Failed to save this link.");
  }
}

function onSuccess(url, pathObj, sectionObj) {
  const pathTitle = pathObj ? pathObj.title : "path";
  const sectionTitle = sectionObj ? sectionObj.title : "section";

  rememberDestination(pathObj, sectionObj);
  rememberSave(url, pathObj, sectionObj);

  state.saving = false;
  state.success = true;
  el["logout-btn"].disabled = false;

  el["success-text"].textContent = `Saved to ${pathTitle} › ${sectionTitle}`;
  el["open-link"].href = pathObj && pathObj.url ? `${BASE_URL}${pathObj.url}` : `${BASE_URL}/linkolearn/`;
  el["success-banner"].classList.remove("hidden");
  setStatus("", "");

  renderSaveButton();
  startAutoClose();
}
