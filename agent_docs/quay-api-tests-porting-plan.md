---
tags:
  - quay
  - testing
  - project-plan
---

# Plan: Port quay-tests API Tests to quay/quay as Playwright

## Context

The `quay-tests` repo has ~450 API test cases across 6 Cypress files in `quay-api-tests/cypress/e2e/`. These have zero equivalent in quay/quay and are the biggest test coverage gap for upstream consolidation. PR quay/quay#4919 (merged 2026-02-17) already runs 1 of 6 files (`quay_api_testing_all.cy.js`, 97 tests) via an external Docker image built from this repo, but the tests live here in quay-tests — not in quay/quay — so they can't be reviewed in upstream PRs or run as part of the upstream CI.

**Decision:** Port directly to Playwright (matching quay/quay's migration direction). Skip the Docker-image expansion approach.

---

## Phase 1: Infrastructure + Smoke Tests ~~(3-5 days)~~ DONE

> **Status:** Complete. PR quay/quay#5715 open on branch `worktree-api-test-infrastructure`.

### 1.1 Helper infrastructure (DONE)

All helpers are integrated into the existing Playwright utils structure at `web/playwright/`:

**`web/playwright/utils/api/auth.ts`** — Programmatic auth (replaces browser-based OAuth flow)
- `initializeSuperuser(request, baseUrl, username, password, email)` — `POST /api/v1/user/initialize` (returns access_token, falls back to sign-in if 404 or already initialized)
- `getAccessToken(request, baseUrl, username, password)` — sign in + fetch CSRF token
- `createOAuthToken(request, baseUrl, csrfToken, orgName, appName)` — create org via API, create OAuth app, POST `/oauth/authorize` to get token without browser
- `getV2Token(request, baseUrl, username, password, scope)` — `GET /v2/auth?service=...&scope=...`

Source translated: `quay-api-tests/cypress/support/commands.js` lines 1-180

**`web/playwright/utils/api/raw-client.ts`** — Low-level HTTP wrapper returning raw `APIResponse`
- Holds `baseUrl` + CSRF token cache (auto-invalidated on sign-in)
- Methods: `get(path)`, `post(path, data)`, `put(path, data)`, `delete(path)`, `patch(path, data)`
- Returns full `APIResponse` for status code assertions in negative tests
- Complements the existing `ApiClient` (which throws on errors and is used for setup/teardown)

**`web/playwright/utils/image-ops.ts`** — Shell command wrappers
- `pushImage(hostname, user, pass, source, sourceTag, org, repo, targetTag)` — `execFileSync('skopeo copy ...')`
- `pushImageAll(...)` — same with `--all` for manifest lists
- `orasAttach(hostname, namespace, repo, user, pass, tag, artifactType, annotation, path)` — `execFileSync('oras attach ...')`
- `isSkopeoAvailable()`, `isOrasAvailable()` — tool availability checks

Source translated: `quay-api-tests/cypress/support/commands.js` lines 200-311

**`web/playwright/shared/csrf.ts`** — Shared CSRF token fetch (used by both `RawApiClient` and `ApiClient`)

**`web/playwright/shared/test-utils.ts`** — `uniqueName(prefix)` utility (used by both API and UI tests)

### 1.2 Playwright API config (DONE)

**`web/playwright/api/playwright.api.config.ts`**
- No browser needed — uses Playwright's `request` context only
- `testDir: './suites'`
- `fullyParallel: false`, `workers: 1` (tests within a file are serial)
- `timeout: 60_000` per test (some API calls are slow)
- Reporters: GitHub (CI) + JSON output

### 1.3 API fixtures (DONE)

**`web/playwright/api/fixtures.ts`**
- Worker-scoped: `_adminInitialized` (init or sign-in), `_testUserInitialized` (self-registration)
- Test-scoped: `adminClient`, `userClient`, `anonClient` (all `RawApiClient` instances)
- Credentials from env vars with defaults matching CI setup

### 1.4 Smoke tests (DONE)

**`web/playwright/api/suites/smoke.spec.ts`** — 5 tests validating the infrastructure:
- Admin org CRUD, repo creation, 403/401 permission boundaries

### 1.5 Port `quay_api_testing_all.cy.js` (NEXT)

**`web/playwright/api/suites/api-v1-superuser.spec.ts`**

Translation pattern:
```typescript
// Cypress:
cy.request({ method: "POST", url: `${endpoint}/api/v1/organization/`,
  headers: { authorization }, body: { name: org_name, email: "test@test.com" } })
  .then(response => { expect(response.status).to.eq(200); });

// Playwright:
const response = await client.post('/api/v1/organization/', {
  name: org_name, email: "test@test.com"
});
expect(response.status()).toBe(200);
```

Structure: `test.describe.serial('Quay API v1', () => { ... })` to preserve execution order.

**What to skip/change:**
- Remove the `create Quay Oauth Token` UI test (dead code, line 406 DOM assertion)
- Remove hardcoded Red Hat registry credentials — skip mirror sync tests, or parameterize via env
- Replace `cy.wait(300000)` with `expect.poll()` (5s intervals, 300s timeout)
- Mark vulnerability tests with `test.skip` + `// Requires Clair` comment
- Replace `cy.push_image()` calls with `pushImage()` from `image-ops.ts`

### 1.6 Workflow changes (TODO)

Modify `.github/workflows/qe-tests.yaml`:
- Add a new job `qe-api-tests-playwright` alongside the existing Docker-image job
- Install `skopeo` and `oras` in the runner
- Run: `npx playwright test --config playwright/api/playwright.api.config.ts`
- Keep the Docker-image job running for comparison during transition

Add trigger paths:
```yaml
paths:
  - "endpoints/**"
  - "web/playwright/api/**"
  - "web/playwright/utils/**"
  - "web/playwright/shared/**"
  - ".github/actions/setup-quay/**"
  - ".github/workflows/qe-tests.yaml"
```

---

## Phase 2: Port remaining test files (5-7 days)

### 2.1 Superuser-exclusive tests

**`web/playwright/api/suites/api-v1-superuser-exclusive.spec.ts`**

Source: `quay_api_testing_super_user.cy.js` — only endpoints NOT covered by `_all`:
- Service keys: create, approve, list, update, delete
- Take ownership: `POST /api/v1/superuser/takeownership/{namespace}`
- Create install user: `POST /api/v1/superuser/users/`
- Changelog: `GET /api/v1/superuser/changelog/`
- Aggregate logs: `GET /api/v1/superuser/aggregatelogs`
- All logs: `GET /api/v1/superuser/logs`
- Tag restore: `POST /api/v1/repository/{ns}/{repo}/tag/{tag}/restore`
- Prototypes (default perms): CRUD via `/api/v1/organization/{org}/prototypes`

### 2.2 Normal user permission boundaries

**`web/playwright/api/suites/api-v1-normal-user.spec.ts`**

Source: `quay_api_testing_normal_user.cy.js`

Auth setup:
1. Initialize superuser via API
2. Create normal user via `POST /api/v1/superuser/users/`
3. Generate OAuth token for normal user

Tests verify: same CRUD operations as superuser but from a non-privileged user. Key value is testing that superuser-only endpoints return 403.

### 2.3 Readonly superuser restrictions

**`web/playwright/api/suites/api-v1-readonly-superuser.spec.ts`**

Source: `quay_api_testing_gobal_readonly_supuer_user.cy.js`

Most complex auth — requires 3 tokens:
1. Normal user token (creates test data)
2. Readonly superuser token (verifies read access, verifies write blocked)
3. Full superuser token (admin operations)

`setup-quay` extra-config must include:
```yaml
GLOBAL_READONLY_SUPER_USERS:
  - readonly_admin
```

### 2.4 Immutability policy tests

**`web/playwright/api/suites/api-v1-immutability.spec.ts`**

Source: 21 unique tests from `quay_api_testing_all_new_ui.cy.js` (the rest is a duplicate of `_all`).

`setup-quay` extra-config: `FEATURE_IMMUTABLE_TAGS: true`

### 2.5 V2 Registry API

**`web/playwright/api/suites/api-v2.spec.ts`**

Source: `quay_api_v2_testing.cy.js` — only tests not already inline in `_all`.

Auth: V2 Bearer token via `GET /v2/auth?service=...&scope=...` with Basic auth (use `getV2Token` from `auth.ts`).

### 2.6 Workflow: matrix strategy

```yaml
strategy:
  matrix:
    suite:
      - api-v1-superuser
      - api-v1-superuser-exclusive
      - api-v1-normal-user
      - api-v1-readonly-superuser
      - api-v1-immutability
      - api-v2
```

Each suite gets its own `setup-quay` instance with appropriate config.

---

## Phase 3: Cleanup + Clair (future, 5-10 days)

- Remove Docker-image-based job from `qe-tests.yaml` once Playwright tests are stable (2+ weeks)
- Enable Clair in a separate workflow job for vulnerability API tests
- Optionally refactor from `test.describe.serial` to independent tests with Playwright fixtures
- Remove ported files from quay-tests repo

---

## Critical source files

| File | Purpose |
|---|---|
| `quay-tests/quay-api-tests/cypress/support/commands.js` | All custom commands to reimplement (OAuth, skopeo, oras) |
| `quay-tests/quay-api-tests/cypress/e2e/quay_api_testing_all.cy.js` | Primary file (97 tests), port first |
| `quay-tests/quay-api-tests/cypress/e2e/quay_api_testing_super_user.cy.js` | Unique superuser endpoints |
| `quay-tests/quay-api-tests/cypress/e2e/quay_api_testing_normal_user.cy.js` | Permission boundary tests |
| `quay-tests/quay-api-tests/cypress/e2e/quay_api_testing_gobal_readonly_supuer_user.cy.js` | 3-role auth pattern |
| `quay-tests/quay-api-tests/cypress/e2e/quay_api_v2_testing.cy.js` | V2 API tests |
| `quay-tests/quay-api-tests/cypress/e2e/quay_api_testing_all_new_ui.cy.js` | 21 unique immutability tests |
| `quay/quay:.github/workflows/qe-tests.yaml` | Workflow to modify |
| `quay/quay:.github/actions/setup-quay/action.yaml` | Composite action (may need new config inputs) |

## ~~Open question~~ Resolved

**Programmatic OAuth token generation**: Verified that Quay's `/oauth/authorize` endpoint accepts a POST without browser interaction. The `createOAuthToken` function in `web/playwright/utils/api/auth.ts` handles the redirect-based token extraction (reads `access_token` from the `Location` header fragment or response body).

## Verification

1. **Phase 1**: Run Playwright API tests alongside Docker-image Cypress tests. Compare pass/fail counts — Playwright should match Cypress (minus skipped vuln tests).
2. **Phase 2**: Total Playwright test count should be ~350 (450 minus duplicates in `_all_new_ui` minus vuln tests).
3. **Each phase**: Open PR on quay/quay, verify `qe-tests` workflow passes, review CTRF report in PR comments.


---

## PR Roadmap (added 2026-04-13)

| PR | Title | Est. Lines | Est. Tests | Dep | Status |
|----|-------|-----------|------------|-----|--------|
| 1 | API Test Infrastructure (config, fixtures, helpers) | ~400-500 | 5 smoke | — | **PR #5715 open** |
| 2 | Organization & User API Tests | ~400-500 | 20-25 | PR 1 | |
| 3 | Repository API Tests | ~400-500 | 20-25 | PR 1 | |
| 4 | Repository Features (perms, notifs, tags, builds) | ~500-600 | 25-30 | PR 1 | |
| 5 | Advanced Features (quotas, proxy cache, mirror, messages) | ~450-550 | 20-25 | PR 1 | |
| 6 | Superuser-Exclusive Endpoints | ~500-600 | 40-50 | PR 1 | |
| 7 | Permission Boundary Tests (normal user 403s) | ~400-500 | 40-50 | PR 1 | |
| 8 | Readonly Superuser Role Tests (3-role auth) | ~400-500 | 30-40 | PR 1 | |
| 9 | Immutability API Tests (unique from new_ui) | ~350-450 | ~21 | PR 1 | |
| 10 | V2 Registry API Tests (+ V2 client helper) | ~600 | 30-40 | PR 1 | |
| 11 | CI Workflow Integration (qe-tests.yaml) | ~100-150 | 0 | PR 1 | |

**Dependency graph:** PRs 2-10 can be developed in parallel after PR 1 merges. PR 11 ideally after PRs 2-3.

**Architecture:** All API tests live under `web/playwright/api/` with their own config (no browser, serial execution). Helpers are integrated into the existing `web/playwright/utils/` structure:
- `RawApiClient` at `web/playwright/utils/api/raw-client.ts` — returns raw `APIResponse` for status code assertions
- `ApiClient` at `web/playwright/utils/api/client.ts` — existing high-level client (81 methods, throws on error), used for setup/teardown
- Auth helpers at `web/playwright/utils/api/auth.ts`
- Image ops at `web/playwright/utils/image-ops.ts`
- Shared CSRF + test utils at `web/playwright/shared/`
- API fixtures at `web/playwright/api/fixtures.ts`

**Source location:** All source Cypress tests are in the `quay-tests` repo (this repo) at `quay-api-tests/cypress/`. No container extraction needed — reference the files directly:
- Test files: `quay-api-tests/cypress/e2e/quay_api_testing_*.cy.js`
- Custom commands/helpers: `quay-api-tests/cypress/support/commands.js`
- Config: `quay-api-tests/cypress.config.js`

---

## Structure Update — 2026-04-14

> **The sections above reference an outdated directory structure.** PR #5715 was reworked to consolidate API tests into the main Playwright suite. This section supersedes all path/config references above.

### What changed

The separate API test infrastructure (`web/playwright/api/`) was merged into the main suite. There is now **one Playwright config, one fixtures file, one test directory**.

### Old → New path mapping

| Old path (references above) | New path |
|---|---|
| `web/playwright/api/playwright.api.config.ts` | **Deleted** — uses main `web/playwright.config.ts` |
| `web/playwright/api/fixtures.ts` | **Deleted** — fixtures merged into `web/playwright/fixtures.ts` |
| `web/playwright/api/suites/smoke.spec.ts` | `web/playwright/e2e/api/smoke.spec.ts` |
| `web/playwright/api/suites/*.spec.ts` | `web/playwright/e2e/api/*.spec.ts` |
| `web/playwright/shared/csrf.ts` | `web/playwright/utils/api/csrf.ts` |
| `web/playwright/shared/test-utils.ts` | `web/playwright/utils/test-utils.ts` |

### Updated architecture

- **All API tests** live under `web/playwright/e2e/api/` alongside UI tests in `web/playwright/e2e/`
- **API tests are tagged `@api`** and filtered via `--grep @api` (no separate Playwright config)
- **API fixtures** (`adminClient`, `userClient`, `anonClient`) are in the main `web/playwright/fixtures.ts`, using `playwright.request` (no browser)
- **Tests are parallel** — each test is self-contained with inline cleanup (no serial execution, no shared state)
- **`PLAYWRIGHT_SKIP_WEBSERVER=1`** is set by `npm run test:api` to skip the frontend build

### Running tests

```bash
npm run test:e2e          # All tests (UI + API together)
npm run test:api          # Only @api tests (no browser, no frontend build)
npm run test:e2e:no-api   # Only UI tests
```

### Impact on future PRs

When porting test files (PRs 2-10 in the roadmap above), place them at:
- `web/playwright/e2e/api/api-v1-superuser.spec.ts` (not `web/playwright/api/suites/`)
- Tag all describe blocks with `{tag: ['@api', '@auth:Database']}`
- Use `adminClient`/`userClient`/`anonClient` from `../../fixtures`
- Tests should be parallel and self-contained (create + cleanup per test)

### Workflow paths update

For section 1.6 workflow triggers, replace:
```yaml
# Old
- "web/playwright/api/**"
- "web/playwright/shared/**"

# New
- "web/playwright/e2e/api/**"
- "web/playwright/utils/**"
```
