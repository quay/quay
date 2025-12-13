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
│   └── superuser/                # Superuser tests
├── utils/                        # Shared utilities
│   ├── api.ts                    # createRepository, deleteRepository
│   └── config.ts                 # API_URL, BASE_URL
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

### Repositories

Create repositories in the user's namespace (e.g., `testuser`):

```typescript
import { test, expect, uniqueName } from '../../fixtures';
import { createRepository, deleteRepository } from '../../utils/api';
import { TEST_USERS } from '../../global-setup';

test.describe('Repository Tests', () => {
  const namespace = TEST_USERS.user.username; // 'testuser'
  let repoName: string;

  test.beforeEach(async ({ authenticatedRequest }) => {
    repoName = uniqueName('testrepo');
    // Create repo in user's namespace (CSRF token is fetched automatically)
    await createRepository(authenticatedRequest, namespace, repoName, 'private');
  });

  test.afterEach(async ({ authenticatedRequest }) => {
    await deleteRepository(authenticatedRequest, namespace, repoName);
  });
});
```

## Test Data Cleanup (REQUIRED)

**All tests that create data MUST clean up after themselves.** Use `test.afterEach` hooks.

### Key Principles

- Create data in `test.beforeEach`
- Delete data in `test.afterEach`
- Use try/catch in cleanup to handle cases where deletion already happened
- Use `uniqueName()` to generate unique resource names

### Example Pattern

```typescript
test.describe('Feature Tests', () => {
  const namespace = TEST_USERS.user.username;
  let repoName: string;

  test.beforeEach(async ({ authenticatedRequest }) => {
    repoName = uniqueName('testrepo');
    await createRepository(authenticatedRequest, namespace, repoName, 'private');
  });

  test.afterEach(async ({ authenticatedRequest }) => {
    // Always attempt cleanup, even if test failed
    try {
      await deleteRepository(authenticatedRequest, namespace, repoName);
    } catch {
      // Already deleted by test or never created - that's fine
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

For tests that require specific Quay features, use the `skipUnlessFeature` helper for runtime skip with clear messaging.

### Using skipUnlessFeature

```typescript
import { test, expect, skipUnlessFeature } from '../../fixtures';

// Single feature requirement
test('billing settings', { tag: '@config:BILLING' }, async ({
  authenticatedPage,
  quayConfig,
}) => {
  test.skip(...skipUnlessFeature(quayConfig, 'BILLING'));

  // Test only runs if BILLING is enabled
  await authenticatedPage.goto('/organization/myorg?tab=Settings');
  await authenticatedPage.getByTestId('Billing information').click();
});

// Multiple feature requirements
test('quota editing', { tag: '@config:QUOTA' }, async ({
  page,
  quayConfig,
}) => {
  test.skip(...skipUnlessFeature(quayConfig, 'QUOTA_MANAGEMENT', 'EDIT_QUOTA'));

  // Test only runs if both features are enabled
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

1. **Self-documenting**: Tests skip with clear reason in output
2. **Type-safe**: Feature names are typed for autocomplete
3. **No manual filtering**: Works automatically in any environment
4. **Tag compatible**: Keep `@config:*` tags for documentation/filtering

### Test Output

When a feature is disabled, the test output shows:
```text
✓ validates email and saves org settings (2.3s)
- billing email and receipt settings (skipped: Required feature(s) not enabled: BILLING)
✓ CLI token tab not visible (1.1s)
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
import { test, expect, uniqueName } from '../../fixtures';
import { createRepository, deleteRepository } from '../../utils/api';
import { API_URL } from '../../utils/config';
import { TEST_USERS } from '../../global-setup';

test.describe('Repository Delete', { tag: ['@critical', '@repository'] }, () => {
  const namespace = TEST_USERS.user.username;
  let repoName: string;

  test.beforeEach(async ({ authenticatedRequest }) => {
    repoName = uniqueName('delrepo');
    await createRepository(authenticatedRequest, namespace, repoName, 'private');
  });

  test.afterEach(async ({ authenticatedRequest }) => {
    try {
      await deleteRepository(authenticatedRequest, namespace, repoName);
    } catch {
      // Already deleted by test
    }
  });

  test('deletes repository via UI', { tag: '@PROJQUAY-XXXX' }, async ({
    authenticatedPage,
    authenticatedRequest,
  }) => {
    await authenticatedPage.goto(`/repository/${namespace}/${repoName}?tab=settings`);
    await authenticatedPage.getByTestId('settings-tab-deleterepository').click();

    await expect(
      authenticatedPage.getByText('Deleting a repository cannot be undone')
    ).toBeVisible();

    await authenticatedPage.getByTestId('delete-repository-btn').click();
    await authenticatedPage.getByTestId('delete-repository-confirm-input').fill(`${namespace}/${repoName}`);
    await authenticatedPage.getByTestId('delete-repository-confirm-btn').click();

    await expect(authenticatedPage).toHaveURL('/repository');

    // Verify via API
    const response = await authenticatedRequest.get(
      `${API_URL}/api/v1/repository/${namespace}/${repoName}`
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
| `playwright/utils/api.ts` | API utilities: `createRepository`, `deleteRepository` |
| `playwright/utils/config.ts` | Global config: `API_URL`, `BASE_URL` |
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
| ⬚ | `org-settings.cy.ts` | | |
| ⬚ | `account-settings.cy.ts` | | |
| ⬚ | `autopruning.cy.ts` | | |
| ⬚ | `breadcrumbs.cy.ts` | | |
| ⬚ | `builds.cy.ts` | | |
| ⬚ | `create-account.cy.ts` | | |
| ⬚ | `default-permissions.cy.ts` | | |
| ⬚ | `external-login.cy.ts` | | @config:OIDC |
| ⬚ | `external-scripts.cy.ts` | | |
| ⬚ | `footer.cy.ts` | | |
| ⬚ | `fresh-login-oidc.cy.ts` | | @config:OIDC |
| ⬚ | `logout.cy.ts` | | |
| ⬚ | `manage-team-members.cy.ts` | | |
| ⬚ | `marketplace.cy.ts` | | @config:BILLING |
| ⬚ | `mirroring.cy.ts` | | @feature:REPO_MIRROR |
| ⬚ | `notification-drawer.cy.ts` | | |
| ⬚ | `oauth-callback.cy.ts` | | |
| ⬚ | `org-list.cy.ts` | | |
| ⬚ | `org-oauth.cy.ts` | | |
| ⬚ | `overview.cy.ts` | | |
| ⬚ | `packages-report.cy.ts` | | |
| ⬚ | `proxy-cache.cy.ts` | | @feature:PROXY_CACHE |
| ⬚ | `quota.cy.ts` | | @feature:QUOTA_MANAGEMENT |
| ⬚ | `repositories-list.cy.ts` | | |
| ⬚ | `repository-autopruning.cy.ts` | | @feature:AUTO_PRUNE |
| ⬚ | `repository-details.cy.ts` | | |
| ⬚ | `repository-notifications.cy.ts` | | |
| ⬚ | `repository-permissions.cy.ts` | | |
| ⬚ | `repository-shorthand-navigation.cy.ts` | | |
| ⬚ | `repository-state.cy.ts` | | |
| ⬚ | `repository-visibility.cy.ts` | | |
| ⬚ | `robot-accounts.cy.ts` | | |
| ⬚ | `security-report.cy.ts` | | @feature:SECURITY_SCANNER |
| ⬚ | `security-scanner-feature-toggle.cy.ts` | | @feature:SECURITY_SCANNER |
| ⬚ | `service-status.cy.ts` | | |
| ⬚ | `signin.cy.ts` | | |
| ⬚ | `superuser-build-logs.cy.ts` | | Superuser required |
| ⬚ | `superuser-change-log.cy.ts` | | Superuser required |
| ⬚ | `superuser-framework.cy.ts` | | Superuser required |
| ⬚ | `superuser-messages.cy.ts` | | Superuser required |
| ⬚ | `superuser-org-actions.cy.ts` | | Superuser required |
| ⬚ | `superuser-service-keys.cy.ts` | | Superuser required |
| ⬚ | `superuser-usage-logs.cy.ts` | | Superuser required |
| ⬚ | `superuser-user-management.cy.ts` | | Superuser required |
| ⬚ | `system-status-banner.cy.ts` | | |
| ⬚ | `tag-details.cy.ts` | | |
| ⬚ | `tag-history-deleted-tags.cy.ts` | | |
| ⬚ | `tags-expanded-view.cy.ts` | | |
| ⬚ | `tags-signatures.cy.ts` | | |
| ⬚ | `teams-and-membership.cy.ts` | | |
| ⬚ | `team-sync.cy.ts` | | @config:OIDC |
| ⬚ | `theme-switcher.cy.ts` | | |
| ⬚ | `update-user.cy.ts` | | |
| ⬚ | `usage-logs.cy.ts` | | |

### Progress Summary

- **Total**: 54 Cypress test files
- **Migrated**: 1 (2%)
- **Remaining**: 53
