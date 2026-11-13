# API Surface Inventory and Migration Map

Status: Expanded
Last updated: 2026-02-09

## 1. Purpose

Track every endpoint contract that must be preserved and migrated.

## 2. Authoritative registration points

- `web.py`
- `registry.py`
- `secscan.py`

## 3. Exhaustive source-of-truth artifacts

- Route rows and decorators:
  - `plans/rewrite/generated/route_inventory.md`
- Supplemental non-blueprint routes (`app.add_url_rule`):
  - `plans/rewrite/generated/non_blueprint_route_inventory.md`
- Route migration tracker (method-level):
  - `plans/rewrite/generated/route_migration_tracker.csv`
  - `plans/rewrite/generated/route_migration_tracker_summary.md`
- Suggested route-family rollout ordering:
  - `plans/rewrite/generated/route_family_cutover_sequence.md`
- Counts by route family:
  - `plans/rewrite/generated/route_family_counts.md`
- `show_if` / `route_show_if` feature gates:
  - `plans/rewrite/generated/feature_gate_inventory.md`
- Coverage audit:
  - `plans/rewrite/generated/http_surface_coverage_audit.md`

## 4. Baseline counts (current)

From static parse:
- Flask-RESTful `@resource` routes: `176`
- `v1_bp` routes: `24`
- `v2_bp` routes: `19`
- Other blueprint route rows: `84+`
- Dynamic OAuth callback patterns via `add_url_rule`: `4`
- App-level non-blueprint `add_url_rule` patterns: `3` (`/userfiles` GET/PUT and `/_storage_proxy_auth` GET)
- Method-level route tracker rows (including supplemental non-blueprint routes): `413`

## 5. Route family commitments

### 5.1 Registry
- `/v1/*` full behavior parity required.
- `/v2/*` full behavior parity required.
- Includes auth flow and feature-gated routes such as referrers and v2 advertise route behavior.

### 5.2 Quay REST API
- `/api/v1/*` via Flask-RESTful `@resource` classes.
- Includes multi-URL class resources (for example in superuser quota routes).

### 5.3 Non-`/api/v1` contract surfaces
- `/oauth2/*`: login callback, attach callback, CLI callback, captcha callback (dynamic route registration).
- `/oauth1/*`: bitbucket callback.
- `/webhooks/*`: stripe and build trigger webhooks.
- `/keys/*`: service key APIs.
- `/secscan/*`: secscan callback and status.
- `/realtime/*`: SSE subscriptions.
- `/.well-known/*`: capabilities and password-change redirect.
- `web` blueprint endpoints used by UI/API clients (`/config`, `/csrf_token`, health routes, oauth grant endpoints, initialize endpoint, build/log links).
- App-level routes registered outside blueprints/resources (`/userfiles/*`, `/_storage_proxy_auth`).

## 6. Gaps found vs earlier draft

1. Dynamic OAuth callback routes were under-accounted; these are now explicitly inventoried.
2. Feature-gated route behavior is extensive and must be migrated as a compatibility matrix, not as simple static routes.
3. `/v1/*` and `/v2/*` counts are lower than some earlier rough counts due deduped static parse (`24` and `19` respectively), but still fully in scope.
4. `web` blueprint has a large contract-adjacent surface (`66` route rows) that includes operational and OAuth endpoints; these must be triaged, not ignored.
5. Route scanning that only targets `endpoints/*` misses app-level routes registered from `data/userfiles.py` and `storage/downloadproxy.py`; these are now explicitly tracked.

## 7. Migration ownership policy

- `registryd` owns `/v1/*` and `/v2/*`.
- `api-service` owns `/api/v1/*`, `/oauth*`, `/webhooks/*`, `/keys/*`, `/secscan/*`, `/realtime/*`, `/.well-known/*`, and selected `web` blueprint contract endpoints.
- `api-gateway` (or equivalent edge layer) owns route-to-owner decisioning and canary routing.

## 8. Tracker status and next action

Completed:
- Endpoint-by-endpoint method-level tracker generated in:
  - `plans/rewrite/generated/route_migration_tracker.csv`
- Unknown `auth_mode` rows resolved in:
  - `plans/rewrite/generated/route_auth_verification.md` (0 unresolved)
- Auth verification execution backlog generated in:
  - `plans/rewrite/generated/route_auth_verification_checklist.csv`
  - `plans/rewrite/generated/route_auth_verification_checklist_summary.md`
  - `plans/rewrite/generated/route_auth_manual_backlog.md`
  - `plans/rewrite/generated/route_auth_review_waves.md`
  - `plans/rewrite/generated/route_auth_auto_verification_report.md`
  - current checklist status after closure pass: `source-anchored-needs-review=0`, `verified-source-anchored=413`
- Expression-based parser path gaps documented in:
  - `plans/rewrite/generated/route_parser_gaps.md`

Tracker columns include:
- method
- full path template
- source file/symbol/blueprint
- feature gate expression(s)
- inferred auth mode
- contract test ID
- go owner package
- cutover switch ID
- rollback switch ID

Next required action:
- promote `verified-source-anchored` rows to `verified` with owner signoff/test evidence in signoff batches.
- keep automation in sync via `plans/rewrite/scripts/route_auth_auto_verify.py`.
- route review waves are now fully pre-verified (`A1`..`A4` backlog = 0); remaining work is owner signoff promotion.
- canonicalize parser-gap routes into stable fixture IDs and path templates.

Route count consistency note:
- `route_family_counts.md` reports `web=66` blueprint rows while `route_migration_tracker.csv` currently tracks `web=65` method rows.
- Treat this as an explicit reconciliation item before M0 exit.
