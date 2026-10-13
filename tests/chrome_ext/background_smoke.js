/**
 * Smoke test for chrome_ext/background.js (auth flow).
 * Usage: node tests/chrome_ext/background_smoke.js
 */
const fs = require("fs");
const assert = require("assert");

const EXT = require("path").resolve(__dirname, "../../chrome_ext");
const REDIRECT = "https://abcdefgh.chromiumapp.org/provider_cb/";

const store = {};
let listener = null;
let lastAuthUrl = null;
let nextResponseUrl = null;
let nextLastError = null;

global.self = globalThis;
global.importScripts = (file) => {
  new Function(fs.readFileSync(`${EXT}/${file}`, "utf8")).call(global);
};
global.chrome = {
  runtime: {
    get lastError() { return nextLastError; },
    onMessage: { addListener: (fn) => { listener = fn; } }
  },
  identity: {
    getRedirectURL: () => REDIRECT,
    launchWebAuthFlow: (details, cb) => {
      lastAuthUrl = details.url;
      cb(nextResponseUrl);
    }
  },
  storage: { local: { set: async (obj) => Object.assign(store, obj) } }
};

new Function(fs.readFileSync(`${EXT}/background.js`, "utf8")).call(global);

const send = (msg) => new Promise((resolve) => {
  assert.strictEqual(listener(msg, {}, resolve), true, "listener keeps channel open for async response");
});

(async () => {
  assert(typeof listener === "function", "onMessage listener registered");

  // Unknown action is ignored (returns false -> no async channel).
  assert.strictEqual(listener({ action: "nope" }, {}, () => {}), false, "unknown action ignored");

  // 1. Successful login.
  nextResponseUrl = `${REDIRECT}?token=abc123`;
  nextLastError = null;
  let res = await send({ action: "login" });
  assert.strictEqual(res.success, true, `expected success, got ${JSON.stringify(res)}`);
  assert.strictEqual(store.api_token, "abc123", "token stored");
  assert(typeof store.logged_in_at === "number", "login timestamp stored");
  assert(lastAuthUrl.startsWith("https://linkversity.lol/slack/chrome_ext_auth"), `auth url: ${lastAuthUrl}`);
  assert(lastAuthUrl.includes(encodeURIComponent(REDIRECT)), "redirect_uri is encoded");
  console.log("✓ successful login stores the token");

  // 2. Redirect without a token.
  nextResponseUrl = `${REDIRECT}?nope=1`;
  res = await send({ action: "login" });
  assert.strictEqual(res.success, false);
  assert(typeof res.error === "string" && res.error.length > 0, "error message returned");
  console.log("✓ missing token handled:", JSON.stringify(res.error));

  // 3. User cancels the auth window.
  nextResponseUrl = undefined;
  nextLastError = { message: "The user did not approve sign-in." };
  res = await send({ action: "login" });
  assert.strictEqual(res.success, false);
  assert.strictEqual(res.error, "Login was cancelled.", `got: ${res.error}`);
  nextLastError = null;
  console.log("✓ cancelled login reported:", JSON.stringify(res.error));

  console.log("\nAll background smoke tests passed.");
  process.exit(0);
})().catch((e) => {
  console.error("FAILED:", e.message);
  process.exit(1);
});
