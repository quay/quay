# Playwright E2E Testing Guide

Authoritative reference for writing and maintaining Playwright end-to-end tests in Project Quay.

## Key Principles

1. **NO MOCKS/INTERCEPTS** - Use real API interactions, not `page.route()` stubs (exception: external third-party CDNs like StatusPage)
2. **NO DATABASE SEEDING** - Use API utilities to create test data dynamically
3. **Use Playwright Tags** - Label every test with `{ tag: [...] }` for filtering and traceability
4. **Use the `api` Fixture** - Create test data inline with automatic cleanup
5. **Consolidate When Logical** - Merge sequential CRUD operations into single e2e flows

## Directory Structure

```text
web/playwright/
├── e2e/                          # Test specifications
│   ├── api/                      # API-level tests
│   ├── auth/                     # Authentication tests
│   ├── legacy-ui/                # Angular UI tests
│   ├── organization/             # Organization tests
│   ├── repository/               # Repository tests
│   ├── superuser/                # Superuser tests
│   ├── tags/                     # Tag tests
│   ├── ui/                       # UI component tests
│   └── user/                     # User account tests
├── utils/                        # Shared utilities
│   ├── api/                      # API utilities by resource
│   │   ├── index.ts              # Re-exports all API utilities
│   │   ├── auth.ts               # Authentication helpers
│   │   ├── client.ts             # TestApi client (auto-cleanup)
│   │   ├── csrf.ts               # getCsrfToken
│   │   └── raw-client.ts         # ApiClient (raw, no auto-cleanup)
│   ├── config.ts                 # API_URL, BASE_URL
│   ├── container.ts              # pushImage, isContainerRuntimeAvailable (skopeo/crane/oras/regctl)
│   ├── mailpit.ts                # Email testing utilities
│   ├── s3.ts                     # S3 storage utilities
│   ├── security.ts               # Security scanning utilities
│   ├── test-utils.ts             # General test helpers
│   └── webhook.ts                # Webhook receiver utilities
├── fixtures/                     # Static test data (e.g., ORAS referrer JSON)
├── fixtures.ts                   # Custom fixtures, uniqueName()
├── global-setup.ts               # Creates admin, testuser, readonly users
├── ensure-required-tags.cjs      # Tag validation script
└── AGENTS.md                     # This guide
```

## Test Tagging System

Use Playwright's built-in tag feature for test categorization.

### Syntax

```typescript
// Tag a describe block
test.describe('Feature Name', {tag: ['@critical', '@repository']}, () => {
  // Tag individual tests
  test('does something', {tag: '@PROJQUAY-1234'}, async ({page}) => {
    // ...
  });
});
```

### Tag Categories

| Category     | Format                 | Example                | Purpose                                                                |
| ------------ | ---------------------- | ---------------------- | ---------------------------------------------------------------------- |
| JIRA         | `@PROJQUAY-####`       | `@PROJQUAY-1234`       | Link to JIRA ticket                                                    |
| Priority     | `@critical`, `@smoke`  | `@critical`            | Test importance                                                        |
| Feature      | `@repository`          | `@repository`          | Feature area                                                           |
| Config       | `@config:BILLING`      | `@config:OIDC`         | Required config                                                        |
| Feature Flag | `@feature:PROXY_CACHE` | `@feature:REPO_MIRROR` | Required feature                                                       |
| Container    | `@container`           | `@container`           | Requires registry image tooling (auto-skip)                            |
| Superuser    | `@superuser`           | `@superuser`           | Uses superuser-authenticated fixtures or local fixtures backed by them |
| Webhook      | `@webhook`             | `@webhook`             | Uses the webhook receiver fixture or helper                            |

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

### Required Usage Tags

Tests that use `superuserPage`, `superuserRequest`, `superuserApi`,
`superuserContext`, `freshUser`, or spec-local fixtures backed by those fixtures
must include `@superuser`.

Tests that use the `webhook` fixture or instantiate `WebhookReceiver` must
include `@webhook`.

```bash
# Check tag coverage
pnpm run test:e2e:check-required-tags

# Add missing tags to existing tests
pnpm run test:e2e:fix-required-tags
```

## data-testid Conventions

Prefer `getByTestId()` over element IDs or framework-generated selectors (like PatternFly's `#pf-tab-N-tabname`). `data-testid` attributes are stable across CSS and framework changes.

### IMPORTANT: Use data-testid, NOT test-id

Playwright's `getByTestId()` only works with the standard `data-testid` attribute. Using `test-id` (without the `data-` prefix) requires manual locator selectors.

```tsx
// Wrong - requires manual locator
<Button test-id="my-button">Click</Button>
await page.locator('[test-id="my-button"]').click();

// Correct - works with getByTestId()
<Button data-testid="my-button">Click</Button>
await page.getByTestId('my-button').click();
```

### Naming Convention

```text
{feature}-{component}-{action/purpose}
```

Examples: `org-settings-email`, `org-settings-save-button`, `billing-invoice-checkbox`, `delete-repository-confirm-btn`

### Adding to Components

```tsx
// Add data-testid to interactive elements
<Button
  id="save-billing-settings"
  data-testid="billing-save-button"
  onClick={handleSave}
>
  Save
</Button>

// For form components using shared wrappers
<FormTextInput
  name="email"
  fieldId="org-settings-email"
  data-testid="org-settings-email"
  // ...
/>
```

### Using in Tests

```typescript
// Prefer getByTestId
await page.getByTestId('org-settings-save-button').click();

// Over element IDs
await page.locator('#save-org-settings').click();

// Or framework-specific selectors (may break on upgrade)
await page.locator('#pf-tab-2-cliconfig').click();
```

## Authentication Pattern

### Using Fixtures (Recommended)

```typescript
import {test, expect} from '../fixtures';

// authenticatedPage is already logged in as regular user
test('can view repository list', async ({authenticatedPage}) => {
  await authenticatedPage.goto('/repository');
  await expect(authenticatedPage.getByText('Repositories')).toBeVisible();
});

// superuserPage is logged in as superuser
test('superuser can manage users', async ({superuserPage}) => {
  await superuserPage.goto('/superuser');
});
```

### Manual Login (When Needed)

```typescript
import {loginUser} from '../fixtures';

test('custom login scenario', async ({page, request}) => {
  const csrfToken = await loginUser(request, 'customuser', 'password');
  await page.goto('/repository');
});
```

## Test Data Creation with the `api` Fixture

The `api` fixture provides methods to create test resources with **automatic cleanup** after each test (even on failure). Resources are deleted in reverse creation order.

```typescript
import {test, expect} from '../../fixtures';

test.describe('Repository Tests', () => {
  test('works with repository', async ({authenticatedPage, api}) => {
    // Create resources inline - auto-cleaned after test
    const org = await api.organization('myorg');
    const repo = await api.repository(org.name, 'myrepo');
    const team = await api.team(org.name, 'myteam');
    const robot = await api.robot(org.name, 'mybot');

    await authenticatedPage.goto(`/repository/${repo.fullName}`);
    // ... test code ...
    // Resources auto-deleted in reverse order: robot, team, repo, org
  });
});
```

### Available `api` Methods

Methods are grouped by category. All create methods register automatic cleanup unless noted otherwise.

#### Basic Resources

| Method | Returns | Description |
| --- | --- | --- |
| `api.organization(prefix?, email?)` | `{name, email}` | Creates org with unique name |
| `api.repository(namespace?, prefix?, visibility?)` | `{namespace, name, fullName}` | Creates repo (defaults to test user namespace) |
| `api.repositoryWithName(namespace, name, visibility?)` | `{namespace, name, fullName}` | Creates repo with an exact name; supports multi-segment names like `release/installer` |
| `api.team(orgName, prefix?, role?)` | `{orgName, name}` | Creates team in org |
| `api.teamMember(orgName, teamName, memberName)` | `{orgName, teamName, memberName}` | Adds a member to a team |
| `api.robot(orgName, prefix?, description?)` | `{orgName, shortname, fullName, token}` | Creates robot account in org |

#### Permissions

| Method | Returns | Description |
| --- | --- | --- |
| `api.prototype(orgName, role, delegate, activatingUser?)` | `{id}` | Creates default permission (prototype) |
| `api.repositoryPermission(namespace, repoName, entityType, entityName, role?)` | `{namespace, repoName, entityType, entityName}` | Grants a user, robot, or team access to a repo |

#### Repository Features

| Method | Returns | Description |
| --- | --- | --- |
| `api.notification(namespace, repoName, event, method, config, title?)` | `{uuid, namespace, repoName}` | Creates a repository notification |
| `api.setMirrorState(namespace, repoName)` | `void` | Sets repo to MIRROR state (no cleanup needed) |
| `api.build(namespace, repoName, dockerfileContent?, dockerTags?)` | `{namespace, repoName, buildId}` | Starts a Dockerfile build (no cleanup needed; tied to repo lifecycle) |

#### Policies

| Method | Returns | Description |
| --- | --- | --- |
| `api.orgImmutabilityPolicy(orgName, tagPattern, tagPatternMatches?)` | `{uuid, tagPattern, tagPatternMatches, orgName}` | Creates an immutability policy for an org |
| `api.repoImmutabilityPolicy(namespace, repoName, tagPattern, tagPatternMatches?)` | `{uuid, tagPattern, tagPatternMatches, namespace, repoName}` | Creates an immutability policy for a repo |
| `api.orgAutoPrunePolicy(orgName, policy)` | `{uuid, orgName}` | Creates an auto-prune policy for an org |
| `api.repoAutoPrunePolicy(namespace, repoName, policy)` | `{uuid, namespace, repoName}` | Creates an auto-prune policy for a repo |
| `api.userAutoPrunePolicy(policy)` | `{uuid}` | Creates an auto-prune policy for the current user |
| `api.quota(orgName, limitBytes?)` | `{orgName, quotaId, limitBytes}` | Creates a quota for an org (default: 10 GiB) |
| `api.userQuota(username, limitBytes?)` | `{orgName, quotaId, limitBytes}` | Creates a quota for a user namespace (superuser only) |

#### Superuser-Only

These methods require the `superuserApi` fixture instead of `api`.

| Method | Returns | Description |
| --- | --- | --- |
| `superuserApi.user(prefix?)` | `{username, email, password}` | Creates a user via the superuser API |
| `superuserApi.message(content, severity?)` | `{uuid, content, severity}` | Creates a global message |
| `superuserApi.serviceKey(service, name?, expiration?)` | `{kid, service, name?, expiration?}` | Creates a service key |

#### OAuth

| Method | Returns | Description |
| --- | --- | --- |
| `api.oauthApplication(orgName, prefix?)` | `{orgName, name, clientId, clientSecret?}` | Creates an OAuth application in an org |

#### Raw Client Access

| Method | Returns | Description |
| --- | --- | --- |
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
  const user = await superuserApi.raw.createUser(
    'newuser',
    'password',
    'user@example.com',
  );
});
```

### Anti-Pattern: Manual Cleanup

Avoid `beforeEach`/`afterEach` with manual `try/catch` cleanup. The `api` fixture handles cleanup automatically, is parallel-safe, and guarantees reverse-order deletion. See existing tests for the legacy pattern if maintaining older specs.

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

- Tests that share the same setup (create repo -> ...)
- Sequential workflow steps (create -> verify -> update -> delete)
- Tests that would be faster as a single flow
- Related CRUD operations on the same entity

### When NOT to Consolidate

- Independent feature verifications
- Tests with different config requirements
- Error/edge case scenarios
- Tests that need isolation for debugging

### Example: Consolidated Lifecycle Test

```typescript
test(
  'repo settings lifecycle: create, update, delete',
  {tag: '@PROJQUAY-1234'},
  async ({page}) => {
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
  },
);
```

## Config-Dependent Tests

For tests that require specific Quay features, use `@feature:X` tags on the describe block. The test framework automatically skips tests when required features are not enabled.

### Using @feature: Tags (Recommended)

```typescript
import {test, expect} from '../../fixtures';

// Single feature requirement - just add the tag
test.describe(
  'Billing Settings',
  {tag: ['@organization', '@feature:BILLING']},
  () => {
    test('shows billing information', async ({authenticatedPage}) => {
      // Auto-skipped if BILLING is not enabled - no manual skip needed!
      await authenticatedPage.goto('/organization/myorg?tab=Settings');
      await authenticatedPage.getByTestId('Billing information').click();
    });
  },
);

// Multiple feature requirements - add multiple @feature: tags
test.describe(
  'Quota Editing',
  {tag: ['@feature:QUOTA_MANAGEMENT', '@feature:EDIT_QUOTA']},
  () => {
    test('edits quota', async ({authenticatedPage}) => {
      // Auto-skipped if EITHER feature is disabled
    });
  },
);
```

### Manual Skip (Edge Cases Only)

For rare cases where you need conditional logic beyond feature flags, use `skipUnlessFeature` directly:

```typescript
import {test, expect, skipUnlessFeature} from '../../fixtures';

test('shows registry autoprune policy', async ({
  authenticatedPage,
  quayConfig,
}) => {
  const hasRegistryPolicy =
    quayConfig?.config?.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY != null;
  test.skip(
    !hasRegistryPolicy,
    'DEFAULT_NAMESPACE_AUTOPRUNE_POLICY not configured',
  );
  // Test code...
});
```

### Available Features

See the `QuayFeature` type in `fixtures.ts` for the complete list of available feature flags.

### Test Output

When a feature is disabled, tests skip with a clear reason:

```text
- billing email and receipt settings (skipped: Required feature(s) not enabled: BILLING)
```

## Container-Dependent Tests

For tests that require registry image tooling (skopeo, crane, oras, or regctl), use the `@container` tag. Tests are automatically skipped when skopeo is unavailable.

### Using @container Tag

```typescript
import {test, expect} from '../../fixtures';
import {pushImage} from '../../utils/container';

// Tag on describe block - all tests auto-skip if registry image tooling is unavailable
test.describe('Image Push Tests', {tag: ['@container']}, () => {
  test('pushes image to registry', async ({authenticatedPage, api}) => {
    const repo = await api.repository();
    await pushImage(repo.namespace, repo.name, 'latest', username, password);
    // ... test assertions
  });
});
```

### With beforeAll Setup

When using `beforeAll` for shared container setup, check `cachedContainerAvailable`:

```typescript
test.describe('Multi-Arch Tests', {tag: ['@container']}, () => {
  let testRepo: {namespace: string; name: string};

  test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
    // Skip setup if registry image tooling is unavailable (tests auto-skip via @container tag)
    if (!cachedContainerAvailable) return;
    // Push images for tests...
  });

  test('verifies multi-arch manifest', async ({authenticatedPage}) => {
    // Auto-skipped if registry image tooling is unavailable
  });
});
```

## Common Gotchas

| Issue | What to Know |
| ----- | ------------ |
| **Async/Await** | Every Playwright interaction must be `await`ed - no implicit chaining |
| **Auto-waiting** | Locators auto-wait for elements; explicit waits are rarely needed |
| **Timeouts** | Configure via `timeout` in `playwright.config.ts`, not per-command |
| **Screenshots** | Configure capture-on-failure in `playwright.config.ts` |
| **Selectors** | Prefer `getByRole()`, `getByTestId()`, `getByText()` over CSS selectors |
| **Network waits** | Usually unnecessary - Playwright auto-waits for navigation and network idle |
| **Parallel safety** | Use `uniqueName()` for all created resources; never hard-code entity names |
| **Fixture scoping** | `api` fixture is per-test; use `beforeAll` + `cachedContainerAvailable` for expensive shared setup |
