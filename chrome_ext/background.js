importScripts("config.js");

const BASE_URL = self.LINKVERSITY.baseUrl;

/**
 * Launch the web auth flow and resolve with the final redirect URL.
 * Callback style is used on purpose so it works on older Chrome builds too.
 */
function launchWebAuthFlow(details) {
  return new Promise((resolve, reject) => {
    chrome.identity.launchWebAuthFlow(details, (responseUrl) => {
      const err = chrome.runtime.lastError;
      if (err) {
        reject(new Error(err.message));
      } else if (!responseUrl) {
        reject(new Error("Login was cancelled."));
      } else {
        resolve(responseUrl);
      }
    });
  });
}

/** Pull the API token out of the redirect URL (query or hash parameters). */
function extractToken(responseUrl) {
  try {
    const url = new URL(responseUrl);
    const fromQuery = url.searchParams.get("token");
    if (fromQuery) return fromQuery;
    if (url.hash) {
      const fromHash = new URLSearchParams(url.hash.replace(/^#/, "")).get("token");
      if (fromHash) return fromHash;
    }
  } catch (e) {
    console.error("Could not parse auth redirect URL:", e);
  }
  return null;
}

function friendlyError(message) {
  const msg = (message || "").toLowerCase();
  if (msg.includes("cancel") || msg.includes("user did not approve") || msg.includes("dismiss")) {
    return "Login was cancelled.";
  }
  if (msg.includes("oauth2") && msg.includes("not")) {
    return "Login is not configured for this extension.";
  }
  return "Login failed. Please try again.";
}

async function login() {
  const redirectUrl = chrome.identity.getRedirectURL();
  const authUrl =
    `${BASE_URL}/slack/chrome_ext_auth?redirect_uri=${encodeURIComponent(redirectUrl)}`;

  const responseUrl = await launchWebAuthFlow({ url: authUrl, interactive: true });

  if (!responseUrl.startsWith(redirectUrl)) {
    throw new Error("Login failed: unexpected redirect target.");
  }

  const token = extractToken(responseUrl);
  if (!token) {
    throw new Error("Login failed: no token returned.");
  }

  await chrome.storage.local.set({
    api_token: token,
    logged_in_at: Date.now()
  });
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (!request || request.action !== "login") {
    return false;
  }

  login()
    .then(() => sendResponse({ success: true }))
    .catch((err) => {
      console.error("Login error:", err);
      sendResponse({ success: false, error: friendlyError(err && err.message) });
    });

  return true; // keep the message channel open for the async response
});
