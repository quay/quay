# Web UI Unit Test Coverage Roadmap

Prioritized checklist of testable areas in `web/src/`, with effort estimates and implementation guidance.

**Stack:** Vitest + React Testing Library + happy-dom
**Current state:** 1117 tests passing across 160 files. Phases 1-8a, 8b complete. Playwright covers E2E (58 tests).
**Target:** ~1,100 unit tests across 8 phases (exceeded)

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

## Phase 7: Components with Logic — COMPLETE (163 tests)

101 component files total. 39 tested, 62 remaining. Focus on components with branching/validation logic (70+ testable). Skip pure layout/presentation components (~30).

**Completed (39 test files, 163 tests):**

| Component | Tests | Status |
|-----------|-------|--------|
| `src/components/LoadingPage.tsx` | 6 | **Done** — Default render, custom title/message, JSX title, primary/secondary actions |
| `src/components/ActivityHeatmap/` | tests | **Done** |
| `src/components/empty/` (2 files) | tests | **Done** |
| `src/components/errors/` (7 files) | tests | **Done** — 100% file coverage |
| `src/components/forms/` (2 files) | tests | **Done** |
| `src/components/labels/` (2 files) | tests | **Done** |
| `src/components/toolbar/` (11 files) | tests | **Done** — 85% file coverage |
| Other components | tests | **Done** — LinkOrPlainText, ManifestDigest, etc. |

**Remaining — see Phase 8.**

---

## Phase 8: Remaining Gaps (~170 tests)

Covers untested modals, hooks with testable logic, and remaining components from Phase 7 backlog.

### 8a: Modal Components — COMPLETE (87 tests)

18 test files covering modals, wizard sub-components, and header toolbar. All use `vi.mock` at module boundary for hooks; `customRender` from `test-utils.tsx` for QueryClient/RecoilRoot/UIProvider.

**Critical priority (>250 lines, security/core features):**

| Component | Tests | Status |
|-----------|-------|--------|
| `src/components/modals/RobotTokensModal.tsx` | 8 | **Done** — Tab switching, regenerate token, clipboard display. Uses `Module._resolveFilename` patch for dynamic `require()` SVG assets. |
| `src/components/modals/robotAccountWizard/*` (4 files tested) | 20 | **Done** — NameAndDescription (6), DefaultPermissions (3), ReviewAndFinish (6), DisplayModal (5). Validation states, toggle groups, save/close. |
| `src/components/header/HeaderToolbar.tsx` | 8 | **Done** — User menu, notification badge, theme toggle, sign-in button, logout |
| `src/components/modals/ChangeAccountTypeModal.tsx` | 6 | **Done** — Blocking message for org members, admin form validation, convert flow |
| `src/components/modals/CreateRepoModalTemplate.tsx` | 8 | **Done** — Namespace dropdown, repo name regex validation, visibility radio, submit |
| `src/components/modals/CredentialsModal.tsx` | 8 | **Done** — 6 tabs, token/encrypted-password types, newly created alert, clipboard |
| `src/components/modals/CreateRobotAccountModal.tsx` | 6 | **Done** — Wizard steps (5 for org, 3 for user), name validation, submit disabled state |
| `src/components/modals/ChangePasswordModal.tsx` | 7 | **Done** — Password validation, match check, submit, cancel (pre-existing) |

**Medium priority modals:**

| Component | Tests | Status |
|-----------|-------|--------|
| `BulkDeleteModalTemplate.tsx` | 4 | **Done** — Confirm input, search filter, bulk delete callback |
| `ConfirmationModal.tsx` | 3 | **Done** — Custom confirm handler, visibility change, cancel |
| `DeleteModalForRowTemplate.tsx` | 3 | **Done** — Item display, delete handler, cancel |
| `DeleteAccountModal.tsx` | 4 | **Done** — Verification text match, disabled state, confirm/cancel |
| `RobotFederationModal.tsx` | 3 | **Done** — Title, empty state, existing entries |
| `TokenDisplayModal.tsx` | 3 | **Done** — Scopes display, security warning |
| `RevokeTokenModal.tsx` | 3 | **Done** — Warning text, null token, revoke mutation |

**Notes:** SCSS compilation in vitest was failing due to sass version mismatch with Vite. Fixed by adding an `enforce: 'pre'` plugin to `vitest.config.ts` that stubs `.scss` files via `resolveId`/`load` hooks before the `vite:css` plugin processes them. PatternFly Modal renders its own close (X) button, requiring `getAllByRole` + filter for footer-specific close buttons. `ClipboardCopy` splits text across `<input>` + wrapper elements — use `data-testid` or `querySelector('input')` instead of `getByText`.

### 8b: Remaining Hooks (~50 tests, ~2-3 days)

12 hooks with testable logic not covered by the Phase 6 skip list:

| Hook | Est. Tests | What to Test |
|------|-----------|-------------|
| `UseTeams.ts` | ~6 | Team CRUD queries/mutations |
| `UseEvents.tsx` | ~5 | Event fetching + filtering |
| `UseUsageLogs.ts` | ~5 | Usage log queries |
| `UseMirroringConfig.ts` | ~5 | Mirror config queries |
| `UseOrganization.ts` | ~4 | Single org fetch |
| `UseAnalytics.ts` | ~3 | Analytics event dispatch |
| `UseAuthorizedApplications.ts` | ~4 | App listing + revocation |
| `UseGlobalFreshLogin.tsx` | ~3 | Fresh login modal trigger |
| `UseLogDescriptions.tsx` | ~3 | Log description mapping |
| `UseMarketplaceSubscriptions.ts` | ~3 | Subscription queries |
| `UseServiceStatus.ts` | ~3 | Service status polling |
| `useAppNotifications.ts` | ~3 | Notification state management |

**Skip (intentional — Recoil, form state, external deps, infrastructure):**
UseOrganizations, UseRepositories, UseUpgradePlan, UseOrgMirroringConfig, UseMirroringForm, UseOAuthApplicationForm, UseCreateAccount, UseCreateServiceKey, UseExternalLoginAuth, UseExternalLoginManagement, UseExternalScripts, UseAxios, UseLogo, UseRefreshPage, UseOrgMirroringForm.

### 8c: Remaining Components (~40 tests, ~2 days)

| Component | Est. Tests | What to Test |
|-----------|-----------|-------------|
| `EntitySearch.tsx` | ~15 | Search input, dropdown filtering, entity selection |
| `TypeAheadSelect.tsx` | ~6 | Search dropdown filtering + selection |
| `ImmutabilityPolicyForm.tsx` | ~10 | Pattern validation regex, edit/view toggle |
| `AutoPrunePolicyForm.tsx` | ~15 | Method selection, duration parsing, form state |

**Skip (pure presentation, covered by Playwright):**
Breadcrumb, Footer, Labels (read-only), Sidebar, Table cells (ImageSize, ManifestListSize, RepoCount, Menu), layout-only modals without form logic, header/MinimalHeader/QuayHeader.

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
| 5 | API resources (28 files) | 291 | 4-5 days | **Complete** |
| 6 | Standard hooks (55 files) | 240 | 4-5 days | **Complete** — 55 test files |
| 7 | Components (39 files) | 163 | 5-6 days | **Complete** — 39 test files |
| 8a | Modal components (18 files) | 87 | 4-5 days | **Complete** |
| 8b | Remaining hooks (12 files) | 53 | 2-3 days | **Complete** |
| 8c | Remaining components | ~40 | 2 days | **Planned** |

**Current: 1117 tests passing across 160 files | Target: ~1,100 tests (exceeded)**

Phases 1-8a, 8b complete. Phase 8c covers remaining component gaps. Remaining effort: ~2 days.

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

**Baseline after Phase 7 (927 tests, measured 2026-05-04):**
- `src/contexts/` **100%** lines
- `src/resources/` **87%** lines (28/29 files tested)
- `src/libs/` **83%** lines (7/8 files tested)
- `src/components/` **50%** lines (39/101 files tested)
- `src/hooks/` **37%** lines (55/82 files tested)
- `src/routes/` **0%** lines (intentionally untested — 235 files, E2E only)
- **Overall: 20.9% lines** (routes drag this down)

**Ratchet-up plan:**
1. After Phase 8b (hooks): `src/hooks/` should reach ~55%
2. After Phase 8a (modals): `src/components/` should reach ~60%
3. After Phase 8c (remaining components): `src/components/` should reach ~65%
4. Target: 90%+ `src/libs/`, 90%+ `src/resources/`, 55%+ `src/hooks/`, 60%+ `src/components/`
