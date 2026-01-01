const BASE_URL = "https://linkversity.lol";

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "login") {
    const redirectUrl = chrome.identity.getRedirectURL();
    const authUrl = `${BASE_URL}/slack/chrome_ext_auth?redirect_uri=${encodeURIComponent(redirectUrl)}`;

    chrome.identity.launchWebAuthFlow({
      url: authUrl,
      interactive: true
    }, (responseUrl) => {
      if (chrome.runtime.lastError || !responseUrl) {
        console.error("Auth failed:", chrome.runtime.lastError);
        sendResponse({ success: false });
        return;
      }

      const url = new URL(responseUrl);
      const token = url.searchParams.get("token");
      
      if (token) {
        chrome.storage.local.set({ api_token: token }, () => {
          sendResponse({ success: true });
        });
      } else {
        sendResponse({ success: false });
      }
    });
    return true; // Keep channel open for async response
  }
});
