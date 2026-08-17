# Implementation Status

## Consumer Portal richer data + no raw IDs as names + real "outstanding" bug

- **No more raw IDs where a name belongs**: `SimpleCrud` (covers Territory's
  9 levels, Sub-Categories, VEE Schedule, Bill Schedules, Meter Schedules)
  now auto-resolves any table column whose key matches a form field with
  `optionsEndpoint` to that option's label, reusing the same lookup already
  used for the edit/view form -- no per-page wiring needed. The one
  hand-built page with the same issue (Readings' "Meter" column) was fixed
  directly.
- **Consumer Portal now has real history, not 2 data points**:
  `demo_data.py` generates 7 rounds of meter readings/bills over ~7 months
  (was 2) with a shared seasonal usage curve, so the portal's consumption
  chart and bill history look like a real customer's data. Payment
  behavior is now applied per round with a realistic mixed policy (always
  pays in full / always pays half / pays in full but misses every 3rd bill
  / never pays -- delinquent) instead of one payment on the final bill only.
  Noah Thompson still deliberately gets stuck in Revisit at round 2 (VEE
  demo) and is left unread afterward, a realistic "blocked until resolved"
  account.
- **Real bug found while building the above**: `Bill.total_outstanding` is
  a point-in-time snapshot of the running balance *as generated* (by
  design -- see `compute_outstanding`) and is never updated after a
  payment. Every "Outstanding" column and the portal's dashboard total was
  reading that raw field directly, so a fully-paid bill still displayed
  its full original amount next to a "paid" badge. Fixed by adding a
  computed `Bill.remaining_balance` (total_outstanding minus payments
  recorded against that specific bill, floored at 0) and switching every
  "Outstanding" display (admin Billing list + detail modal, portal Bills
  list + dashboard) to it. The stored `total_outstanding` field itself is
  untouched -- it's still what the billing engine chains forward into the
  next bill's `previous_outstanding`.
- Consumer Portal Profile page now surfaces plan (name/frequency/tax%),
  meter (no/device/read type), activation date, and first meter reading --
  previously only name/email/contact/addresses. Consumption page adds
  summary stats (latest/average/total usage, trend vs. previous cycle) and
  a reading-history table under the chart. Bills page adds a paid/
  outstanding summary header.

41/41 backend tests pass. Verified live: portal consumption chart now
shows 7 real points; a fully-paid consumer (Emma) shows $0 everywhere it
should; a never-pays consumer (Ethan) shows correctly compounding
outstanding; Territory/Sub-Category tables show parent names, not UUIDs.

## PDF viewing bug + custom roles + email-invite-to-set-password

- **Real bug fixed**: every "View PDF" link (admin Billing, Consumer
  Portal) used a plain `<a href target="_blank">`, which can't carry our
  JWT bearer token -- browsers only attach it via axios requests, never
  on native navigation -- so opening one 401'd with `{"detail":"Not
  authenticated"}`. Fixed everywhere via `lib/files.ts`'s
  `openAuthenticatedFile()`: fetches the PDF as a blob through the
  authenticated API client, then opens it via a programmatic `<a>` click
  (not `window.open(blobUrl)`, which recent Chromium silently refuses to
  navigate a *new* window to).
- **Custom roles**: `/users` → Roles tab → "+ Create Role" -- pick a name,
  description, and exact permissions from the full module/resource/action
  catalogue (`GET /permissions`), then assign it to invited users like any
  system role. System (workbook) roles remain read-only; custom roles can
  be edited or deleted (blocked while still assigned to a user).
- **Invite-by-email, set-your-own-password**: `POST /users` no longer
  generates a temp password. It creates the account locked (an unrevealed
  random password), emails an invite link carrying a 7-day single-purpose
  token (`POST /auth/set-password` consumes it and logs the user straight
  in), and returns that same link in the API response either way. SMTP is
  configured via `SMTP_HOST`/`SMTP_FROM_EMAIL`/etc. in `backend/.env`
  (see `.env.example`); with nothing configured (this sandbox's default),
  `send_email()` logs a warning and returns `False` instead of sending --
  the Users page shows the invite link directly with a Copy button so the
  flow still works end-to-end in dev. Onboarding (Utility Admin) and
  Consumer creation are unchanged (still show a temp password directly);
  only the new staff-invite flow moved to this pattern.

41/41 backend tests pass (added role-CRUD and invite/set-password
coverage). Verified live end-to-end: PDF fetch returns 200 and opens,
a custom role was created and immediately usable, and an invited user
activated their own account via the emailed-style link and landed on a
dashboard correctly scoped to just their role's permissions.

## User invitation + role assignment + real permission visibility

New `/users` page (Utility Admin+ only): invite a staff user (name, email,
role) -- generates a one-time temp password shown in-app (no email
service yet, same pattern as onboarding/consumer creation), view/edit a
user's name/role/active status, and a **Roles** tab showing each role's
real permission list (module/resource/action) pulled live from the DB,
not hard-coded copy. Backend: `POST/GET/PATCH /users`, `GET /roles`,
`GET /roles/{id}`; new `users` permission module granted to Utility
Admin. `/auth/me` now returns `permission_modules` (the distinct set of
modules the caller's roles actually grant), and the sidebar nav filters
against that in real time instead of a hard-coded role→page map -- an
invited BX Manager sees only Dashboard + Billing, a CSR sees only
Dashboard + Consumers, etc., automatically, from whatever role they were
assigned.

Also fixed while verifying PDFs: the bill PDF's meter row was showing a
raw internal meter UUID instead of the human-readable meter number.

## Completed — Phases 1-8

**Phase 1 — Repository + DB + Docker + Auth + RBAC + Tenant isolation**
Backend (FastAPI/SQLAlchemy/Alembic) + Frontend (Next.js/TS/Tailwind) scaffolds,
JWT auth, module→resource→action RBAC, server-side tenant isolation, Docker
Compose (postgres/redis/backend/frontend), seed script.

**Phase 2 — Super Admin + Utility onboarding + Utility Admin**
`/admin/tenants` full CRUD + activate/suspend + logo upload, one-call
onboarding (tenant + cloned roles/permissions + Utility Admin login),
Super Admin dashboard, platform audit log viewer, Utility Services
catalogue + per-tenant toggle.

**Phase 3 — Territory + Services + Categories + Rates + Plans**
Full 9-level territory hierarchy (Region→Premise) with cascading FKs,
Category/Sub-Category, a real **rate engine** (fixed / per-unit-area /
tiered / time-of-use — no hard-coded example values, unit tested against
the workbook's own numbers), Plans with multi-service rate components,
Service Charges.

**Phase 4 — Consumers + Meters**
Consumer creation flow (Premise→Plan→Meter→Initial Reading) with ID
document upload, auto-created Consumer Portal login, meter
assignment/availability tracking. Meter inventory with premise-based
auto-population fields.

**Phase 5 — Routes + Read Cycles + Meter Schedules + Meter Runs**
Auto meter-count/premise-count from real associations, manual "Generate
Run" API (+ idempotent Celery Beat task for production).

**Phase 6 — Meter Reading Upload + VEE + V1/V2/Revisit**
Manual entry + CSV/XLSX upload (original file + every raw row preserved
regardless of validity), a real VEE rule engine (No Reading / Threshold
Alert, extensible), full Received→V1→V2→Revisit→Completed state machine,
validation breakdown dashboard, revisit resolution flow.

**Phase 7 — Billing Engine + Bill Cycle/Template/Schedule/Run**
A real, deterministic, unit-tested billing engine: consumption →
plan/rate lookup → rate-engine charge → service charges → tax →
credits/debits → outstanding-balance carry-forward (verified against a
two-bill sequence with a partial payment) → persisted Bill + line items.
Bill Cycle/Template/Schedule/Run CRUD, manual "Generate Run" (+ Celery
Beat task).

**Phase 8 — PDF Bills + Consumer Portal + Payments**
Real PDF generation (reportlab) from stored bill data — branding,
customer/invoice/meter/consumption/charges/tax/outstanding, recent
payment history; view/download both from the admin Billing screen and
the Consumer Portal. Consumer Portal (dashboard, bill history, PDF,
consumption chart, meter, plan, payment history, limited profile edit)
strictly scoped server-side to the caller's own consumer record. Payment
recording against bills with automatic paid/partially_paid status.

### Verification performed
- 29 backend unit/integration tests passing, including a full
  `Create Utility → Configure → Consumer → Meter → Reading → VEE → Bill`
  integration test driven through the real HTTP API (not direct DB
  access), asserting exact tiered-rate billing math.
- Alembic migration (`phase2_8_domain_model`) verified with zero drift
  against all ORM models; Postgres-portable SQL.
- Frontend: `npm run build` + `tsc` clean across all 17 routes; a live
  headless-browser run drove SuperAdmin onboarding → Utility Admin login
  → service toggle → territory creation end-to-end against the real API
  with zero console errors (screenshots confirmed).
- Known simplification: TOU billing splits consumption across windows
  proportionally to each window's share of 24h (no per-interval AMI data
  model yet) — documented in `app/services/rate_engine.py`. Bill PDF
  history sections are tables, not charts (no charting lib added to the
  PDF pipeline).
- Docker/Postgres have not been run in this build environment (neither
  is installed here) — see README's "Notes on this build environment".
  Everything else was verified against SQLite as a stand-in, with the
  migration checked for Postgres-portable SQL.

## View + Edit + Bill visibility (post-showcase follow-up)

CLAUDE.md §29 requires list/create/edit/view/delete on every CRUD page;
Phase 1-8 had only shipped list+create. Added:

- **`SimpleCrud` now supports View/Edit/Delete** (covers Territory's 9
  levels, Categories, Sub-Categories, Service Charges, VEE Rules, VEE
  Schedules) -- View shows a read-only detail panel, Edit pre-fills the
  same form and PATCHes, Delete confirms then removes. Fields the
  backend's `*Update` schema doesn't actually accept are marked
  `readOnlyOnEdit` so the UI never implies an edit that won't persist.
- **Hand-built pages** (Rate, Plan, Consumer, Utilities, Meter,
  Route/Read Cycle/Meter Schedule, Bill Cycle/Template/Schedule) got
  matching View/Edit modals, and the missing backend `GET .../{id}` +
  `PATCH .../{id}` endpoints they needed (previously only Meter, Plan
  and Consumer had them).
- **Bills**: a real on-screen "View" invoice (consumer info, full charge
  breakdown, tax, outstanding, payments applied) via a new
  `GET /bills/{id}/detail` endpoint -- not just a PDF link.
- **Root cause of "can't see bills"**: the PDF endpoints set
  `Content-Disposition: attachment`, which silently downloads the file
  instead of opening it in the browser tab. Fixed to `inline` on both
  the admin and consumer-portal PDF routes.
- Entities without a real DELETE endpoint (Meter, Route, Read Cycle,
  Meter Schedule, Bill Cycle, Bill Template, Bill Schedule, VEE Config)
  show View/Edit but not a Delete button, rather than a button that 404s.

## Bug fixes since Phase 8 (found via manual testing + building the showcase dataset)

- **Frontend nav**: SuperAdmin was shown links to tenant-only pages
  (Territory, Consumers, Billing, ...) that always 403 for a SuperAdmin
  (no tenant_id). Nav now correctly scopes to Dashboard + Utilities only.
- **Frontend error handling**: the shared `SimpleCrud` list component (and
  several hand-built pages) swallowed failed API calls and rendered an
  *empty* table indistinguishable from "no records yet." Every list/form
  across the app now surfaces the real backend error message.
- **Invisible form text**: no input/select had an explicit background/text
  color, so browsers rendered them with native dark-mode UA styling
  whenever the OS/embedder (e.g. VS Code's built-in browser) preferred
  dark — unreadable input text. Pinned `color-scheme: light` and made
  every form control's colors explicit.
- **VEE readings stuck at "V2" forever**: `evaluate_reading()` only
  advanced one pipeline stage per call; a reading that failed V1 sat at
  status "V2" until something called it again, which nothing did outside
  the (not-running-in-this-sandbox) Celery sweep. Now resolves fully to
  Completed/Revisit in one call.
- **VEE/billing consumption miscalculated for a meter's first-ever
  reading**: with no prior `MeterReading` row, "previous reading" was
  treated as 0, so consumption was the full cumulative meter value
  instead of the actual delta — spuriously failing every threshold rule.
  Added `app/services/reading_helpers.get_previous_reading()`, which
  falls back to the consumer's own First Meter Reading (workbook §11) as
  the baseline.
- **Ambiguous "latest bill for consumer" ordering**: `compute_outstanding`
  and the portal's "current bill" query ordered only by `invoice_date`
  (day granularity) — two bills generated the same day had an undefined
  tiebreak, corrupting outstanding-carry-forward. Added `created_at` as a
  secondary sort key, and made `created_at`/`updated_at` use a
  microsecond-precision Python-side default instead of relying on
  SQLite's 1-second `CURRENT_TIMESTAMP` resolution.

## Showcase demo data

`app/services/demo_data.py` (idempotent, run after `seed.py`) populates
the Demo Water Utility tenant end-to-end: 2 territory areas / 6 premises,
3 rate types (tiered/fixed/TOU) across 3 plans, 6 consumers with meters,
5 routes/read-cycles/schedules/runs, two rounds of readings (11
Completed, 1 deliberately in Revisit to demo the VEE workflow), two bill
runs with real outstanding-carry-forward, PDFs, and paid/partially-paid/
unpaid bills. See `SEED_CREDENTIALS.md` for consumer portal logins.

## Current
- None in progress — ready to start Phase 9.

## Next — Phase 9: OEM catalogue + Mock Meter API + Audit + Reports

- Smart Meter OEM catalogue is seeded (`app/services/seed.py`) but has
  no admin UI yet.
- Mock smart-meter provider (integration abstraction + one provider that
  can push readings in) not yet built — `integration_configs` table exists.
- Tenant-level audit log viewer (platform-level one exists at
  `/admin/audit-logs`; tenant admins have no `/audit` UI yet).
- Reports module (`reports` permission module exists; no endpoints/UI yet).

Then **Phase 10**: Docker/Postgres actually run end-to-end, frontend
Playwright specs (login/create consumer/create meter/upload
reading/view bill), production polish.
