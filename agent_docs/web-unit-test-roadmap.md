# Web UI Unit Test Coverage Roadmap

Prioritized checklist of testable areas in `web/src/`, with effort estimates and implementation guidance.

**Stack:** Vitest + React Testing Library + happy-dom
**Current state:** 111 tests passing across 6 files. Phase 1 complete. Playwright covers E2E (58 tests).
**Target:** ~460 unit tests across 7 phases

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

## Phase 2: Error Handling + Cookie Utils (~25 tests)

| File | Functions | Est. Tests | Notes |
|------|-----------|-----------|-------|
| `src/resources/ErrorHandling.ts` | 8 exported + 2 classes | ~15 | `BulkOperationError`, `getErrorMessage` (priority chain from AxiosError), `addDisplayError`. Used by every resource — high ROI. |
| `src/libs/cookieUtils.ts` | 3 exported | ~5 | `getCookie`/`setCookie`/`deleteCookie`. happy-dom provides `document.cookie`. |
| `src/libs/quotaUtils.tsx` | 1 exported (JSX) | ~3 | `renderQuotaConsumed()` — first JSX unit test after `LoadingPage` seed test |

**Effort:** ~1 day. ErrorHandling needs `AxiosError` mock construction.

---

## Phase 3: Contexts (~35 tests)

Small surface area, high value — these are used everywhere.

| File | What to Test | Est. Tests |
|------|-------------|-----------|
| `src/contexts/UIContext.tsx` | Sidebar toggle + localStorage persistence, alert add/remove/clear, `useUI()` outside provider throws | ~15 |
| `src/contexts/ThemeContext.tsx` | Dark/light/auto theme switching, localStorage persistence, `matchMedia` listener, DOM class updates | ~20 |

**Effort:** ~1 day. Uses `renderHook` with provider wrapper.

---

## Phase 4: Complex Hooks (~60 tests)

These hooks have significant logic beyond "call API, return data." Highest ROI in the hooks layer.

| File | Complexity | Est. Tests | Why |
|------|-----------|-----------|-----|
| `src/hooks/usePaginatedSortableTable.ts` | High (168 LOC) | ~30 | Pagination + sorting + filtering pipeline. Tests hex/UUID sort, locale-aware string sort, page boundary math. Pure state — no mocking needed. |
| `src/hooks/UseUsernameValidation.ts` | High (60 LOC) | ~15 | State machine: editing -> confirming -> confirmed/existing/error. Dual async API check. Mock axios. |
| `src/hooks/UseQuotaManagement.ts` | Medium (242 LOC) | ~15 | 6 hooks for quota CRUD. Standard React Query pattern but worth testing error callbacks. |

**Effort:** ~2-3 days. `usePaginatedSortableTable` is the single highest-ROI test target in the codebase.

---

## Phase 5: API Resource Layer (~80 tests)

29 resource files. Most follow the same pattern: thin axios wrapper with optional data transformation. Create a shared mock factory and template tests.

**High priority (test first):**

| File | Est. Tests | Notes |
|------|-----------|-------|
| `src/resources/RepositoryResource.ts` | ~15 | Pagination logic in `fetchAllRepos`, state classification in `isNonNormalState` |
| `src/resources/TagResource.ts` | ~15 | Many operations, complex types |
| `src/resources/OrganizationResource.ts` | ~15 | `OrgDeleteError` class, bulk operations |
| `src/resources/UserResource.ts` | ~10 | Auth-related transforms |

**Medium priority (batch with template):**
Remaining ~25 resources: `DefaultPermissionResource`, `MembersResource`, `NotificationResource`, `TeamResources`, `BuildResource`, `MirroringResource`, etc. Most need just 1-2 tests per endpoint.

**Effort:** ~3-4 days. Create `createMockAxios()` utility once, reuse everywhere.

---

## Phase 6: Standard Query/Mutation Hooks (~100 tests)

60+ hooks follow the same React Query pattern. After Phase 4 establishes the testing pattern, these can be templated.

**Pattern:**
```text
hook calls useQuery/useMutation -> mock the resource function -> verify data shape + error handling
```

**Group by feature area:**
- Tags: `UseTags.ts` (7 hooks) — ~20 tests
- Organizations: `UseOrganizationActions.ts`, `UseOrganizationSettings.ts` — ~15 tests
- Builds: `UseBuildLogs.ts`, `UseBuilds.ts`, `UseBuildTriggers.ts` — ~15 tests
- Permissions: `UseRepositoryPermissions.ts`, `UseSuperuserPermissions.ts` — ~10 tests
- Remaining ~40 hooks: ~40 tests (1 per hook minimum)

**Effort:** ~3-4 days. Highly parallelizable once pattern is established.

---

## Phase 7: Components with Logic (~80 tests)

Focus on components with branching/validation logic. Skip pure layout components.

**Seed test completed:**

| Component | Tests | Status |
|-----------|-------|--------|
| `src/components/LoadingPage.tsx` | 6 | **Done** — Default render, custom title/message, JSX title, primary/secondary actions. Validates PatternFly + happy-dom + RTL chain. |

**High priority:**

| Component | Est. Tests | What to Test |
|-----------|-----------|-------------|
| `src/components/AutoPrunePolicyForm.tsx` | ~15 | Method selection (NONE/TAG_NUMBER/TAG_CREATION_DATE), duration parsing, form state sync |
| `src/components/ImmutabilityPolicyForm.tsx` | ~10 | Pattern validation regex, edit/view toggle, error states |
| `src/components/EntitySearch.tsx` | ~15 | Search input, dropdown filtering, entity selection, team/robot distinction |
| `src/components/ActivityHeatmap.tsx` | ~10 | Calendar generation (90-day window), week alignment, color scaling |
| `src/components/errors/ErrorBoundary.tsx` | ~5 | Error capture + fallback render |

**Medium priority:**
- `FormTextInput.tsx`, `FormCheckbox.tsx`, `FormDateTimePicker.tsx` — ~10 tests each
- Error display components (`RequestError`, `PageLoadError`, etc.) — ~15 tests total

**Skip (pure presentation, covered by Playwright):**
- Breadcrumb, Footer, Header, Labels, Sidebar, Table cells, Modals

**Effort:** ~3-4 days.

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
| 2 | Error handling + cookies | ~25 | 1 day | Pending |
| 3 | Contexts | ~35 | 1 day | Pending |
| 4 | Complex hooks | ~60 | 2-3 days | Pending |
| 5 | API resources | ~80 | 3-4 days | Pending |
| 6 | Standard hooks | ~100 | 3-4 days | Pending |
| 7 | Components | 6/~80 | 3-4 days | **In progress** — LoadingPage (6) done |

**Current: 111 tests passing across 6 files | Target: ~460 tests**

Phases 1-3 deliver the most value per test written. Phase 4's `usePaginatedSortableTable` is the single highest-ROI target. Phases 5-7 are incremental and can be spread over sprints.

---

## Shared Test Infrastructure to Build Along the Way

1. [x] **`createTestQueryClient()`** — Fresh QueryClient per render, in `src/test-utils.tsx`
2. [x] **`customRender()`** — Wraps in RecoilRoot + UIProvider + QueryClientProvider, in `src/test-utils.tsx`
3. [ ] **`createMockAxios()`** — Factory for axios-mock-adapter setup (Phase 2)
4. [ ] **Mock data factories** — e.g., `createMockOrg()`, `createMockRepo()`, `createMockTag()` (Phase 5)
5. [ ] **`renderWithRoute()`** — MemoryRouter wrapper for components using `useNavigate`/`useParams` (Phase 7, if needed)

---

## Coverage Strategy

Coverage is collected via V8 (`@vitest/coverage-v8`). No enforcement thresholds initially.

**Ratchet-up plan:**
1. After Phase 3 (~140 tests): measure baseline, set thresholds 5% below current
2. Increase thresholds by 5% each quarter
3. Target: 80% on `src/libs/`, 60% on `src/hooks/`, 40% overall
