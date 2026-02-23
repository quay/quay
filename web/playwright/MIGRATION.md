# Cypress to Playwright Migration Guide

This guide provides instructions for migrating Quay's Cypress e2e tests to Playwright.

## Key Principles

1. **NO MOCKS/INTERCEPTS** - Replace all `cy.intercept()` calls with real API interactions
2. **NO DATABASE SEEDING** - Use API utilities to create test data dynamically
3. **Maintain Coverage** - Port tests to preserve feature/bug coverage
4. **Use Playwright Tags** - Label tests with `{ tag: [...] }` for filtering
5. **Consolidate When Logical** - Merge sequential operations into e2e flows

## Directory Structure

```text
web/playwright/
├── e2e/                          # Test specifications
│   ├── auth/                     # Authentication tests
│   ├── repository/               # Repository tests
│   │   └── repository-delete.spec.ts
│   ├── superuser/                # Superuser tests
│   └── ui/                       # UI component tests
│       ├── breadcrumbs.spec.ts
│       └── theme-switcher.spec.ts
├── utils/                        # Shared utilities
│   ├── api/                      # API utilities by resource
│   │   ├── index.ts              # Re-exports all API utilities
│   │   ├── csrf.ts               # getCsrfToken
│   │   ├── organization.ts       # createOrganization, deleteOrganization
│   │   ├── repository.ts         # createRepository, deleteRepository
│   │   └── team.ts               # createTeam, deleteTeam
│   ├── config.ts                 # API_URL, BASE_URL
│   └── container.ts              # pushImage, isContainerRuntimeAvailable (multi-runtime: podman/docker)
├── fixtures.ts                   # Custom fixtures, uniqueName()
├── global-setup.ts               # Creates admin, testuser, readonly users
└── MIGRATION.md                  # This guide
```

## Test Tagging System

Use Playwright's built-in tag feature for test categorization.

### Syntax

```typescript
// Tag a describe block
test.describe('Feature Name', { tag: ['@critical', '@repository'] }, () => {
  // Tag individual tests
  test('does something', { tag: '@PROJQUAY-1234' }, async ({ page }) => {
    // ...
  });
});
```

### Tag Categories

| Category | Format | Example | Purpose |
|----------|--------|---------|---------|
| JIRA | `@PROJQUAY-####` | `@PROJQUAY-1234` | Link to JIRA ticket |
| Priority | `@critical`, `@smoke` | `@critical` | Test importance |
| Feature | `@repository` | `@repository` | Feature area |
| Config | `@config:BILLING` | `@config:OIDC` | Required config |
| Feature Flag | `@feature:PROXY_CACHE` | `@feature:REPO_MIRROR` | Required feature |
| Container | `@container` | `@container` | Requires container runtime (auto-skip) |

### Running Tagged Tests

```bash
# Run critical tests only
npx playwright test --grep @critical

# Run tests for a specific JIRA ticket
npx playwright test --grep @PROJQUAY-1234

# Run all repository tests
npx playwright test --grep @repository

# Exclude tests requiring specific config
npx playwright test --grep-invert @config:BILLING

# Combine filters (AND logic)
npx playwright test --grep "(?=.*@critical)(?=.*@repository)"
```

## Command Mapping

### Navigation & Interaction

| Cypress | Playwright |
|---------|------------|
| `cy.visit(url)` | `await page.goto(url)` |
| `cy.get(selector)` | `page.locator(selector)` |
| `cy.get('[data-testid="x"]')` | `page.getByTestId('x')` |
| `cy.contains(text)` | `page.getByText(text)` |
| `cy.get('button').contains('Save')` | `page.getByRole('button', { name: 'Save' })` |
| `.click()` | `await locator.click()` |
| `.type(text)` | `await locator.fill(text)` |
| `.clear().type(text)` | `await locator.fill(text)` |
| `.check()` | `await locator.check()` |
| `.select(value)` | `await locator.selectOption(value)` |

### Assertions

| Cypress | Playwright |
|---------|------------|
| `.should('exist')` | `await expect(locator).toBeVisible()` |
| `.should('not.exist')` | `await expect(locator).not.toBeVisible()` |
| `.should('be.visible')` | `await expect(locator).toBeVisible()` |
| `.should('be.disabled')` | `await expect(locator).toBeDisabled()` |
| `.should('be.enabled')` | `await expect(locator).toBeEnabled()` |
| `.should('have.text', x)` | `await expect(locator).toHaveText(x)` |
| `.should('have.value', x)` | `await expect(locator).toHaveValue(x)` |
| `.should('contain', x)` | `await expect(locator).toContainText(x)` |
| `cy.url().should('include', x)` | `await expect(page).toHaveURL(/.*x.*/)` |
| `cy.url().should('eq', x)` | `await expect(page).toHaveURL(x)` |

### Scoping

| Cypress | Playwright |
|---------|------------|
| `cy.get('#modal').within(() => { ... })` | `page.locator('#modal').locator(...)` |
| `cy.get('#modal').find('.btn')` | `page.locator('#modal').locator('.btn')` |

### Things to ELIMINATE

| Cypress | Playwright Replacement |
|---------|------------------------|
| `cy.intercept()` | Use real API calls |
| `cy.fixture()` | Use API utilities to create data |
| `cy.exec('npm run quay:seed')` | Use `utils/api.ts` functions |
| `cy.wait('@alias')` | `await page.waitForResponse()` or just let auto-wait work |

## Adding data-testid Attributes

When migrating tests, prefer `getByTestId()` over element IDs or framework-generated selectors (like PatternFly's `#pf-tab-N-tabname`).

### Why data-testid?

- **Stable**: Won't break when CSS classes or IDs change
- **Explicit**: Clearly marks elements as test targets
- **Framework-agnostic**: Works regardless of UI framework changes

### When to Add data-testid

If a Cypress test uses selectors like:
- `#some-element-id` (element ID)
- `.pf-v5-c-button` (framework class)
- `[aria-label="..."]` (accessibility attribute)

Add a `data-testid` to the source component and use `getByTestId()` in Playwright.

### IMPORTANT: Use data-testid, NOT test-id

⚠️ **Always use `data-testid`, not `test-id`**

Playwright's `getByTestId()` method only works with the standard `data-testid` attribute.
Using `test-id` (without the `data-` prefix) requires manual locator selectors and loses
the benefits of Playwright's built-in test ID support.

```tsx
// ❌ Wrong - requires manual locator
<Button test-id="my-button">Click</Button>
await page.locator('[test-id="my-button"]').click();

// ✅ Correct - works with getByTestId()
<Button data-testid="my-button">Click</Button>
await page.getByTestId('my-button').click();
```

### Naming Conventions

```text
{feature}-{component}-{action/purpose}
```

Examples:
- `org-settings-email` - Email input in org settings
- `org-settings-save-button` - Save button in org settings
- `billing-invoice-checkbox` - Invoice checkbox in billing
- `delete-repository-confirm-btn` - Confirm button in delete modal

### Adding to Components

```tsx
// Before: No data-testid
<Button id="save-billing-settings" onClick={handleSave}>
  Save
</Button>

// After: Add data-testid
<Button
  id="save-billing-settings"
  data-testid="billing-save-button"
  onClick={handleSave}
>
  Save
</Button>
```

For form components using shared wrappers (like `FormTextInput`):

```tsx
<FormTextInput
  name="email"
  fieldId="org-settings-email"
  data-testid="org-settings-email"  // Add this
  // ...
/>
```

### Using in Tests

```typescript
// Prefer this
await page.getByTestId('org-settings-save-button').click();

// Over this
await page.locator('#save-org-settings').click();

// Or this (framework-specific, may break)
await page.locator('#pf-tab-2-cliconfig').click();
```

## Authentication Pattern

### Using Fixtures (Recommended)

```typescript
import { test, expect } from '../fixtures';

// authenticatedPage is already logged in as regular user
test('can view repository list', async ({ authenticatedPage }) => {
  await authenticatedPage.goto('/repository');
  await expect(authenticatedPage.getByText('Repositories')).toBeVisible();
});

// superuserPage is logged in as superuser
test('superuser can manage users', async ({ superuserPage }) => {
  await superuserPage.goto('/superuser');
});
```

### Manual Login (When Needed)

```typescript
import { loginUser } from '../fixtures';

test('custom login scenario', async ({ page, request }) => {
  const csrfToken = await loginUser(request, 'customuser', 'password');
  await page.goto('/repository');
});
```

## Creating Test Data

### Using the `api` Fixture (Recommended)

The `api` fixture provides methods to create test resources with automatic cleanup:

```typescript
import {test, expect} from '../../fixtures';

test.describe('Repository Tests', () => {
  test('works with repository', async ({authenticatedPage, api}) => {
    // Create repo in user's namespace (auto-cleaned after test)
    const repo = await api.repository(undefined, 'testrepo');

    // Or create in an organization
    const org = await api.organization('myorg');
    const orgRepo = await api.repository(org.name, 'orgrepo');

    await authenticatedPage.goto(`/repository/${repo.fullName}`);
    // ... test code ...
  });
});
```

## Test Data Cleanup (REQUIRED)

**All tests that create data MUST clean up after themselves.** Use the `api` fixture for automatic cleanup.

### Recommended: Use the `api` Fixture (Auto-Cleanup)

The `api` fixture provides a `TestApi` instance that automatically tracks created resources and cleans them up after each test (even on failure). This is the preferred pattern.

```typescript
import {test, expect} from '../../fixtures';

test.describe('Feature Tests', () => {
  test('creates and uses resources', async ({authenticatedPage, api}) => {
    // Create resources - auto-cleaned after test
    const org = await api.organization('myorg');
    const repo = await api.repository(org.name, 'myrepo');
    const team = await api.team(org.name, 'myteam');
    const robot = await api.robot(org.name, 'mybot');

    // Resources are deleted in reverse order: robot, team, repo, org
    await authenticatedPage.goto(`/repository/${repo.fullName}`);
    // ... test code ...
  });
});
```

### Available `api` Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `api.organization(prefix?)` | `{name, email}` | Creates org with unique name |
| `api.repository(namespace?, prefix?, visibility?)` | `{namespace, name, fullName}` | Creates repo (defaults to test user namespace) |
| `api.team(orgName, prefix?, role?)` | `{orgName, name}` | Creates team in org |
| `api.robot(orgName, prefix?, description?)` | `{orgName, shortname, fullName}` | Creates robot account |
| `api.prototype(orgName, role, delegate, activatingUser?)` | `{id}` | Creates default permission |
| `api.setMirrorState(namespace, repoName)` | `void` | Sets repo to MIRROR state |
| `api.raw` | `ApiClient` | Access underlying client for non-tracked operations |

### Using `api.raw` for Non-Tracked Operations

For operations that don't need cleanup (reads) or are cleaned up by parent resource deletion:

```typescript
test('configures mirror', async ({api}) => {
  const org = await api.organization('mirror');
  const repo = await api.repository(org.name, 'mirrorrepo');
  const robot = await api.robot(org.name, 'mirrorbot');
  await api.setMirrorState(org.name, repo.name);

  // Mirror config is cleaned up when repo is deleted
  await api.raw.createMirrorConfig(org.name, repo.name, {...});

  // Read operations don't need cleanup
  const config = await api.raw.getMirrorConfig(org.name, repo.name);
});
```

### Superuser API

Use `superuserApi` for operations requiring superuser privileges:

```typescript
test('admin creates user', async ({superuserApi}) => {
  // Created resources auto-cleaned
  const user = await superuserApi.raw.createUser('newuser', 'password', 'user@example.com');
});
```

### Why Auto-Cleanup is Better

| Manual Cleanup | Auto-Cleanup (`api` fixture) |
|----------------|------------------------------|
| Requires `beforeEach`/`afterEach` | Inline resource creation |
| Must wrap cleanup in try/catch | Automatic error handling |
| Easy to forget cleanup | Cleanup guaranteed |
| Cleanup order must be correct | Reverse-order cleanup automatic |
| Shared state via `let` variables | Scoped variables per test |
| Breaks with parallel tests | Parallel-safe |

### Legacy Pattern (Manual Cleanup)

For reference, the old pattern using `beforeEach`/`afterEach`:

```typescript
// ❌ Legacy pattern - avoid in new tests
test.describe('Feature Tests', () => {
  const namespace = TEST_USERS.user.username;
  let repoName: string;

  test.beforeEach(async ({ authenticatedRequest }) => {
    repoName = uniqueName('testrepo');
    await createRepository(authenticatedRequest, namespace, repoName, 'private');
  });

  test.afterEach(async ({ authenticatedRequest }) => {
    try {
      await deleteRepository(authenticatedRequest, namespace, repoName);
    } catch {
      // Already deleted
    }
  });

  test('does something', async ({ authenticatedPage }) => {
    // ... test code ...
  });
});
```

### Why Cleanup Matters

- Tests run in parallel - leftover data causes collisions
- Tests should be independent and repeatable
- Cleanup prevents database bloat in CI environments
- Use `uniqueName()` to avoid collisions even if cleanup fails

## Session-Destructive Tests (Logout)

Tests that call `/api/v1/signout` require special handling because Quay invalidates **ALL sessions** for that user server-side (`invalidate_all_sessions(user)`). This breaks parallel tests using the same user.

### Solution: Unique Temporary Users

Create a custom fixture that provisions a unique user per test:

```typescript
import {test as base, expect, uniqueName} from '../../fixtures';
import {ApiClient} from '../../utils/api';

const test = base.extend<{logoutPage: Page; logoutUsername: string}>({
  logoutUsername: async ({}, use) => {
    await use(uniqueName('logout'));
  },

  logoutPage: async ({browser, superuserRequest, logoutUsername}, use) => {
    const password = 'testpassword123';
    const email = `${logoutUsername}@example.com`;

    // Create temporary user
    const superApi = new ApiClient(superuserRequest);
    await superApi.createUser(logoutUsername, password, email);

    // Login as temporary user
    const context = await browser.newContext();
    const api = new ApiClient(context.request);
    await api.signIn(logoutUsername, password);

    const page = await context.newPage();
    await use(page);

    // Cleanup
    await page.close();
    await context.close();
    try {
      await superApi.deleteUser(logoutUsername);
    } catch {
      // Already deleted
    }
  },
});

test('logs out successfully', async ({logoutPage}) => {
  // Safe to logout - won't affect other tests
});
```

### When to Use This Pattern

- Tests that call the logout API
- Tests that invalidate sessions
- Any test where signing out is part of the test flow

See `e2e/auth/logout.spec.ts` for a complete implementation.

## Test Consolidation Guidelines

### When to Consolidate

- Tests that share the same setup (create repo → ...)
- Sequential workflow steps (create → verify → update → delete)
- Tests that would be faster as a single flow
- Related CRUD operations on the same entity

### When NOT to Consolidate

- Independent feature verifications
- Tests with different config requirements
- Error/edge case scenarios
- Tests that need isolation for debugging

### Example: Before (Cypress)

```typescript
// 3 separate tests, each needs full setup
it('creates repo setting', () => { /* seed → create setting */ });
it('updates repo setting', () => { /* seed → create → update */ });
it('deletes repo setting', () => { /* seed → create → delete */ });
```

### After (Playwright)

```typescript
test('repo settings lifecycle: create, update, delete', { tag: '@PROJQUAY-1234' }, async ({ page }) => {
  // Create
  await page.goto('/repository/testuser/myrepo?tab=settings');
  // ... configure setting
  await expect(page.getByText('Setting saved')).toBeVisible();

  // Update
  // ... update setting
  await expect(page.getByText('Setting updated')).toBeVisible();

  // Delete
  // ... delete setting
  await expect(page.getByText('Setting removed')).toBeVisible();
});
```

## Config-Dependent Tests

For tests that require specific Quay features, use `@feature:X` tags on the describe block. The test framework automatically skips tests when required features are not enabled.

### Using @feature: Tags (Recommended)

```typescript
import { test, expect } from '../../fixtures';

// Single feature requirement - just add the tag
test.describe('Billing Settings', { tag: ['@organization', '@feature:BILLING'] }, () => {
  test('shows billing information', async ({ authenticatedPage }) => {
    // Auto-skipped if BILLING is not enabled - no manual skip needed!
    await authenticatedPage.goto('/organization/myorg?tab=Settings');
    await authenticatedPage.getByTestId('Billing information').click();
  });
});

// Multiple feature requirements - add multiple @feature: tags
test.describe('Quota Editing', { tag: ['@feature:QUOTA_MANAGEMENT', '@feature:EDIT_QUOTA'] }, () => {
  test('edits quota', async ({ authenticatedPage }) => {
    // Auto-skipped if EITHER feature is disabled
  });
});
```

### Manual Skip (Edge Cases Only)

For rare cases where you need conditional logic beyond feature flags, use `skipUnlessFeature` directly:

```typescript
import { test, expect, skipUnlessFeature } from '../../fixtures';

test('shows registry autoprune policy', async ({ authenticatedPage, quayConfig }) => {
  // Additional condition beyond the @feature: tag
  const hasRegistryPolicy = quayConfig?.config?.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY != null;
  test.skip(!hasRegistryPolicy, 'DEFAULT_NAMESPACE_AUTOPRUNE_POLICY not configured');

  // Test code...
});
```

### Available Features

The `QuayFeature` type includes:
- `BILLING` - Billing/subscription features
- `QUOTA_MANAGEMENT` / `EDIT_QUOTA` - Storage quotas
- `AUTO_PRUNE` - Auto-pruning policies
- `PROXY_CACHE` - Proxy cache configuration
- `REPO_MIRROR` - Repository mirroring
- `SECURITY_SCANNER` - Security scanning
- `CHANGE_TAG_EXPIRATION` - Tag expiration settings
- `USER_METADATA` - User profile metadata
- `MAILING` - Email features

### Why This Pattern?

1. **Single source of truth**: Feature specified only in the tag, no duplication
2. **Self-documenting**: Tests skip with clear reason in output
3. **Type-safe**: Feature names are typed for autocomplete
4. **CLI filtering**: Filter tests with `npx playwright test --grep @feature:BILLING`
5. **No boilerplate**: No manual `test.skip()` calls needed in each test

### Test Output

When a feature is disabled, the test output shows:
```text
✓ validates email and saves org settings (2.3s)
- billing email and receipt settings (skipped: Required feature(s) not enabled: BILLING)
✓ CLI token tab not visible (1.1s)
```

## Container-Dependent Tests

For tests that require a container runtime (podman or docker), use the `@container` tag. Tests are automatically skipped when no container runtime is available.

### Using @container Tag

```typescript
import { test, expect } from '../../fixtures';
import { pushImage } from '../../utils/container';

// Tag on describe block - all tests auto-skip if no container runtime
test.describe('Image Push Tests', { tag: ['@container'] }, () => {
  test('pushes image to registry', async ({ authenticatedPage, api }) => {
    // Auto-skipped if podman/docker not available
    const repo = await api.repository();
    await pushImage(repo.namespace, repo.name, 'latest', username, password);
    // ... test assertions
  });
});
```

### With beforeAll Setup

When using `beforeAll` for shared container setup, check `cachedContainerAvailable`:

```typescript
test.describe('Multi-Arch Tests', { tag: ['@container'] }, () => {
  let testRepo: { namespace: string; name: string };

  test.beforeAll(async ({ userContext, cachedContainerAvailable }) => {
    // Skip setup if no container runtime (tests auto-skip via @container tag)
    if (!cachedContainerAvailable) return;

    // Push images for tests...
  });

  test('verifies multi-arch manifest', async ({ authenticatedPage }) => {
    // Auto-skipped if no container runtime
  });
});
```

### Test Output

When no container runtime is available:
```text
- pushes image to registry (skipped: Container runtime (podman/docker) required)
```

## Common Gotchas

| Issue | Cypress | Playwright |
|-------|---------|------------|
| Async/Await | Implicit chaining | Must use `await` |
| Auto-waiting | `cy.get()` retries | `locator` auto-waits |
| Timeouts | `defaultCommandTimeout` | `timeout` in config |
| Screenshots | Auto on failure | Configure in config |
| Selectors | jQuery-like | Prefer `getByRole`, `getByTestId` |
| Network waits | `cy.wait('@alias')` | Usually not needed |

## Example Migration

### Original Cypress Test

```typescript
// cypress/e2e/repository-delete.cy.ts
describe('Repository Delete', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => cy.loginByCSRF(token));
    cy.visit('/repository/testuser/testrepo?tab=settings');
    cy.contains('Delete Repository').click();
  });

  it('Deletes repository', () => {
    cy.contains('Deleting a repository cannot be undone').should('exist');
    cy.get('button[test-id="delete-repository-btn"]').click();
    cy.get('input[placeholder="Enter repository here"]').type('testuser/testrepo');
    cy.get('#delete-repository-modal').within(() =>
      cy.get('button').contains('Delete').click()
    );
    cy.url().should('eq', `${Cypress.config('baseUrl')}/repository`);
  });
});
```

### Migrated Playwright Test

```typescript
// playwright/e2e/repository/repository-delete.spec.ts
import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

test.describe('Repository Delete', {tag: ['@critical', '@repository']}, () => {
  test('deletes repository via UI', {tag: '@PROJQUAY-XXXX'}, async ({
    authenticatedPage,
    authenticatedRequest,
    api,
  }) => {
    // Create test repository - auto-cleaned if test fails
    const repo = await api.repository(undefined, 'delrepo');

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=settings`);
    await authenticatedPage.getByTestId('settings-tab-deleterepository').click();

    await expect(
      authenticatedPage.getByText('Deleting a repository cannot be undone'),
    ).toBeVisible();

    await authenticatedPage.getByTestId('delete-repository-btn').click();
    await authenticatedPage
      .getByTestId('delete-repository-confirm-input')
      .fill(repo.fullName);
    await authenticatedPage.getByTestId('delete-repository-confirm-btn').click();

    await expect(authenticatedPage).toHaveURL('/repository');

    // Verify via API
    const response = await authenticatedRequest.get(
      `${API_URL}/api/v1/repository/${repo.fullName}`,
    );
    expect(response.status()).toBe(404);
  });
});
```

## Files Reference

| File | Purpose |
|------|---------|
| `playwright.config.ts` | Playwright configuration |
| `playwright/global-setup.ts` | Creates test users (admin, testuser, readonly) |
| `playwright/fixtures.ts` | Custom fixtures with pre-auth contexts, `uniqueName()` |
| `playwright/utils/api/` | API utilities organized by resource type |
| `playwright/utils/api/csrf.ts` | CSRF token helper: `getCsrfToken` |
| `playwright/utils/api/organization.ts` | Organization utilities: `createOrganization`, `deleteOrganization` |
| `playwright/utils/api/repository.ts` | Repository utilities: `createRepository`, `deleteRepository` |
| `playwright/utils/api/team.ts` | Team utilities: `createTeam`, `deleteTeam` |
| `playwright/utils/config.ts` | Global config: `API_URL`, `BASE_URL` |
| `playwright/utils/container.ts` | Container utilities (multi-runtime: podman/docker): `pushImage`, `isContainerRuntimeAvailable` |
| `playwright/MIGRATION.md` | This guide |

## Migration Checklist

Track migration progress from Cypress to Playwright.

### Legend
- ✅ Migrated
- 🚧 In Progress
- ⬚ Not Started

### Status

| Status | Cypress File | Playwright File | Notes |
|--------|--------------|-----------------|-------|
| ✅ | `repository-delete.cy.ts` | `repository/repository-delete.spec.ts` | |
| ✅ | `org-settings.cy.ts` | `organization/settings.spec.ts` | @organization, @feature:USER_METADATA, @feature:BILLING, consolidated 4→3 tests (tag expiration in account-settings) |
| ✅ | `account-settings.cy.ts` | `user/account-settings.spec.ts` | @user, @feature:BILLING, @feature:MAILING, @feature:CHANGE_TAG_EXPIRATION, consolidated 31→20 tests |
| ⬚ | `autopruning.cy.ts` | | |
| ✅ | `breadcrumbs.cy.ts` | `ui/breadcrumbs.spec.ts` | |
| ⬚ | `builds.cy.ts` | | |
| ✅ | `create-account.cy.ts` | `auth/create-account.spec.ts` | @feature:MAILING, @feature:QUOTA_MANAGEMENT, consolidated 10→6 tests |
| ✅ | `default-permissions.cy.ts` | `organization/default-permissions.spec.ts` | |
| ⬚ | `external-login.cy.ts` | | @config:OIDC |
| ✅ | `external-scripts.cy.ts` | `ui/external-scripts.spec.ts` | @feature:BILLING |
| ⬚ | `footer.cy.ts` | | |
| ⬚ | `fresh-login-oidc.cy.ts` | | @config:OIDC |
| ✅ | `logout.cy.ts` | `auth/logout.spec.ts` | Consolidated 6→4 tests |
| ✅ | `manage-team-members.cy.ts` | `organization/team-members.spec.ts` | @organization, 7 tests preserved |
| ⬚ | `marketplace.cy.ts` | | @config:BILLING |
| ✅ | `mirroring.cy.ts` | `repository/mirroring.spec.ts` | @feature:REPO_MIRROR, consolidated 18→5 tests |
| ✅ | `notification-drawer.cy.ts` | `ui/notification-drawer.spec.ts` | @container |
| ⬚ | `oauth-callback.cy.ts` | | |
| ✅ | `org-list.cy.ts` | `organization/org-list.spec.ts` | @organization, @feature:SUPERUSERS_FULL_ACCESS, @feature:QUOTA_MANAGEMENT, consolidated 22→10 tests |
| ⬚ | `org-oauth.cy.ts` | | |
| ✅ | `overview.cy.ts` | `ui/overview.spec.ts` | |
| ⬚ | `packages-report.cy.ts` | | |
| ✅ | `proxy-cache.cy.ts` | `organization/proxy-cache.spec.ts` | @feature:PROXY_CACHE, consolidated 4→3 tests |
| ✅ | `quota.cy.ts` | `organization/quota.spec.ts` | @feature:QUOTA_MANAGEMENT, @feature:EDIT_QUOTA, consolidated 27→7 tests |
| ✅ | `repositories-list.cy.ts` | `repository/repositories-list.spec.ts` | Consolidated 11→6 tests |
| ✅ | `repository-autopruning.cy.ts` | `repository/autopruning.spec.ts` | @feature:AUTO_PRUNE, consolidated 17→6 tests |
| ⬚ | `repository-details.cy.ts` | | |
| ✅ | `repository-notifications.cy.ts` | `repository/notifications.spec.ts` | @feature:MAILING, consolidated 18→7 tests |
| ✅ | `repository-permissions.cy.ts` | `repository/permissions.spec.ts` | Consolidated 6→3 tests |
| ✅ | `repository-shorthand-navigation.cy.ts` | `repository/shorthand-navigation.spec.ts` | consolidated 11 → 7 tests |
| ✅ | `repository-state.cy.ts` | `repository/mirroring.spec.ts` | @feature:REPO_MIRROR, consolidated into mirroring tests |
| ⬚ | `repository-visibility.cy.ts` | | |
| ✅ | `robot-accounts.cy.ts` | `organization/robot-accounts.spec.ts` | Consolidated 12→4 tests |
| ⬚ | `security-report.cy.ts` | | @feature:SECURITY_SCANNER |
| ⬚ | `security-scanner-feature-toggle.cy.ts` | | @feature:SECURITY_SCANNER |
| ⬚ | `service-status.cy.ts` | | |
| ✅ | `signin.cy.ts` | `auth/signin.spec.ts` | @feature:MAILING, @auth:Database, @feature:SUPERUSERS_FULL_ACCESS, consolidated 30→18 tests |
| ⬚ | `superuser-build-logs.cy.ts` | | Superuser required |
| ✅ | `superuser-change-log.cy.ts` | `superuser/change-log.spec.ts` | Superuser required, 7→2 tests (access control in framework.spec.ts) |
| ✅ | `superuser-framework.cy.ts` | `superuser/framework.spec.ts` | Superuser required, consolidated 7→4 tests |
| ✅ | `superuser-messages.cy.ts` | `superuser/messages.spec.ts` | Superuser required, consolidated 14→6 tests |
| ⬚ | `superuser-org-actions.cy.ts` | | Migration pending: org-actions.spec.ts doesn't exist |
| ✅ | `superuser-service-keys.cy.ts` | `superuser/service-keys.spec.ts` | Superuser required, 17→5 tests consolidated |
| ⬚ | `superuser-usage-logs.cy.ts` | | Superuser required |
| ✅ | `superuser-user-management.cy.ts` | `superuser/user-management.spec.ts` | Superuser required, 29→10 tests consolidated |
| ⬚ | `system-status-banner.cy.ts` | | |
| ⬚ | `tag-details.cy.ts` | | |
| ⬚ | `tag-history-deleted-tags.cy.ts` | | |
| ⬚ | `tags-expanded-view.cy.ts` | | |
| ⬚ | `tags-signatures.cy.ts` | | |
| ⬚ | `teams-and-membership.cy.ts` | | |
| ⬚ | `team-sync.cy.ts` | | @config:OIDC |
| ✅ | `theme-switcher.cy.ts` | `ui/theme-switcher.spec.ts` | |
| ✅ | `update-user.cy.ts` | `user/update-user.spec.ts` | @feature:USER_METADATA, consolidated 7→3 tests (OAuth tests TODO) |
| ✅ | `usage-logs.cy.ts` | `usage-logs.spec.ts`, `superuser/usage-logs.spec.ts` | @logs, @feature:SUPERUSERS_FULL_ACCESS, consolidated 13→10 tests |
