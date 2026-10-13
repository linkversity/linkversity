// Shared configuration.
// Loaded by the background service worker via importScripts() and by the
// popup via <script src="config.js">.
self.LINKVERSITY = Object.freeze({
  // API origin (no trailing slash).
  baseUrl: "https://linkversity.lol",
  // Abort hanging requests after this many milliseconds.
  requestTimeoutMs: 15000,
  // Number of paths fetched per page.
  perPage: 100
});
