# Web UI Unit Test Coverage Roadmap

Prioritized checklist of testable areas in `web/src/`, with effort estimates and implementation guidance.

**Stack:** Vitest + React Testing Library + happy-dom
**Current state:** 893 tests passing across 124 files. Phases 1-7 complete. Playwright covers E2E (58 tests).
**Target:** ~870 unit tests across 7 phases

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
| `src/resources/OrganizationResource.ts` | 16 | **Done** — org CRUD, `OrgDeleteError`, superuser paths, bulk delete with `Promise.allSettled`, `updateOrgSettings` null key stripping |
| `src/resources/UserResource.ts` | 32 | **Done** — `getEntityKind` enumeration, entity search with robot prefix stripping/filtering, user CRUD, `UserDeleteError`/`ApplicationTokenError` detail extraction, app token CRUD |

**Medium priority (9 files, 117 tests):**

| File | Tests | Status |
|------|-------|--------|
| `src/resources/QuotaResource.ts` | 26 | **Done** — viewMode-based URL routing (self/org/superuser), 404/403 fallback, `bytesToHumanReadable`/`humanReadableToBytes` conversions |
| `src/resources/AuthResource.ts` | 10 | **Done** — `GlobalAuthState` management, login/logout, CSRF token |
| `src/resources/RobotsResource.ts` | 14 | **Done** — Robot CRUD with org prefix stripping, federation config, bulk operations |
| `src/resources/BuildResource.ts` | 16 | **Done** — Build CRUD, trigger management, `startBuild` ref type routing, `fetchBuildLogs` with archived redirect, parallel superuser log fetch |
| `src/resources/MirroringResource.ts` | 10 | **Done** — Mirror config CRUD, `timestampToISO`/`timestampFromISO`, status labels |
| `src/resources/DefaultPermissionResource.ts` | 9 | **Done** — Permission CRUD, `addRepoPermissionToTeam` with console.error (no throw), bulk delete |
| `src/resources/MembersResource.ts` | 7 | **Done** — Member/collaborator CRUD, parallel fetch |
| `src/resources/NotificationResource.ts` | 12 | **Done** — Notification CRUD with eventConfig transform, `isNotificationDisabled` (>=3 failures) |
| `src/resources/TeamResources.ts` | 13 | **Done** — Team CRUD, `updateTeamRepoPerm` with role='none' delete path |

**Low priority (14 files, 57 tests):**

| File | Tests | Status |
|------|-------|--------|
| `src/resources/BillingResource.ts` | 9 | **Done** |
| `src/resources/OrgMirrorResource.ts` | 9 | **Done** |
| `src/resources/ImmutabilityPolicyResource.ts` | 6 | **Done** |
| `src/resources/OAuthApplicationResource.ts` | 5 | **Done** |
| `src/resources/TeamSyncResource.ts` | 5 | **Done** |
| `src/resources/ServiceKeysResource.ts` | 4 | **Done** |
| `src/resources/NamespaceAutoPruneResource.ts` | 5 | **Done** |
| `src/resources/RepositoryAutoPruneResource.ts` | 3 | **Done** |
| `src/resources/ProxyCacheResource.ts` | 2 | **Done** |
| `src/resources/RegistrySizeResource.ts` | 2 | **Done** |
| `src/resources/GlobalMessagesResource.ts` | 4 | **Done** |
| `src/resources/CapabilitiesResource.ts` | 1 | **Done** |
| `src/resources/ChangeLogResource.ts` | 1 | **Done** |
| `src/resources/QuayConfig.ts` | 1 | **Done** |

**Notes:** `LabelsResource.ts` and `ExternalLoginResource.ts` do not exist in the resources directory. No shared `createMockAxios()` utility was needed — the per-file `vi.mock` + `mockResponse()` pattern is simple and self-contained.

---

## Phase 6: Standard Query/Mutation Hooks — COMPLETE (206 tests)

52 hook files tested. Mock strategy: `vi.mock('src/resources/ResourceModule', ...)` at module boundary; `QueryClientProvider` wrapper using `createTestQueryClient()`; `waitFor` for async state, `act` for mutations.

| File | Tests | Notes |
|------|-------|-------|
| `UseTags.test.ts` | 15 | 404 fallback in `useTagPullStatistics`, all 8 mutation hooks |
| `UseRepositoryPermissions.test.ts` | 4 | Member assembly, search filter |
| `UseOrganizationActions.test.ts` | 7 | Rename/delete/takeOwnership with navigate |
| `UseBuildLogs.test.ts` | 4 | Superuser fetch, disabled, error |
| `UseConvertAccount.test.ts` | 3 | Success + clientKey exposed |
| `UsePasswordRecovery.test.ts` | 5 | Axios mock, AxiosError/unknown, resetState |
| `UseBuilds.test.ts` | 9 | Filter, recent limit, start/cancel, log parsing |
| `UseBuildTriggers.test.ts` | 9 | All trigger CRUD hooks |
| `UseNotifications.test.ts` | 6 | Event/status filter, resetFilter |
| `UseOrganizationSettings.test.ts` | 2 | Update success/error |
| `UseSuperuserPermissions.test.ts` | 4 | Superuser/readonly/registry-readonly/regular |
| `UseQuayConfig.test.ts` | 3 | Fetch, undefined before load, withLoading |
| `UseQuayState.test.ts` | 4 | Readonly/normal/recovery/undefined config |
| `UseCurrentUser.test.ts` | 5 | Superuser detection, updateUser, changeEmail |
| `useRobotAccounts.test.ts` | 3 | Fetch, disabled, error |
| `useRobotFederation.test.ts` | 2 | Fetch + create mutation |
| `UseExternalLogins.test.ts` | 6 | OIDC, hasExternalLogins, readonly tab |
| `UseApplicationTokens.test.ts` | 7 | Pagination, search, create, revoke |
| `UseMembers.test.ts` | 6 | Add, fetch+filter, collaborators, delete |
| `UseDefaultPermissions.test.ts` | 4 | Transform prototypes, CRUD |
| `UseRepository.test.ts` | 4 | Fetch + disabled |
| `UseRepositoryState.test.ts` | 2 | Mutation success/error |
| `UseRepositoryVisibility.test.ts` | 2 | Mutation success/error |
| `UseDeleteRepositories.test.ts` | 2 | Mutation success/error |
| `UseGlobalMessages.test.ts` | 3 | Fetch, create, delete |
| `UseRegistrySize.test.ts` | 3 | Fetch, disabled, queue |
| `UseRegistryCapabilities.test.ts` | 4 | Architectures, sparse manifests |
| `UseSecurityDetails.test.ts` | 2 | Fetch + disabled |
| `UseManifestByDigest.test.ts` | 2 | Fetch + disabled |
| `UseTagLabels.test.ts` | 3 | Fetch via onSuccess state, create, delete |
| `UseEntities.test.ts` | 3 | Debounce with fake timers, error |
| `UseImageSize.test.ts` | 3 | Layer sum, null layers, error |
| `UseDeleteAccount.test.ts` | 3 | deleteUser, deleteOrg, error (mutateAsync) |
| `UseUserActions.test.ts` | 5 | email/password/status/delete/recovery |
| `UseCreateUser.test.ts` | 2 | Success + error |
| `UseCreateClientKey.test.ts` | 2 | Success + error |
| `UseCreateRepository.test.ts` | 2 | Success + error |
| `UseUpdateRepositoryPermissions.test.ts` | 2 | set + delete mutations |
| `UseUpdateNotifications.test.ts` | 3 | create, delete, enable |
| `UseTeamSync.test.ts` | 3 | sync+error format, removeSync |
| `UseAuthorizedEmails.test.ts` | 3 | Initial state, poll, send |
| `UseOrgMirrorExists.test.ts` | 2 | Returns true, disabled |
| `UseProxyCache.test.ts` | 4 | Fetch, disabled, create, delete |
| `UseChangeLog.test.ts` | 2 | Fetch + error |
| `UseNotificationMethods.test.ts` | 3 | MAILING on/off, title interpolation |
| `UseServiceKeys.test.ts` | 5 | Fetch, filter, delete, approve, create |
| `UseNamespaceAutoPrunePolicies.test.ts` | 4 | Fetch, create, update, delete |
| `UseRepositoryAutoPrunePolicies.test.ts` | 4 | Fetch, create, update, delete |
| `UseNamespaceImmutabilityPolicies.test.ts` | 4 | Fetch, create, update, delete |
| `UseRepositoryImmutabilityPolicies.test.ts` | 4 | Fetch, create, update, delete |
| `UseOAuthApplications.test.ts` | 4 | Fetch, filter, create, delete, update |
| `UseDeleteRobotAccount.test.ts` | 2 | Bulk delete + error |

**Skipped (Recoil atoms, form state, external deps):** UseOrganizations, UseRepositories, UseUpgradePlan, UseOrgMirroringConfig, UseMirroringForm, UseOAuthApplicationForm, UseCreateAccount, UseCreateServiceKey.

**Key patterns discovered:**
- React Query v4 disabled queries have `isLoading: true` (never fetched) — assert on call count, not loading state
- `onSuccess` state setters need `waitFor(() => stateProp)` directly, not `waitFor(loading=false)` + assert
- `mutateAsync` throws on error; tests must `.catch(vi.fn())` to avoid unhandled rejections
- Debounced hooks: use `vi.useFakeTimers()` + `await act(async () => { vi.advanceTimersByTime(N) })` (no `waitFor` after)

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
| 6 | Standard hooks (52 files) | 206 | 4-5 days | **Complete** — 206 new tests across 52 hook files |
| 7 | Components (100 files) | ~140 | 5-6 days | **Complete** — 157 tests across 31 files added |

**Current: 893 tests passing across 124 files | Target: ~870 tests**

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
