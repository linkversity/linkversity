## Unreleased

### Explore pagination

- The landing "Explore latest" grid now pages through every public path
  instead of stopping at the 8 newest: 8 per page, `?page=N`, prev/next
  plus numbered pages, and a total count. Out-of-range or junk `page`
  values clamp to the first/last page instead of erroring

## 1.10.0

### Path & section descriptions (SEO)

- Paths and sections gained a fillable `description` (edit + new forms,
  up to 500 chars; blank saves as NULL), editable by whoever can edit
  the path
- The path page shows the path description under the heading and each
  section description under its title (extra crawlable text)
- The page `<meta name="description">` now comes from the path
  description (first 160 chars) plus a matching `og:description`;
  paths without one fall back to a slug-based default instead of the
  old hardcoded "Create courses using links" (`metadesc` block in
  `base.html`)

### Team read checks

- Sleek round checkbox beside every link on any path: every logged-in
  user marks links as read (one row per link + user, toggles off again)
- Org admins (owner or admin role) and the path owner additionally see
  round avatar chips of exactly who completed each link, refreshed live
  on check - regular members only ever see their own checkbox. Chips
  stack compact: first 3 avatars plus a "+N" badge, the rest revealed
  on hover
- New `link_checks` table (migration `45c0384abf41`), new
  `POST /linkolearn/check_link` toggle
- Saving the edit page no longer wipes everyone's read progress:
  the rebuild now reuses existing section/link rows (matched by title,
  then shared link targets) instead of deleting and re-creating them,
  which had cascaded `Link.checks` away on every save - even a
  description-only change. Checks still die when a link or section is
  genuinely removed from the form

### Links

- Inline "Add link" on the path page now stores markdown input
  (`[Description](url)`) raw, exactly like the edit-page textarea, so it
  renders `<a href="url">Description</a>` instead of unwrapping to
  `<a href="url">url</a>` (raw URL as the link text)

### Pricing

- `/activate` card prices aligned with the live Dodo products: Pro is
  **$5/year** (was $3), Enterprise is **$15/year** (was $10) - the page
  previously advertised different amounts than checkout actually charged

## 1.9.0

### MCP server (auth)

- Every unauthenticated `/mcp` request is now answered with **HTTP 401** and
  `WWW-Authenticate: Bearer resource_metadata=...` instead of an in-band
  JSON-RPC error: MCP clients decide "needs OAuth?" at handshake time, so
  an anonymous 200 on `initialize` suppressed their sign-in flow entirely
  (TUIs showed "connected" while every personal tool failed). The gate
  validates tokens against `/oauth/userinfo` (cached 60s), fails closed
  without a token, and lets CORS preflights through
- `/.well-known/oauth-protected-resource` now advertises
  `resource: <host>/mcp` (was `/api/v1`); resource-indicator-validating
  clients rejected the mismatch. Per-path metadata is noted for `/api/v1`
  if it ever needs its own discovery
- Public search stays anonymous on the website and `/api/v1/public/*`;
  only the MCP transport is gated

### Agents & docs

- New `/agents` page: the "How to add Linkversity MCP" guide moved off the
  landing page, plus a skill section pointing at `/agents/skill`
- New `/agents/skill`: `agents/SKILL.md` served as `text/markdown` -
  Agent Skill frontmatter, all 7 MCP tools with scopes, save-by-name
  workflow, guardrails, REST fallback and token guidance
- Landing hero gains a "Connect agents" pill -> `/agents`
- New blog post "How to Connect Agents to Linkversity" (MCP setup, OAuth
  token lifecycle, skill, guardrails); `/blog` posts de-first-personed to
  second person (quoted speech kept)

### Security

- Slack webhook payloads (`/slack/payload`, `/slack/options`) now require
  a valid `X-Slack-Signature` (HMAC-SHA256 `v0`, 5-minute replay window,
  constant-time compare, fail-closed when `SLACK_SIGNING_SECRET` is unset)
- `save_link_modal` submissions enforce section ownership: the target
  section must belong to the account linked to the submitting Slack user
  (previously an unsigned request with an existing workspace + section ID
  could write links into anyone's collection)

### Misc

- Subtle "Open source on GitHub" footer link on all pages

## 1.8.0

### Front theme

- Airbnb-inspired redesign of the front theme: Rausch coral `#FF385C`
  primary, ink `#222222` / muted `#6A6A6A` text, `#EBEBEB`/`#DDDDDD`
  hairlines and `#F7F7F7` page background; 16px radii, layered soft
  shadows and Inter throughout
- Sticky, blurred topbar with pill-style navigation; every existing route,
  script (GA, service worker, PWA install, password-match JS) and
  integration (Slack, Chrome, Product Hunt) is preserved
- The retuned `path-*` design system lives in `blocks/brand.html` and is
  inherited by all 13 front templates with unchanged class names, so the
  new look reaches every page at once

### Homepage

- New hero: an Airbnb-style split pairing the register card with a
  carousel card
- Carousel slides get per-slide radial tints, uncropped illustrations
  (`object-fit: contain` in place of a circular crop), step chips and
  story-style progress dots synced to the 12s animation; hovering pauses
  it and mobile stacks the slides
- "Explore latest" cards rebuilt: real titles (slug fallback), link and
  section counts, owner or org identity, section chips, a lock badge for
  protected paths and a 2-line title clamp; section headers gain coral
  eyebrow chips

### Path covers

- Paths get a **cover icon** chosen by the user: a new `Path.cover_icon`
  column (migration `71f72b1115f6`) plus a `PATH_ICONS` catalogue of 18
  labelled Font Awesome 5 icons with an "Auto" default
- Create and edit pages share `blocks/icon_picker.html` — a tile grid with
  the selection glowing coral, dark-mode styled and `aria-pressed` for
  assistive tech; the choice rides the existing JSON payload as `path_icon`
- The backend whitelists against the catalogue and falls back to "Auto" for
  anything else, since the stored value is echoed into a
  `fas {{icon}}` class attribute
- `Path.cover_style()` is now the single source of truth for a path's
  gradient, icon and monogram — crc32-derived (stable across restarts) with
  a chosen `cover_icon` overriding the icon; the landing cards and the new
  path-profile cover band both draw from it, so a path looks identical
  everywhere it appears
- The path profile header gets the cover band: a bleeding gradient banner
  with an oversized translucent monogram, a white glyph tile hanging off
  the edge, a link-count pill and a lock pill when the path is protected
- `fa-music` leaves the auto rotation, replaced by `fa-rocket`

### Bug fixes

- The path-profile glyph tile was clipped in half: it hung past the banner
  edge (`bottom: -20px`) inside a parent that had `overflow: hidden`. The
  cover no longer clips — the gradient stays rounded via `border-radius` —
  the monogram is contained by its own `.mono-clip` wrapper, and the band's
  bottom margin was increased so the hanging tile clears the breadcrumb nav

## 1.7.0

### ChatGPT integration

- New `apiv1` module (`/api/v1`): REST endpoints backing the ChatGPT/MCP
  integration — public collection search/detail/links, connected-user
  collections and links, a read-only study-plan preparation endpoint and an
  integration status endpoint; pagination, search over titles/slugs/section
  titles, in-memory rate limiting (120 req/min per token/IP), CSRF-exempt;
  access rules mirror `Path.can_edit()` (owner, editor, org owner, org
  admin/member) and never trust a user id from the caller — identity comes
  only from the bearer token; password-protected collections expose metadata
  but never links through the API
- OAuth 2.0 provider (`apiv1/oauth.py`): authorization-code flow with PKCE
  (S256/plain), RFC 7591 dynamic client registration, single-use 5-minute
  authorization codes, hashed 7-day access / 90-day refresh tokens, consent
  screen, userinfo endpoint and `/.well-known` discovery metadata; the API
  accepts OAuth access tokens everywhere a bearer token is accepted and
  enforces the `collections:read` scope (migration `a0698e947742` adds the
  `oauth_*` tables)
- New `mcp-server/`: standalone FastMCP process (streamable-http, stateless)
  exposing five tools — `search_public_collections`, `get_public_collection`,
  `list_my_collections`, `get_collection_links`, `create_study_plan` — that
  call the Flask API over HTTP and forward the caller's bearer token
- New `cha-gpt plugin/` folder: portable ChatGPT plugin package
  (`plugin.json`, `mcp.json` with OAuth declaration, logo/composer assets)
  ready to zip and upload

## 1.6.0

### PWA

- Install Linkversity as an app: an "Install app" pill in the homepage CTA
  row (beside Add to Chrome), shown only once the browser fires
  `beforeinstallprompt` (installable and not already installed); it triggers
  the native prompt and hides itself on install or dismissal
- Manifest now declares real icon sizes — generated `icon-192.png`,
  `icon-512.png` and a `maskable-512` from the logo, replacing a single
  300x300 PNG that was mislabelled as 72-512px (Chrome needs genuine 192 +
  512 icons to offer installation); added `id`, `lang` and `dir`
- `base.html` gains `theme-color` and `apple-touch-icon` plus the
  `apple-mobile-web-app-*` metas, so iOS add-to-home-screen gets the right
  icon, title and standalone chrome; service-worker registration is deferred
  to `window.load`
- Rework the service worker: it cached `/` once and served cache-first
  forever with no update path, pinning visitors to a frozen homepage; it is
  now network-first for navigations (fresh HTML online, cached shell
  offline) and cache-first for static assets, with `skipWaiting` /
  `clients.claim` and cleanup of superseded caches (cache name bumped to v2)

### Homepage

- "Buy Premium" moves out of the CTA bar and into the nav for logged-out
  visitors (crown icon, `www.activate`, active-state highlight), matching the
  signed-in "Go premium" entry; the signed-out nav is otherwise unchanged
- Sleek the CTA pills (Connect to Slack / Add to Chrome / Install app): one
  shared lighter style — smaller type, `gap` icon spacing, Tailwind color
  classes instead of inline `style`, and a subtle `shadow-sm hover:shadow-md`
  transition in place of the heavy `shadow-lg`

## 1.5.1

- Public path page no longer 500s for logged-out visitors: `AnonymousUser`
  was missing `is_pro()` / `is_enterprise()` / `is_enterprise_admin()`, so
  the unconditional `current_user.is_pro()` in the manage-access modal
  raised an UndefinedError

## 1.5.0

Unreleased: everything below shipped after the 1.4.0 tag.

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
- Slug is the canonical display on path pages: tab title, `og:title`,
  breadcrumb crumb, hero H1 (and the org-page card / edit-page header)
  show the URL slug instead of `path.title`, which silently overrode it
- Manage access moved into a modal off the owner toolbar (button beside
  the link-preview switch on org/pro paths): add-editor-by-username
  form, editor chips with remove and the org Team panel; free personal
  paths keep the inline card
- New "Remove previews" toolbar pill (Pro and above): confirms, then
  wipes title/description/image_url from every link on the path in one
  go (`POST /linkolearn/remove-all-previews`, owner or editor only)

### App pages

- Shared brand style extracted to `blocks/brand.html` + a cleaned `blocks/crown.html`
  partial (dropped ~4KB of Inkscape metadata per crown); all pages below draw
  from the same cards/pills/inputs/empty-states and dark mode
- Bookmarks (`/linkolearn/bookmarks`): hero with saved count, path-card grid
  showing titles + owner + Locked/Private badges, empty state
- Create (`/new/`): hero, details card (title + slug with `/username/` prefix
  and live availability check), restyled sections, coral "Create path" button
- Edit (`/linkolearn/settings/p/<id>/edit`) rebuilt in the same style: breadcrumb
  header, slug field with org-aware `/org/<org>/` or `/username/` prefix + live
  availability check (self-excluded via `exclude_path_id`), pre-filled sections
  as cards, coral "Save changes" + "Back to path" — dark mode included; the old
  gray profile sidebar, red section bars and blue buttons are gone; the header
  avatar shows the company logo for org paths, the creator's emoji otherwise
- Profile (`/<username>`): avatar + crown hero, name/@handle/enterprise chips,
  labeled stat pills (paths / private / likes), path-card grid, empty state
- Fix "Create Path" never submitting: `json_submit.sections` was never
  initialized (TypeError on the first push); remove the duplicated
  "extract from document" button
- Fix every profile page 500ing: `len()` is not a Jinja global — use `|length`
- Homepage: "Add to Chrome" pill (Chrome-blue, `fa-chrome`) linking to the
  Chrome Web Store listing, beside Connect to Slack

### Payments (Dodo)

- Dodo Payments integration for self-serve upgrades: hosted checkout for
  Pro ($3/year) and Enterprise ($10/year), created server-side from `/activate`
- New routes: `POST /dodo/checkout` (login + CSRF protected), `GET /dodo/return`
  (acknowledges the redirect; never fulfills), `POST /dodo/webhook`
  (CSRF-exempt, signature-verified)
- Fulfillment happens exclusively from signed webhooks (Standard Webhooks
  scheme via `client.webhooks.unwrap` on the raw body): `payment.succeeded` /
  `subscription.active` / `subscription.trialing` upgrade to the plan matching
  the purchased product; `subscription.cancelled` / `expired` / `on_hold`
  downgrade to Free, which switches off every plan-gated feature
- Upgrades are idempotent; events for other products on the same Dodo
  account are ignored; activation codes keep working as a fallback
- Config via env: `DODO_PAYMENTS_API_KEY`, `DODO_PAYMENTS_WEBHOOK_KEY`,
  `DODO_PAYMENTS_ENVIRONMENT`, `DODO_PRODUCT_ID_PRO`, `DODO_PRODUCT_ID_ENTERPRISE`

### Enterprise

- New per-path option for enterprise owners: **disable link previews** —
  links added to the path stay plain (no title/image fetch). Toggle lives in
  the path's Manage access card (`POST /linkolearn/set-preview-policy`,
  owner + enterprise only); the generate-preview buttons disappear and
  `generate_preview` refuses server-side while it's off
- Enterprise is now **companies / organizations**: enterprise users can
  create any number of orgs (name + optional logo) from the dashboard,
  switch between them, and attach members, domains and analytics per org
- Org logos: uploaded on creation or later ("Change logo", owner only),
  stored under `static/uploads/org_logos/`, shown on the dashboard, on
  linked path pages and on the public org page
- Public org pages at `/org/<slug>` list the organization's public paths
- Create-path page gets an "Organization" picker for org owners/members;
  slug uniqueness is per-org; members (who aren't on the enterprise plan
  themselves) can create org paths
- Org-linked paths now live under the organization: canonical URL is
  `/org/<org>/<path>`; `/<user>/<path>` redirects there; the create-page
  slug prefix shows `/org/<org>/` when an organization is selected
- Org path pages speak org, not person: breadcrumb is
  Home › Org › path (linking to the org page) and the hero shows the org
  logo + name with "by @creator" underneath
- Org page (`/org/<slug>`) gets a "Create path" button in the header for
  signed-in owners/members — links to the create page with the org
  preselected; hidden for anonymous visitors and non-members
- Path cards across the site show the organization identity for org
  paths: homepage "Explore latest" and bookmarks cards display the org
  logo (or a building glyph) + org name instead of the owner's avatar;
  profile path cards print the real `/org/<org>/<slug>` URL
- Path pages show the org badge (logo + name) linking to `/org/<slug>`
- Org management (members, domains) authorizes by org ownership or an
  admin member role, not by the global enterprise plan; add-member /
  add-domain now target the selected org
- `org` is a reserved username (public org pages live at `/org/...`)
- The org logo (or building glyph) on the dashboard org card links to
  the public org page, like the name beside it
- Team membership grants access to **all** paths in the org: `Path.can_edit`
  now resolves membership directly from `EnterpriseTeamMember` rows (owner,
  admin or member role) instead of the legacy single `user.team_id` pointer,
  `Path.is_org_member()` opens private org paths to any member, and the path
  page toolbar, edit page, add/move link and visibility switch all follow
  `can_edit`; viewers get read access but no edit controls
- Per-org management moved out of the enterprise dashboard:
  `/linkolearn/enterprise/` now only lists organizations (logo, name, link
  to the public page, Settings pill for owner/admins, New organization);
  the stats row and the Team/Analytics/Domains/Paths tabs are gone
- Analytics actually record now: `EnterpriseAnalytics.track_click` existed
  but was never called. Org path pages fire a keepalive fetch on link
  click (`POST /linkolearn/track-click`, public + CSRF) which logs the
  click per org with referrer, user agent and a parsed device type; the
  same-day dedupe also worked (the old filter compared a DATE against the
  DATETIME column, so every click spawned a fresh row instead of
  incrementing)
- Analytics rows resolve their link: the table shows Date, Path (linked
  `/org/<org>/<slug>` plus the section name after a `|`), the actual link
  URL (markdown links unwrap to the target, the label stays in the
  tooltip), Clicks, Country, Device instead of the opaque `Link #id`
- Analytics glyph switched to `fa-chart-bar`: `fa-chart-simple` is a
  Font Awesome 6 icon and the site loads FA 5.15, so it rendered blank
- New org settings page at `/org/<slug>/settings` (owner or admin member,
  others are bounced back to the org page): the dashboard's per-org
  management moved here wholesale — stats row (members, total clicks,
  custom domains) plus Members / Analytics / Domains tabs (add member by
  username with role, members table with remove, link-click table,
  add/remove custom domain), change logo below; a note spells out that
  members get access to all paths in the org (the Paths tab stays out,
  the org page already lists them)
- The public org page header gets a **Settings** pill beside Create path,
  shown to owners and admin members

### Migrations

- New revision `37910fefe751`: conditionally adds `paths.disable_previews`
  and `enterprise_teams.slug`/`logo_url` (skipped when already present,
  e.g. the dev box that got them by hand), backfills org slugs from the
  name and puts a unique constraint on `enterprise_teams.slug`
- `EnterpriseSettings.created_at` added to the model so it matches the
  real table (autogenerate had flagged it as a column to drop)
- The dev database is now alembic-managed: stamped at `afbf65aa806f`,
  upgraded to head; `flask db migrate` reports no drift

### Bug fixes

- Enterprise audit logging 500'd every add-member call
  (`EnterpriseAuditLog.save()` doesn't exist on a plain db.Model)
- Sign-in/register flashes no longer render raw HTML: replaced the legacy
  `notify_*` wrapper (a Bootstrap alert div + inline `<script>`) with plain
  text + proper categories, so the toast shows clean text in the right
  color; also drop the empty `flash('')` gray toasts on register
- Logout flash now shows as a green success toast
- Path page no longer 500s for non-Pro owners/editors: the upgrade links
  pointed at a non-existent `new.activate` endpoint (now `www.activate`)
- Create page's "remove section" (×) deleted the whole sections container
  instead of one section (three `.parent()`s landed on `#sections`); now
  uses `closest('.section')` on both the create and edit pages
- Enterprise link-preview toggle was a silent no-op: it sent the CURRENT
  state instead of the desired one, so the server never changed anything;
  fixed and synced across all instances, and the switch now also sits in
  the path owner toolbar next to Delete

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
