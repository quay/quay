# Web UI Unit Test Coverage Roadmap

Prioritized checklist of testable areas in `web/src/`, with effort estimates and implementation guidance.

**Stack:** Vitest + React Testing Library + happy-dom
**Current state:** 530 tests passing across 41 files. Phases 1-5 complete. Playwright covers E2E (58 tests).
**Target:** ~620 unit tests across 7 phases

## Completed: Framework Setup

- [x] `vitest.config.ts` — happy-dom, asset stubbing, `src` alias, V8 coverage
- [x] `vitest.setup.ts` — jest-dom matchers, localStorage cleanup, matchMedia mock
- [x] `src/test-utils.tsx` — Custom render with QueryClient/RecoilRoot/UIProvider
- [x] `tsconfig.json` — Added `vitest/globals` to types
- [x] `package.json` — 7 devDependencies + 3 scripts (`test`, `test:watch`, `test:coverage`)
- [x] `.github/workflows/web-unit-tests.yaml` — CI workflow
- [x] `web/AGENTS.md` — Updated testing docs

---

## Phase 1: Pure Utility Functions — COMPLETE (105 tests)

| File | Tests | Status |
|------|-------|--------|
| `src/libs/utils.ts` | 75 | **Done** — all 21 exported functions covered |
| `src/libs/cosign.ts` | 9 | **Done** — `isCosignSignatureTag`, `enrichTagsWithCosignData` |
| `src/libs/dateTimeUtils.ts` | 17 | **Done** — all 8 exported functions covered |
| `src/libs/dockerfileParser.ts` | 8 | **Done** — `getRegistryBaseImage` with domain/tag/port edge cases |
| `src/libs/avatarUtils.ts` | 4 | **Done** — deterministic hashing, shape, color format |

---

## Phase 2: Error Handling + Cookie Utils — COMPLETE (31 tests)

| File | Tests | Status |
|------|-------|--------|
| `src/resources/ErrorHandling.ts` | 20 | **Done** — `BulkOperationError`, `ResourceError`, `throwIfError`, `addDisplayError`, `getErrorMessage` (priority chain, 5xx security, network errors, fallback), `assertHttpCode`, `isErrorString`, `getErrorMessageFromUnknown`. 100% statement/branch/function coverage. |
| `src/libs/cookieUtils.ts` | 6 | **Done** — `getCookie`, `setCookie`, `setPermanentCookie`, `deleteCookie`. 100% statement/function coverage. |
| `src/libs/quotaUtils.tsx` | 5 | **Done** — `renderQuotaConsumed` with null input, percentage/total display, zero bytes edge case, backfill status, null quota_bytes. 95% statement, 100% function coverage. |

**Notes:** Real `AxiosError` instances used (not mocks) to satisfy `instanceof` checks. Cookie tests use happy-dom's `document.cookie` with `beforeEach` cleanup. `quotaUtils` tests use `customRender` from `test-utils.tsx` for PatternFly Tooltip support.

---

## Phase 3: Contexts — COMPLETE (38 tests)

| File | Tests | Status |
|------|-------|--------|
| `src/contexts/UIContext.tsx` | 15 | **Done** — sidebar toggle + localStorage persistence, alert add/remove/clear with key generation, `useUI()` outside provider throws |
| `src/contexts/ThemeContext.tsx` | 23 | **Done** — LIGHT/DARK/AUTO switching, localStorage persistence + invalid fallback, `matchMedia` listener lifecycle (register/respond/cleanup/unmount), DOM class toggle (`pf-v6-theme-dark`), default context without provider |

**Notes:** First use of `renderHook` in the codebase. ThemeContext tests use a `createMockMediaQueryList` helper returning a stable object with `_triggerChange` for simulating system theme changes. Per-test `vi.spyOn(window, 'matchMedia')` overrides the global mock; `restoreMocks: true` handles cleanup. DOM class cleanup in `afterEach` since `vitest.setup.ts` only clears localStorage.

---

## Phase 4: Complex Hooks — COMPLETE (59 tests)

| File | Tests | Status |
|------|-------|--------|
| `src/hooks/usePaginatedSortableTable.ts` | 31 | **Done** — default state, initial config, string/hex/UUID/number sorting, sort interactions, filtering, pipeline, pagination, paginationProps |
| `src/hooks/UseUsernameValidation.ts` | 12 | **Done** — state machine transitions (editing/confirming/confirmed/existing), dual API check, sequential validations. axios mocked via `vi.mock`. |
| `src/hooks/UseQuotaManagement.ts` | 16 | **Done** — useFetchOrganizationQuota (null data, first quota, enabled logic), all 6 mutation hooks (success callbacks, error callbacks with addDisplayError). Resource functions mocked via `vi.mock`. |

**Notes:** `usePaginatedSortableTable` tests are pure state (no mocking). `UseUsernameValidation` and `UseQuotaManagement` use `QueryClientProvider` wrapper with `createTestQueryClient()` from `test-utils.tsx`. `waitFor` used for all async state transitions. The `onError` path in `UseUsernameValidation` is defensive/unreachable (internal try/catch absorbs all errors).

---

## Phase 5: API Resource Layer — COMPLETE (291 tests)

27 resource files tested. All use `vi.mock('src/libs/axios')` module-level mocking with a shared `mockResponse()` helper per file.

**High priority (4 files, 120 tests):**

| File | Tests | Status |
|------|-------|--------|
| `src/resources/RepositoryResource.ts` | 38 | **Done** — `isNonNormalState`, pagination recursion, batching, superuser truncation, CRUD, bulk operations with `BulkOperationError`, permission type mapping, transitive permissions with 404 handling |
| `src/resources/TagResource.ts` | 34 | **Done** — `getTags` with URL params, label CRUD, bulk delete with force mode, manifest retrieval, tag operations, pull statistics error paths |
| `src/resources/OrganizationResource.ts` | 20 | **Done** — org CRUD, `OrgDeleteError`, superuser paths, bulk delete with `Promise.allSettled`, `updateOrgSettings` null key stripping |
| `src/resources/UserResource.ts` | 28 | **Done** — `getEntityKind` enumeration, entity search with robot prefix stripping/filtering, user CRUD, `UserDeleteError`/`ApplicationTokenError` detail extraction, app token CRUD |

**Medium priority (9 files, 114 tests):**

| File | Tests | Status |
|------|-------|--------|
| `src/resources/QuotaResource.ts` | 21 | **Done** — viewMode-based URL routing (self/org/superuser), 404/403 fallback, `bytesToHumanReadable`/`humanReadableToBytes` conversions |
| `src/resources/AuthResource.ts` | 10 | **Done** — `GlobalAuthState` management, login/logout, CSRF token |
| `src/resources/RobotsResource.ts` | 14 | **Done** — Robot CRUD with org prefix stripping, federation config, bulk operations |
| `src/resources/BuildResource.ts` | 17 | **Done** — Build CRUD, trigger management, `startBuild` ref type routing, `fetchBuildLogs` with archived redirect, parallel superuser log fetch |
| `src/resources/MirroringResource.ts` | 11 | **Done** — Mirror config CRUD, `timestampToISO`/`timestampFromISO`, status labels |
| `src/resources/DefaultPermissionResource.ts` | 10 | **Done** — Permission CRUD, `addRepoPermissionToTeam` with console.error (no throw), bulk delete |
| `src/resources/MembersResource.ts` | 9 | **Done** — Member/collaborator CRUD, parallel fetch |
| `src/resources/NotificationResource.ts` | 12 | **Done** — Notification CRUD with eventConfig transform, `isNotificationDisabled` (>=3 failures) |
| `src/resources/TeamResources.ts` | 10 | **Done** — Team CRUD, `updateTeamRepoPerm` with role='none' delete path |

**Low priority (14 files, 57 tests):**

| File | Tests | Status |
|------|-------|--------|
| `src/resources/BillingResource.ts` | 8 | **Done** |
| `src/resources/OrgMirrorResource.ts` | 10 | **Done** |
| `src/resources/ImmutabilityPolicyResource.ts` | 6 | **Done** |
| `src/resources/OAuthApplicationResource.ts` | 5 | **Done** |
| `src/resources/TeamSyncResource.ts` | 5 | **Done** |
| `src/resources/ServiceKeysResource.ts` | 4 | **Done** |
| `src/resources/NamespaceAutoPruneResource.ts` | 4 | **Done** |
| `src/resources/RepositoryAutoPruneResource.ts` | 3 | **Done** |
| `src/resources/ProxyCacheResource.ts` | 2 | **Done** |
| `src/resources/RegistrySizeResource.ts` | 2 | **Done** |
| `src/resources/GlobalMessagesResource.ts` | 4 | **Done** |
| `src/resources/CapabilitiesResource.ts` | 1 | **Done** |
| `src/resources/ChangeLogResource.ts` | 1 | **Done** |
| `src/resources/QuayConfig.ts` | 1 | **Done** |

**Notes:** `LabelsResource.ts` and `ExternalLoginResource.ts` do not exist in the resources directory. No shared `createMockAxios()` utility was needed — the per-file `vi.mock` + `mockResponse()` pattern is simple and self-contained.

---

## Phase 6: Standard Query/Mutation Hooks (~140 tests)

79 untested hooks (~170 exported functions). 58 are React Query hooks, 21 are custom state/effect hooks. After Phase 4 establishes the testing pattern, these can be templated.

**Pattern:**
```text
hook calls useQuery/useMutation -> mock the resource function -> verify data shape + error handling
```

**High priority (complex logic beyond standard React Query):**

| File | Functions | Est. Tests | Notes |
|------|-----------|-----------|-------|
| `UseTags.ts` | 8 | ~20 | 404 vs error handling in `useTagPullStatistics`, multiple query/mutation hooks |
| `UseRepositoryPermissions.ts` | 6 | ~12 | Transitive permission chains, conditional fallback logic |
| `UseOrganizationActions.ts` | 3 | ~8 | Mutation chains with callbacks |
| `UseBuildLogs.ts` | 2 | ~6 | Streaming/incremental fetch pattern |
| `UseConvertAccount.ts` | — | ~5 | Multi-step state machine |
| `UsePasswordRecovery.ts` | — | ~5 | Multi-step validation chain |

**Medium priority (standard React Query, group by feature area):**
- Builds: `UseBuilds.ts`, `UseBuildTriggers.ts` — ~10 tests
- Permissions: `UseSuperuserPermissions.ts` — ~6 tests
- Organizations: `UseOrganizationSettings.ts` — ~6 tests
- Members/Teams: `UseMembers.ts`, `UseTeams.ts` — ~8 tests
- Notifications: `UseNotifications.ts`, `UseAppNotifications.ts` — ~6 tests
- Robot accounts: `useRobotAccounts.ts`, `useRobotFederation.ts` — ~6 tests
- Auth/Login: `UseExternalLoginAuth.ts`, `UseExternalLoginManagement.ts`, `UseExternalLogins.ts` — ~8 tests
- Config/State: `UseQuayConfig.ts`, `UseQuayState.ts` — ~4 tests
- Remaining: `UseApplicationTokens`, `UseAuthorizedApplications`, `UseLabels`, `UseEntities`, `UseSecurityDetails`, `UseProxyCache`, `UseMirroringConfig`, `UseAxios`, etc. — ~30 tests (1-2 per hook)

**Effort:** ~4-5 days. Highly parallelizable once pattern is established. Template one hook per complexity tier (simple=1 test, moderate=2, complex=3-5) then batch.

---

## Phase 7: Components with Logic (~140 tests)

101 component files total. Focus on components with branching/validation logic (70+ testable). Skip pure layout/presentation components (~30).

**Seed test completed:**

| Component | Tests | Status |
|-----------|-------|--------|
| `src/components/LoadingPage.tsx` | 6 | **Done** — Default render, custom title/message, JSX title, primary/secondary actions. Validates PatternFly + happy-dom + RTL chain. |

**Critical priority (>250 lines, 5+ hooks, security/core features):**

| Component | Lines | Est. Tests | What to Test |
|-----------|-------|-----------|-------------|
| `src/components/modals/RobotTokensModal.tsx` | 505 | ~8 | Token display/generation/revocation, copy-to-clipboard, lifecycle |
| `src/components/modals/robotAccountWizard/*` (5 files) | 238-370 | ~20 | Multi-step wizard: permission selection, team view, review+submit |
| `src/components/header/HeaderToolbar.tsx` | 369 | ~8 | Navigation state, user menu, search interactions |
| `src/components/modals/ChangeAccountTypeModal.tsx` | 368 | ~6 | Account conversion with validation |
| `src/components/modals/CreateRepoModalTemplate.tsx` | 351 | ~8 | Repository creation form validation and submission |
| `src/components/modals/CredentialsModal.tsx` | 320 | ~6 | Token display + copy functionality |
| `src/components/modals/CreateRobotAccountModal.tsx` | 290 | ~6 | Robot account creation with permissions |
| `src/components/modals/ChangePasswordModal.tsx` | 210 | ~5 | Password validation + change form |

**High priority (significant logic):**

| Component | Est. Tests | What to Test |
|-----------|-----------|-------------|
| `src/components/AutoPrunePolicyForm.tsx` | ~15 | Method selection (NONE/TAG_NUMBER/TAG_CREATION_DATE), duration parsing, form state sync |
| `src/components/ImmutabilityPolicyForm.tsx` | ~10 | Pattern validation regex, edit/view toggle, error states |
| `src/components/EntitySearch.tsx` | ~15 | Search input, dropdown filtering, entity selection, team/robot distinction |
| `src/components/ActivityHeatmap.tsx` | ~10 | Calendar generation (90-day window), week alignment, color scaling |
| `src/components/TypeAheadSelect.tsx` | ~6 | Search dropdown filtering + selection |
| `src/components/LabelsEditable.tsx` | ~8 | Label CRUD with inline edit mode |
| `src/components/errors/ErrorBoundary.tsx` | ~5 | Error capture + fallback render |

**Medium priority:**
- `FormTextInput.tsx`, `FormCheckbox.tsx`, `FormDateTimePicker.tsx` — ~10 tests each
- Error display components (`RequestError`, `PageLoadError`, `SiteUnavailableError`, `ErrorModal`, `FormError`, `404`) — ~15 tests total

**Skip (pure presentation, covered by Playwright):**
- Breadcrumb, Footer (base), Labels (read-only), Sidebar, Table cells (ImageSize, ManifestListSize, RepoCount, Menu), layout-only modals without form logic

**Effort:** ~5-6 days. Template one modal and one form component first, then batch.

---

## What NOT to Unit Test

Leave these to Playwright E2E:

| Category | Why |
|----------|-----|
| Route/page components (`src/routes/`) | Composition of tested parts; E2E validates the assembly |
| Auth flows (login, OIDC, OAuth) | Require real browser + server interaction |
| CSS/styling | Visual regression is a Playwright concern |
| Navigation/routing | Router integration tests need full app context |
| Recoil atoms (`src/atoms/`) | Trivial state definitions, no logic |

---

## Summary

| Phase | Scope | Tests | Effort | Status |
|-------|-------|-------|--------|--------|
| 1 | Pure utilities | 105 | 1-2 days | **Complete** |
| 2 | Error handling + cookies | 31 | 1 day | **Complete** |
| 3 | Contexts | 38 | 1 day | **Complete** |
| 4 | Complex hooks | 59 | 2-3 days | **Complete** |
| 5 | API resources (27 files) | 291 | 4-5 days | **Complete** |
| 6 | Standard hooks (79 files) | ~140 | 4-5 days | Pending |
| 7 | Components (100 files) | ~140 | 5-6 days | **In progress** — LoadingPage (6) done |

**Current: 530 tests passing across 41 files | Target: ~620 tests**

Phases 1-5 are complete. Phases 6-7 are incremental and can be spread over sprints. Remaining effort: ~9-11 days.

---

## Shared Test Infrastructure to Build Along the Way

1. [x] **`createTestQueryClient()`** — Fresh QueryClient per render, in `src/test-utils.tsx`
2. [x] **`customRender()`** — Wraps in RecoilRoot + UIProvider + QueryClientProvider, in `src/test-utils.tsx`
3. [x] **Axios mocking pattern** — `vi.mock('src/libs/axios')` + per-file `mockResponse()` helper (Phase 5). No shared factory needed — pattern is simple and self-contained.
4. [ ] **Mock data factories** — e.g., `createMockOrg()`, `createMockRepo()`, `createMockTag()` (Phase 6-7, if needed)
5. [ ] **`renderWithRoute()`** — MemoryRouter wrapper for components using `useNavigate`/`useParams` (Phase 7, if needed)

---

## Coverage Strategy

Coverage is collected via V8 (`@vitest/coverage-v8`). No enforcement thresholds initially.

**Baseline after Phase 5 (530 tests):** `src/libs/` 84%, `src/contexts/` 100%, `src/hooks/` 4%, `src/resources/` ~55-60%, `src/components/` <1%, overall ~8%.

**Ratchet-up plan:**
1. After Phase 4 (done): baseline measured. `src/libs/` and `src/contexts/` already meet targets.
2. After Phase 5 (done): `src/resources/` ~55-60%
3. After Phase 6: `src/hooks/` should reach ~45-50%
4. After Phase 7: `src/components/` should reach ~40-45%, overall ~50-55%
5. Target: 80% on `src/libs/`, 60% on `src/hooks/`, 40% overall
