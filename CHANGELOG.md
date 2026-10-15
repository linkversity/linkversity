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
- Slug is the canonical display on path pages: tab title, `og:title`,
  breadcrumb crumb, hero H1 (and the org-page card / edit-page header)
  show the URL slug instead of `path.title`, which silently overrode it

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
