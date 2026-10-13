/**
 * Smoke test for chrome_ext/popup.js — runs the popup logic in Node with
 * stubbed DOM + chrome.* APIs and a mocked Linkversity API.
 *
 * Usage: node tests/chrome_ext/popup_smoke.js
 */
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const EXT = path.resolve(__dirname, "../../chrome_ext");

// ---------------------------------------------------------------- DOM stub --
class El {
  constructor(id) {
    this.id = id;
    this.value = "";
    this.textContent = "";
    this.disabled = false;
    this.className = "";
    this.children = [];
    this.listeners = {};
    this.dataset = {};
    this.attributes = {};
    this._html = "";
    const set = new Set();
    this.classList = {
      add: (...c) => c.forEach((x) => set.add(x)),
      remove: (...c) => c.forEach((x) => set.delete(x)),
      contains: (c) => set.has(c),
      toggle: (c, force) => (force ? set.add(c) : set.delete(c))
    };
  }
  set innerHTML(v) {
    this._html = v;
    this.children = [];
    // Browsers reset a <select>'s value when its options are replaced.
    this.value = "";
  }
  get innerHTML() { return this._html; }
  appendChild(c) { this.children.push(c); return c; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  async dispatch(type, ev = {}) {
    for (const fn of this.listeners[type] || []) await fn(ev);
  }
  focus() { document.activeElement = this; }
  blur() { if (document.activeElement === this) document.activeElement = null; }
  setAttribute(k, v) { this.attributes[k] = v; }
  getAttribute(k) { return k in this.attributes ? this.attributes[k] : null; }
  removeAttribute(k) { delete this.attributes[k]; }
  // Reflect the `href` property to the attribute like a real anchor does.
  get href() { return this.attributes.href || null; }
  set href(v) { this.attributes.href = v; }
  get selectedOptions() { return this.children.filter((c) => c.value === this.value); }
}

const elements = new Map();
const docListeners = {};
let onReady = null;

global.self = globalThis;
global.document = {
  activeElement: null,
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, new El(id));
    return elements.get(id);
  },
  createElement: (tag) => new El(tag),
  addEventListener(type, fn) {
    if (type === "DOMContentLoaded") onReady = fn;
    else (docListeners[type] ||= []).push(fn);
  }
};

let windowClosed = false;
global.window = { close: () => { windowClosed = true; } };

// Track interval timers so each popup "run" can be torn down.
const intervalTimers = new Set();
const realSetInterval = global.setInterval;
global.setInterval = (...args) => {
  const id = realSetInterval(...args);
  intervalTimers.add(id);
  return id;
};
const realClearInterval = global.clearInterval;
global.clearInterval = (id) => { intervalTimers.delete(id); realClearInterval(id); };

// ------------------------------------------------------------- chrome stub --
const store = {};
let activeTab = { url: "https://example.com/article", title: "A Great Article" };

global.chrome = {
  runtime: {
    lastError: null,
    sendMessage: (msg, cb) => cb && cb({ success: true })
  },
  storage: {
    local: {
      get: async (keys) => {
        const out = {};
        keys.forEach((k) => { if (k in store) out[k] = store[k]; });
        return out;
      },
      set: async (obj) => Object.assign(store, obj),
      remove: async (keys, cb) => {
        keys.forEach((k) => delete store[k]);
        if (cb) cb();
      }
    }
  },
  tabs: {
    query: async () => [Object.assign({}, activeTab)]
  }
};

// --------------------------------------------------------------- API stub ---
const calls = [];
const pathsPayload = () => ({
  items: [{
    id: 1, title: "Learning", slug: "learning", url: "/alice/learning", section_count: 2
  }],
  total: 1, pages: 1, current_page: 1
});
const sectionsPayload = () => [{ id: 10, title: "General", link_count: 3 }];

const responses = {
  "/slack/api/paths": () => ({ ok: true, status: 200, json: pathsPayload }),
  "/slack/api/sections": () => ({ ok: true, status: 200, json: sectionsPayload }),
  "/slack/api/save-link": (opts, url) => {
    calls.push(JSON.parse(opts.body));
    saveUrls.push(url);
    return { ok: true, status: 200, json: async () => ({ success: true, id: 99 }) };
  }
};
let failPaths = null; // set to a Response-like object to force an error
const saveUrls = [];
global.fetch = async (url, opts = {}) => {
  const pathname = new URL(url).pathname;
  if (pathname === "/slack/api/paths" && failPaths) return failPaths;
  const handler = responses[pathname];
  if (!handler) throw new Error(`Unexpected request: ${url}`);
  return handler(opts, url);
};
global.AbortController = class {
  constructor() { this.signal = {}; }
  abort() {}
};

// ------------------------------------------------------------------ run -----
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const el = (id) => document.getElementById(id);

const load = (file) =>
  new Function(fs.readFileSync(path.join(EXT, file), "utf8")).call(global);

async function startPopup() {
  // Fresh DOM + listeners for a new popup session.
  for (const id of Array.from(elements.keys())) elements.delete(id);
  Object.keys(docListeners).forEach((k) => delete docListeners[k]);
  document.activeElement = null;
  windowClosed = false;
  intervalTimers.forEach((id) => realClearInterval(id));
  intervalTimers.clear();

  load("config.js");
  load("popup.js");
  await onReady();
  await sleep(50);
}

const pressKey = async (key) => {
  const ev = { key, altKey: false, preventDefault() { ev.defaultPrevented = true; } };
  for (const fn of docListeners.keydown || []) await fn(ev);
  return ev;
};

(async () => {
  store.api_token = "tok-123"; // logged in

  // ============================================================ first run ==
  // Fresh user: no remembered destination.
  await startPopup();

  assert(el("save-section").classList.contains("hidden") === false, "save section shown");
  assert.strictEqual(el("page-title-input").value, "A Great Article", "title prefilled");
  assert.strictEqual(el("page-url").textContent, "https://example.com/article");

  // Single path + single section => fully automatic, zero clicks.
  assert.strictEqual(el("path-select").value, "1", "single path auto-selected");
  assert.strictEqual(el("section-select").value, "10", "single section auto-selected");
  assert.strictEqual(el("save-btn").disabled, false, "save ready with no interaction");
  assert.strictEqual(el("save-btn").textContent, "Save “General”", el("save-btn").textContent);
  assert.strictEqual(el("save-hint").textContent, "in Learning");
  assert.strictEqual(document.activeElement, el("save-btn"), "save button focused");
  console.log("✓ zero-click ready: auto path/section + focused save button");

  // No recents yet.
  assert(el("recents").classList.contains("hidden"), "no chips for a fresh user");

  // Edit the title, then just press Enter.
  el("page-title-input").value = "Custom title";
  const ev = await pressKey("Enter");
  await sleep(50);
  assert(ev.defaultPrevented, "Enter was handled by the popup");
  assert.strictEqual(calls.length, 1, "one save request");
  assert.deepStrictEqual(calls[0], {
    token: "tok-123", // the deployed API only reads the token from the body
    url: "https://example.com/article",
    section_id: 10,
    title: "Custom title"
  });
  assert(saveUrls[0].includes("token=tok-123"), `query token missing: ${saveUrls[0]}`);
  console.log("✓ Enter saves with the edited title:", JSON.stringify(calls[0]));

  // Success banner instead of a silent close.
  assert.strictEqual(el("success-banner").classList.contains("hidden"), false, "banner shown");
  assert.strictEqual(el("success-text").textContent, "Saved to Learning › General");
  assert.strictEqual(el("open-link").getAttribute("href"), "https://linkversity.lol/alice/learning",
    "open link points at the saved path");
  assert.strictEqual(el("save-btn").textContent, "Saved ✓");
  assert(el("close-countdown").textContent.includes("Closing in"), el("close-countdown").textContent);
  assert.strictEqual(windowClosed, false, "does not close instantly");
  console.log("✓ success banner:", JSON.stringify(el("success-text").textContent),
    "| link:", el("open-link").getAttribute("href"));

  // The destination is now a recent chip.
  await sleep(50);
  assert.strictEqual(el("recents").classList.contains("hidden"), false, "chip row visible");
  const chips = el("recents").children;
  assert.strictEqual(chips.length, 1, `one chip, got ${chips.length}`);
  assert.strictEqual(chips[0].textContent, "Learning › General");
  console.log("✓ recent destination chip rendered:", chips[0].textContent);

  // Saving again must not fire while the banner is up.
  await pressKey("Enter");
  await sleep(30);
  assert.strictEqual(calls.length, 1, "Enter after success closes instead of re-saving");
  assert.strictEqual(windowClosed, true, "Enter closes after success");
  // keep running: stop the closing timer
  el("success-banner").dispatch("mouseenter");
  windowClosed = false;

  // "Save elsewhere" returns to editing.
  await el("save-elsewhere").dispatch("click");
  await sleep(20);
  assert.strictEqual(el("success-banner").classList.contains("hidden"), true, "banner hidden");
  assert.strictEqual(el("save-btn").disabled, false, "save re-enabled for another section");
  console.log("✓ \"Save elsewhere\" returns to the editor");

  // =========================================================== second run ==
  // Same user comes back: remembered destination + duplicate hint.
  activeTab = { url: "https://example.com/article", title: "A Great Article (2)" };
  await startPopup();

  assert.strictEqual(el("path-select").value, "1", "last path restored");
  assert.strictEqual(el("section-select").value, "10", "last section restored");
  assert.strictEqual(el("save-btn").disabled, false, "one-click ready from memory");
  assert.strictEqual(el("recents").classList.contains("hidden"), false, "chips restored");
  assert(el("status-msg").textContent.includes("Already saved to Learning › General"),
    `duplicate hint: ${el("status-msg").textContent}`);
  console.log("✓ returning user:", JSON.stringify(el("status-msg").textContent));

  // Clicking a chip re-applies the destination.
  el("section-select").value = "";
  await el("section-select").dispatch("change");
  await sleep(20);
  assert.strictEqual(el("save-btn").disabled, true, "save off without a section");
  await el("recents").children[0].dispatch("click");
  await sleep(50);
  assert.strictEqual(el("path-select").value, "1", "chip restored the path");
  assert.strictEqual(el("section-select").value, "10", "chip restored the section");
  assert.strictEqual(el("save-btn").disabled, false, "save ready after chip click");
  console.log("✓ chip click restores the destination");

  // Enter on a focused BUTTON must be left to the browser's native click,
  // otherwise pressing Enter on the save button would save twice.
  const before = calls.length;
  const evBtn = { key: "Enter", altKey: false, target: { tagName: "BUTTON" }, preventDefault() {} };
  for (const fn of docListeners.keydown || []) await fn(evBtn);
  await sleep(30);
  assert.strictEqual(calls.length, before, "Enter on a button must not save on its own");
  console.log("✓ Enter on a focused button does not double-fire");

  // ================================================== blocked page =========
  activeTab = { url: "chrome://extensions", title: "Extensions" };
  await pressKey("Enter");
  await sleep(50);
  assert.strictEqual(calls.length, 1, "no save request for chrome:// page");
  assert(el("status-msg").textContent.includes("can't be saved"),
    `status: ${el("status-msg").textContent}`);
  assert(!el("page-warning").classList.contains("hidden"), "warning shown");
  console.log("✓ non-http pages are blocked:", JSON.stringify(el("status-msg").textContent));

  // Tab watch: page becomes saveable again -> button re-enables itself.
  activeTab = { url: "https://other.example.org/post", title: "Another page" };
  await sleep(1700);
  assert.strictEqual(el("save-btn").disabled, false, "save re-enabled after navigation");
  assert.strictEqual(el("page-title-input").value, "Another page", "title follows the tab");
  console.log("✓ tab watch re-enables save after navigation");

  // ================================================== expired session ======
  failPaths = { ok: false, status: 401, json: async () => ({ error: "Invalid token" }) };
  await el("retry-btn").dispatch("click");
  await sleep(50);
  assert(!el("login-section").classList.contains("hidden"), "login section shown");
  assert(el("login-msg").textContent.includes("expired"), `login msg: ${el("login-msg").textContent}`);
  console.log("✓ 401 handling:", JSON.stringify(el("login-msg").textContent));

  intervalTimers.forEach((id) => realClearInterval(id));
  console.log("\nAll popup smoke tests passed.");
  process.exit(0);
})().catch((e) => {
  console.error("FAILED:", e.message);
  process.exit(1);
});
