# AGENTS.md

Playwright e2e tests for Quay. Real API interactions, no mocks, auto-cleanup fixtures.

## Quick Commands

```bash
# Run all tests
npx playwright test

# Single file
npx playwright test e2e/repository/permissions.spec.ts

# By tag
npx playwright test --grep @critical
npx playwright test --grep @PROJQUAY-1234
npx playwright test --grep @feature:REPO_MIRROR

# Exclude tests
npx playwright test --grep-invert @feature:BILLING
```

## Directory Structure

```text
playwright/
├── e2e/                    # Test specs by domain
│   ├── auth/               # Login, logout, account creation
│   ├── organization/       # Org settings, teams, robots
│   ├── repository/         # Repo CRUD, permissions, mirroring
│   ├── tags/               # Tag operations
│   └── ui/                 # UI components (breadcrumbs, theme)
├── utils/
│   ├── api/client.ts       # ApiClient for all API operations
│   ├── config.ts           # API_URL, BASE_URL constants
│   └── mailpit.ts          # Email testing utilities
├── fixtures.ts             # Custom fixtures (see below)
└── global-setup.ts         # Creates test users on startup
```

## Core Fixtures

Import from `fixtures.ts`:

```typescript
import {test, expect, uniqueName} from '../../fixtures';
```

| Fixture | Type | Description |
|---------|------|-------------|
| `authenticatedPage` | Page | Browser logged in as regular user |
| `superuserPage` | Page | Browser logged in as admin |
| `readonlyPage` | Page | Browser logged in as readonly user |
| `authenticatedRequest` | APIRequestContext | API client as regular user |
| `superuserRequest` | APIRequestContext | API client as admin |
| `api` | TestApi | Auto-cleanup API client (regular user) |
| `superuserApi` | TestApi | Auto-cleanup API client (admin) |
| `quayConfig` | QuayConfig | Current Quay feature flags |

## Test Pattern

```typescript
import {test, expect} from '../../fixtures';

test.describe('Feature Name', {tag: ['@critical', '@feature:X']}, () => {
  test('does something', async ({authenticatedPage, api}) => {
    // 1. Setup via API (auto-cleaned)
    const org = await api.organization('prefix');
    const repo = await api.repository(org.name, 'repoprefix');

    // 2. Navigate and interact
    await authenticatedPage.goto(`/repository/${repo.fullName}`);
    await authenticatedPage.getByTestId('some-button').click();

    // 3. Assert
    await expect(authenticatedPage.getByText('Success')).toBeVisible();
  });
});
```

See `e2e/repository/repository-delete.spec.ts` for a complete example.

## API Fixture Methods

All methods auto-cleanup after test (even on failure):

| Method | Returns | Description |
|--------|---------|-------------|
| `api.organization(prefix?)` | `{name, email}` | Create org with unique name |
| `api.repository(namespace?, prefix?, visibility?)` | `{namespace, name, fullName}` | Create repo (defaults to test user) |
| `api.repositoryWithName(namespace, exactName)` | `{...}` | Create repo with exact name (multi-segment) |
| `api.team(orgName, prefix?, role?)` | `{orgName, name}` | Create team in org |
| `api.robot(orgName, prefix?, description?)` | `{orgName, shortname, fullName}` | Create robot account |
| `api.prototype(orgName, role, delegate)` | `{id}` | Create default permission |
| `api.repositoryPermission(ns, repo, type, entity, role)` | `{...}` | Add permission to repo |
| `api.notification(ns, repo, event, method, config)` | `{uuid, ...}` | Create repo notification |
| `api.setMirrorState(namespace, repoName)` | void | Set repo to MIRROR state |
| `api.raw` | ApiClient | Access underlying client (no auto-cleanup) |

## Tagging

| Category | Format | Example |
|----------|--------|---------|
| JIRA | `@PROJQUAY-####` | `@PROJQUAY-1234` |
| Priority | `@critical`, `@smoke` | `@critical` |
| Feature | `@repository`, `@organization` | `@repository` |
| Feature flag | `@feature:X` | `@feature:REPO_MIRROR` |

Tests with `@feature:X` tags auto-skip when that feature is disabled.

Available features: `BILLING`, `QUOTA_MANAGEMENT`, `EDIT_QUOTA`, `AUTO_PRUNE`, `PROXY_CACHE`, `REPO_MIRROR`, `SECURITY_SCANNER`, `CHANGE_TAG_EXPIRATION`, `USER_METADATA`, `MAILING`, `IMAGE_EXPIRY_TRIGGER`

## Selectors

Priority order:

1. `getByTestId('x')` - Preferred, stable
2. `getByRole('button', {name: 'Save'})` - Semantic, accessible
3. `getByText('exact text')` - When unique
4. `locator('[data-label="x"]')` - Table cells, structured data

**Naming convention:** `{feature}-{component}-{action}` (e.g., `delete-repository-confirm-btn`)

## Critical Rules

1. **No mocks** - Use real API calls, not `cy.intercept()` or route handlers
2. **Use `api` fixture** - Always use for test data, ensures cleanup
3. **Use `data-testid`** - Not `test-id` (Playwright requires `data-` prefix)
4. **Tag tests** - Add `@feature:X` for feature-dependent tests
5. **Unique names** - Use `uniqueName('prefix')` for all created resources
6. **Verify via API** - After destructive UI actions, confirm with API call

## Example Specs

| Pattern | Example File |
|---------|--------------|
| Basic CRUD | `e2e/repository/repository-delete.spec.ts` |
| Org with team/robot | `e2e/repository/permissions.spec.ts` |
| Feature flag skip | `e2e/repository/mirroring.spec.ts` |
| Session-destructive | `e2e/auth/logout.spec.ts` |
| UI components | `e2e/ui/theme-switcher.spec.ts` |
