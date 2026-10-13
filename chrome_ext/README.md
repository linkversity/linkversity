# Linkversity Saver (Chrome extension)

Save the page you are currently reading into a Linkversity path/section with
two clicks.

## Install (unpacked)

1. Open `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** and pick this `chrome_ext/` folder

For a shareable build, zip the folder (`chrome_ext.zip` in the repo root).

## What it does

### Saving in one click

- The popup **remembers your last path & section** and pre-selects them; the
  save button is focused and reads **Save “General”** (with an
  *in Learning* hint underneath) — open the popup and press **Enter**.
- If there is only one path (and one section) they are picked automatically:
  a brand-new user with a single path also saves in one click.
- **Recent destination chips** ("Learning › General") let you jump to a
  frequently used path/section without touching the dropdowns.
- The page **title is editable** right in the popup — fix it before saving
  (or clear it to save without a title).
- The **page favicon** is shown next to the title.

### Feedback

- Saving shows **"Saved to Learning › General"** with an
  **Open in Linkversity ↗** link (straight to the saved path) and
  **Save elsewhere**, then auto-closes after 4s. Hovering the banner
  pauses the countdown; **Esc** closes immediately.
- If you already saved this URL in the last 7 days the popup says
  *"Already saved to Learning › General · 2h ago"* instead of silently
  creating a duplicate.
- Path/section counts are shown in the dropdowns, and a hint tells you when
  only part of a large path list fits.

### Safety

- **Login** – `chrome.identity.launchWebAuthFlow` redirects to
  `https://linkversity.lol/slack/chrome_ext_auth`, which hands back an API
  token. The token is stored in `chrome.storage.local`.
- **Save** – POSTs `{url, title, section_id}` to `/slack/api/save-link`.
- Only `http(s)` pages can be saved; everything else (`chrome://`, files, …)
  is blocked with a warning instead of sending a broken request.
- If the API answers `401`, the popup clears the token and asks you to log in
  again instead of silently failing.
- Requests time out after 15s with a retry button.

### Keyboard

| Key | Action |
| --- | --- |
| `Enter` | Save the link (when a section is selected) |
| `Esc` | Close the popup |

## Files

| File | Purpose |
| --- | --- |
| `manifest.json` | Manifest V3 config. Uses `activeTab` (not `tabs`) so install only prompts for "read the page you save", not browsing history. |
| `config.js` | Shared settings (`baseUrl`, timeouts, page size). Loaded by the worker and the popup. |
| `background.js` | Service worker: web auth flow + token storage. |
| `popup.html` / `popup.js` | Popup UI and API calls. |

## Permissions

- `activeTab` – read the current tab's URL/title when you open the popup
- `storage` – remember the API token and your last path/section
- `identity` – OAuth-style login
- host permissions for `https://linkversity.lol` (the API) and
  `http://localhost` (local development)

## API notes

The extension talks to the endpoints in `modules/box__linkolearn/slack/view.py`:

- `GET /slack/api/paths` – returns `{items, total, pages, current_page}`;
  each item carries `url` (`/{username}/{slug}`, used by the "Open in
  Linkversity" link). The popup requests `per_page=100` and reports when more
  paths exist
- `GET /slack/api/sections?path_id=…`
- `POST /slack/api/save-link`

The token is sent in the `Authorization: Bearer` header **and** (for
backwards compatibility with deployed servers) in the query string/body.

## Development

Load the unpacked extension, edit, then press the reload button on
`chrome://extensions`. Service-worker console output is under **Inspect
views: background page**; the popup console is opened via **Inspect popup**.

### Smoke tests

The popup and background logic are covered by dependency-free Node scripts
(stubbed DOM + `chrome.*` APIs, mocked API). They live outside this folder so
they are not shipped in the zip:

```sh
node tests/chrome_ext/popup_smoke.js
node tests/chrome_ext/background_smoke.js
```
