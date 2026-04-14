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

## Architecture

All API tests are integrated into the main Playwright suite — one config, one fixtures file, one test directory. API tests are distinguished by the `@api` tag.

**Test location:** `web/playwright/e2e/api/*.spec.ts` (alongside UI tests in `web/playwright/e2e/`)

**Fixtures:** `adminClient`, `userClient`, `anonClient` (all `RawApiClient` instances) in `web/playwright/fixtures.ts`, using `playwright.request` (no browser required)

**Helpers:**
- `RawApiClient` at `web/playwright/utils/api/raw-client.ts` — returns raw `APIResponse` for status code assertions
- `ApiClient` at `web/playwright/utils/api/client.ts` — existing high-level client (81 methods, throws on error), used for setup/teardown
- Auth helpers at `web/playwright/utils/api/auth.ts`
- CSRF token handling at `web/playwright/utils/api/csrf.ts`
- Container/image ops at `web/playwright/utils/container.ts` — `pushImage`, `pushMultiArchImage` (skopeo), `orasAttach` (oras)
- Test utils at `web/playwright/utils/test-utils.ts` — `uniqueName(prefix)`

**Running tests:**
```bash
npm run test:e2e          # All tests (UI + API together)
npm run test:api          # Only @api tests (no browser, no frontend build)
npm run test:e2e:no-api   # Only UI tests
```

**Test patterns:**
- Tag all API test describe blocks with `{tag: ['@api', '@auth:Database']}`
- Import `test`, `expect`, `uniqueName` from `../../fixtures`
- Tests are parallel and self-contained (create + cleanup per test via try/finally)
- Use `adminClient`/`userClient` for assertions, existing `ApiClient` for setup when needed

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

**`web/playwright/utils/container.ts`** — Container and image operation helpers
- `pushImage(namespace, repo, tag, username, password)` — push via podman/docker
- `pushMultiArchImage(namespace, repo, tag, username, password)` — push manifest list via skopeo `--all`
- `orasAttach(namespace, repo, tag, username, password, artifactType, annotation, filePath)` — attach OCI artifact via oras
- `isContainerRuntimeAvailable()`, `isOrasAvailable()` — tool availability checks

Source translated: `quay-api-tests/cypress/support/commands.js` lines 200-311

**`web/playwright/utils/api/csrf.ts`** — CSRF token fetch (used by `RawApiClient`, `ApiClient`, and auth helpers)

**`web/playwright/utils/test-utils.ts`** — `uniqueName(prefix)` utility for generating unique test resource names

### 1.2 API fixtures (DONE)

**`web/playwright/fixtures.ts`** — API fixtures integrated into the main fixtures file:
- Test-scoped: `adminClient`, `userClient`, `anonClient` (all `RawApiClient` instances using `playwright.request`, no browser)
- Uses `TEST_USERS` from `global-setup.ts` for credentials
- `PLAYWRIGHT_SKIP_WEBSERVER=1` set by `test:api` script to skip frontend build

### 1.3 Smoke tests (DONE)

**`web/playwright/e2e/api/smoke.spec.ts`** — 4 parallel tests validating the infrastructure:
- Admin org CRUD (create, read, delete)
- Repository creation in an organization
- Permission boundary (user gets 403 on superuser endpoints)
- Auth boundary (unauthenticated request rejected)

### 1.4 Port `quay_api_testing_all.cy.js` (NEXT)

**`web/playwright/e2e/api/api-v1-superuser.spec.ts`**

Translation pattern:
```typescript
// Cypress:
cy.request({ method: "POST", url: `${endpoint}/api/v1/organization/`,
  headers: { authorization }, body: { name: org_name, email: "test@test.com" } })
  .then(response => { expect(response.status).to.eq(200); });

// Playwright:
const response = await adminClient.post('/api/v1/organization/', {
  name: org_name, email: "test@test.com"
});
expect(response.status()).toBe(200);
```

Each test should be self-contained with try/finally cleanup. Tag with `{tag: ['@api', '@auth:Database']}`.

**What to skip/change:**
- Remove the `create Quay Oauth Token` UI test (dead code, line 406 DOM assertion)
- Remove hardcoded Red Hat registry credentials — skip mirror sync tests, or parameterize via env
- Replace `cy.wait(300000)` with `expect.poll()` (5s intervals, 300s timeout)
- Mark vulnerability tests with `test.skip` + `// Requires Clair` comment
- Replace `cy.push_image()` calls with `pushImage()` / `pushMultiArchImage()` from `container.ts`

### 1.5 CI integration (automatic — no workflow changes needed)

API tests run automatically in the existing `web-playwright-ci.yaml` workflow. That workflow runs:
```bash
npx playwright test --grep-invert @auth:OIDC   # Database auth tests (includes @api)
npx playwright test --grep @auth:OIDC           # OIDC auth tests (excludes @api)
```

Since API tests are tagged `@auth:Database` (not `@auth:OIDC`), they're picked up by the first run. The workflow already:
- Triggers on changes to `web/**`
- Installs `skopeo` for image push tests
- Sets up Quay with Clair and Keycloak
- Uploads Playwright HTML/JSON reports

No new workflow, no new job, no trigger path changes.

---

## Phase 2: Port remaining test files (5-7 days)

### 2.1 Superuser-exclusive tests

**`web/playwright/e2e/api/api-v1-superuser-exclusive.spec.ts`**

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

**`web/playwright/e2e/api/api-v1-normal-user.spec.ts`**

Source: `quay_api_testing_normal_user.cy.js`

Auth setup:
1. Initialize superuser via API
2. Create normal user via `POST /api/v1/superuser/users/`
3. Generate OAuth token for normal user

Tests verify: same CRUD operations as superuser but from a non-privileged user. Key value is testing that superuser-only endpoints return 403.

### 2.3 Readonly superuser restrictions

**`web/playwright/e2e/api/api-v1-readonly-superuser.spec.ts`**

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

**`web/playwright/e2e/api/api-v1-immutability.spec.ts`**

Source: 21 unique tests from `quay_api_testing_all_new_ui.cy.js` (the rest is a duplicate of `_all`).

`setup-quay` extra-config: `FEATURE_IMMUTABLE_TAGS: true`

### 2.5 V2 Registry API

**`web/playwright/e2e/api/api-v2.spec.ts`**

Source: `quay_api_v2_testing.cy.js` — only tests not already inline in `_all`.

Auth: V2 Bearer token via `GET /v2/auth?service=...&scope=...` with Basic auth (use `getV2Token` from `auth.ts`).

### 2.6 CI considerations for special configurations

Most API tests run automatically in `web-playwright-ci.yaml` (see 1.5). However, some suites require specific Quay config that differs from the default CI setup:

- **Readonly superuser (2.3)**: Needs `GLOBAL_READONLY_SUPER_USERS` configured. Use `@feature:GLOBAL_READONLY_SUPER_USERS` tag to auto-skip if not configured, or add the config to the existing `setup-quay` step.
- **Immutability (2.4)**: Needs `FEATURE_IMMUTABLE_TAGS: true`. The existing CI already enables this (the `FEATURE_IMMUTABLE_TAGS` flag is set). Use `@feature:IMMUTABLE_TAGS` tag for auto-skip if not.

If certain suites can't run with the default CI config, they should be tagged to auto-skip rather than creating separate workflow jobs. The `@feature:X` auto-skip mechanism already handles this.

---

## Phase 3: Cleanup + Clair (future, 5-10 days)

- Remove Docker-image-based job from `qe-tests.yaml` once Playwright tests are stable (2+ weeks)
- Clair/vulnerability API tests already run in `web-playwright-ci.yaml` (Clair is enabled in the existing CI setup)
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
| `quay/quay:.github/workflows/web-playwright-ci.yaml` | Existing Playwright CI workflow (API tests run here automatically) |
| `quay/quay:.github/workflows/qe-tests.yaml` | Docker-image-based Cypress job (to be removed in Phase 3) |
| `quay/quay:.github/actions/setup-quay/action.yaml` | Composite action (may need config inputs for readonly superuser) |

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
| 1 | API Test Infrastructure (config, fixtures, helpers) | ~400-500 | 4 smoke | — | **PR #5715 open** |
| 2 | Organization & User API Tests | ~400-500 | 20-25 | PR 1 | |
| 3 | Repository API Tests | ~400-500 | 20-25 | PR 1 | |
| 4 | Repository Features (perms, notifs, tags, builds) | ~500-600 | 25-30 | PR 1 | |
| 5 | Advanced Features (quotas, proxy cache, mirror, messages) | ~450-550 | 20-25 | PR 1 | |
| 6 | Superuser-Exclusive Endpoints | ~500-600 | 40-50 | PR 1 | |
| 7 | Permission Boundary Tests (normal user 403s) | ~400-500 | 40-50 | PR 1 | |
| 8 | Readonly Superuser Role Tests (3-role auth) | ~400-500 | 30-40 | PR 1 | |
| 9 | Immutability API Tests (unique from new_ui) | ~350-450 | ~21 | PR 1 | |
| 10 | V2 Registry API Tests (+ V2 client helper) | ~600 | 30-40 | PR 1 | |

**Dependency graph:** PRs 2-10 can be developed in parallel after PR 1 merges.

**CI:** No separate workflow PR needed. API tests run automatically in the existing `web-playwright-ci.yaml` workflow alongside UI tests. The only CI work is removing the Docker-image-based `qe-tests.yaml` job once ported tests are stable (Phase 3).

**Source location:** All source Cypress tests are in the `quay-tests` repo at `quay-api-tests/cypress/`. No container extraction needed — reference the files directly:
- Test files: `quay-api-tests/cypress/e2e/quay_api_testing_*.cy.js`
- Custom commands/helpers: `quay-api-tests/cypress/support/commands.js`
- Config: `quay-api-tests/cypress.config.js`
