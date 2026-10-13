## 1.2.0

### Chrome extension

- Visual redesign of the popup: brand tokens (coral CTA, gold accent),
  masthead with icon, cards/pills, light + dark mode via
  `prefers-color-scheme`, reduced-motion support; flat accessible button
  states (solid coral save, quiet outlined "Saved", AA contrast throughout)
- Strip decorative noise: removed the coral glow blob, status bullet dot and
  gradient/glow button treatments
- Send the auth token three ways (Bearer header, `?token=` query, JSON body)
  for back-compat with deployments that lag the backend
- Share `config.js` between worker and popup; switch permission from `tabs`
  to `activeTab`; add smoke tests under `tests/chrome_ext/`

### Path page

- Public path page (`/<username>/<slug>`) redesigned: hero header with
  labeled Like/Bookmark/Copy pills, owner toolbar, manage-access card,
  section cards, password gate and dark mode
- Wire the inline "Add link" form to a new `POST /linkolearn/add-link`
  endpoint (the handlers shipped in #87 were never implemented)
- Fix the page 500ing: `len()` is not a Jinja global — use `|length`
- Owners are no longer locked out of viewing their own password-protected
  path; fix `remove_editor` raising a NameError for non-premium users

### App pages

- Shared brand style extracted to `blocks/brand.html` + a cleaned `blocks/crown.html`
  partial (dropped ~4KB of Inkscape metadata per crown); all pages below draw
  from the same cards/pills/inputs/empty-states and dark mode
- Bookmarks (`/linkolearn/bookmarks`): hero with saved count, path-card grid
  showing titles + owner + Locked/Private badges, empty state
- Create (`/new/`): hero, details card (title + slug with `/username/` prefix
  and live availability check), restyled sections, coral "Create path" button
- Profile (`/<username>`): avatar + crown hero, name/@handle/enterprise chips,
  labeled stat pills (paths / private / likes), path-card grid, empty state
- Fix "Create Path" never submitting: `json_submit.sections` was never
  initialized (TypeError on the first push); remove the duplicated
  "extract from document" button
- Fix every profile page 500ing: `len()` is not a Jinja global — use `|length`

## 1.1.0

### Refactor

- Chrome extension: one-click saving (remembered destination, auto-picked
  single path/section, Enter to save), recent-destination chips, editable
  title, page favicon, duplicate-save hint, success banner with "Open in
  Linkversity" / "Save to another section"
- Chrome extension: fix path loading against the paginated API, remember the
  last path/section, block non-http pages, handle expired sessions, retries
  and loading states
- move email from auth to api (#89)
- create assets folder
- Add migration folder
- Password protection
- Fix visibility bug
- Private label for private paths
- Android app
- Notify when passwords dont match
- Lighten footer
- Infos moved to single page
- Navbar more crisp
- Add models to admin panel
