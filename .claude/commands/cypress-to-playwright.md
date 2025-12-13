---
allowed-tools: Read, Glob, Grep, TodoWrite, Edit, Write, AskUserQuestion
argument-hint: <cypress-test-file>
description: Migrate Cypress e2e test to Playwright following MIGRATION.md patterns
---

# Cypress to Playwright Migration

Migrate a Cypress e2e test to Playwright following the project's MIGRATION.md guide.

## Test File

`$ARGUMENTS`

---

## Phase 1: Validation & Analysis

### Step 1: Validate Input

1. **Handle Path Formats:**
   - Full path: Use as-is
   - Filename only (e.g., `org-settings.cy.ts`): Prepend `web/cypress/e2e/`
   - Relative path (e.g., `cypress/e2e/org-settings.cy.ts`): Prepend `web/`

2. **Verify File Exists:**
   - Read the Cypress test file
   - If not found, report error and suggest available files

3. **Check Migration Status:**
   - Check `web/playwright/MIGRATION.md` checklist
   - If migrated, warn and confirm regeneration

### Step 2: Analyze Test Structure

**Create TodoList:**

```
- Validate and analyze Cypress test (in_progress)
- Convert intercepts to real API (pending)
- Generate Playwright test (pending)
- Add data-testid attributes (pending)
- Create migration summary (pending)
```

**Parse the Cypress test**, extracting:

1. **Test Organization:**
   - `describe()` blocks and nesting
   - `it()` / `test()` cases
   - `beforeEach()` / `afterEach()` hooks

2. **Data Setup Patterns:**
   - `cy.exec('npm run quay:seed')` - Database seeding
   - `cy.fixture('filename.json')` - Fixture loading
   - `cy.loginByCSRF(token)` - Login

3. **Network Intercepts:**
   Categorize each `cy.intercept()`:
   - **Config/feature mocks** → Use `skipUnlessFeature()` and test real behavior
   - **Data mocks** → Create real data via API
   - **Wait aliases** → Remove (Playwright auto-waits)
   - **Error scenarios** → Keep as `page.route()` (only acceptable mock)

4. **Selectors:**
   - `[data-cy="..."]` attributes
   - `#element-id` IDs
   - `cy.contains('...')` text

5. **Determine Test Category:**

   | Pattern | Category | Directory | API Utilities |
   |---------|----------|-----------|---------------|
   | `repository-*` | Repository | `repository/` | `createRepository`, `deleteRepository` |
   | `org-*` | Organization | `organization/` | `createOrganization`, `deleteOrganization` |
   | `team-*` | Team | `organization/` | `createTeam`, `deleteTeam` |
   | `superuser-*` | Superuser | `superuser/` | N/A (admin context) |
   | Others | UI | `ui/` | Case-by-case |

---

## Phase 2: Strategic Questions

### Step 3: Analyze Intercepts

**IMPORTANT: Do NOT mock. Convert all intercepts to real API calls or skipUnlessFeature.**

For each `cy.intercept()`, determine the conversion strategy:

| Intercept Type | Conversion Strategy |
|----------------|---------------------|
| Feature flags / config | `skipUnlessFeature(quayConfig, 'FEATURE_NAME')` |
| User/data responses | Create real data via API utilities |
| Wait aliases (`.as('name')`) | Remove - Playwright auto-waits |
| Error responses (4xx, 5xx) | Keep as `page.route()` - only acceptable mock |

**Feature-Dependent Tests:**

When a Cypress test mocks responses that depend on backend features (like `prompts`, `awaiting_verification`, quota settings), convert to:

```typescript
test('feature-dependent behavior', {tag: '@feature:FEATURE_NAME'}, async ({
  page,
  quayConfig,
  superuserRequest,
}) => {
  test.skip(...skipUnlessFeature(quayConfig, 'FEATURE_NAME'));

  // Test real behavior - no mocking
  // Clean up created resources at end
});
```

**Available Features (QuayFeature type):**
- `BILLING`, `QUOTA_MANAGEMENT`, `EDIT_QUOTA`, `AUTO_PRUNE`
- `PROXY_CACHE`, `REPO_MIRROR`, `SECURITY_SCANNER`
- `CHANGE_TAG_EXPIRATION`, `USER_METADATA`, `MAILING`

**Ask user to confirm conversion strategy only if unclear.**

### Step 4: Analyze Test Consolidation

Look for consolidation opportunities:

1. **Sequential Operations:**
   - Test 1: "creates settings"
   - Test 2: "updates settings"
   - Test 3: "deletes settings"
   → Could merge into "settings lifecycle"

2. **Shared Setup:**
   - Multiple tests with identical `beforeEach()`
   → Consider consolidating

3. **Keep Separate:**
   - Different permissions
   - Error/edge cases
   - Different features

**Ask user whether to consolidate.**

### Step 5: Suggest Test Tags

Based on filename and content:

```
SUGGESTED TAGS:

Feature: @organization (from filename)
Priority: @critical (CRUD operations detected)
Config: @config:BILLING (feature flag detected)

Recommended: {tag: ['@organization', '@critical', '@config:BILLING']}
```

### Step 6: Identify Missing data-testid

Find selectors needing `data-testid`:

```
SELECTOR ANALYSIS:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEEDS data-testid:

1. cy.get('#org-settings-email')
   Source: web/src/routes/.../GeneralSettings.tsx:45
   Proposed: data-testid="org-settings-email"

2. cy.get('#save-org-settings')
   Source: web/src/routes/.../GeneralSettings.tsx:89
   Better: Use page.getByRole('button', {name: 'Save'})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALREADY HAS data-testid: 1 selector
TEXT/ROLE-BASED: 1 selector (no testid needed)

Components to update: 1 file
```

**Ask user to confirm adding data-testid attributes.**

---

## Phase 3: Generate Playwright Test

### Step 7: Determine Output Path

Map Cypress path to Playwright:

- `org-settings.cy.ts` → `organization/settings.spec.ts`
- `repository-delete.cy.ts` → `repository/delete.spec.ts`
- `breadcrumbs.cy.ts` → `ui/breadcrumbs.spec.ts`

### Step 8: Generate Test Structure

**Imports:**

```typescript
import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {API_URL} from '../../utils/config';

// Add based on category:
import {createRepository, deleteRepository} from '../../utils/api';
import {skipUnlessFeature} from '../../fixtures';
```

**Structure:**

```typescript
test.describe('Feature Name', {tag: ['@category', '@priority']}, () => {
  const namespace = TEST_USERS.user.username;
  let resourceName: string;

  test.beforeEach(async ({authenticatedRequest}) => {
    resourceName = uniqueName('prefix');
    await createResource(authenticatedRequest, resourceName);
  });

  test.afterEach(async ({authenticatedRequest}) => {
    try {
      await deleteResource(authenticatedRequest, resourceName);
    } catch {
      // Already deleted
    }
  });

  test('does something', async ({authenticatedPage}) => {
    // Test implementation
  });
});
```

### Step 9: Convert Test Cases

**Key Conversions:**

| Cypress | Playwright |
|---------|------------|
| `cy.visit(url)` | `await page.goto(url)` |
| `cy.get('#id')` | `page.getByTestId('id')` |
| `cy.contains('text')` | `page.getByRole('button', {name: 'text'})` |
| `.type(text)` | `.fill(text)` |
| `.should('be.visible')` | `await expect(...).toBeVisible()` |
| `cy.wait('@alias')` | Remove (auto-wait) |
| `cy.intercept({fixture})` | Create real data via API |
| `cy.loginByCSRF()` | Use `authenticatedPage` fixture |

**Feature-Dependent Tests (NO MOCKING):**

```typescript
// Cypress mocked: cy.intercept('GET', '/api/v1/user/', {body: {prompts: [...]}})
// Playwright: Skip if feature disabled, test real behavior
test('user prompts redirect', {tag: '@feature:QUOTA_MANAGEMENT'}, async ({
  page,
  quayConfig,
  superuserRequest,
}) => {
  test.skip(...skipUnlessFeature(quayConfig, 'QUOTA_MANAGEMENT'));

  // Create real user, test real behavior
  const username = uniqueName('testuser');
  // ... test code ...

  // Clean up
  await deleteUser(superuserRequest, username);
});
```

**Error Scenarios (ONLY acceptable mock):**

```typescript
// Only use page.route() for error responses that can't be triggered otherwise
await page.route('**/api/v1/endpoint', async (route) => {
  await route.fulfill({status: 500, body: JSON.stringify({error: 'message'})});
});
```

---

## Phase 4: Update React Components

### Step 10: Add data-testid Attributes

For each component identified:

1. Read component file
2. Add `data-testid` following naming convention: `{feature}-{component}-{purpose}`
3. Apply edit

**Examples:**

```tsx
// FormTextInput
<FormTextInput
  fieldId="org-settings-email"
  data-testid="org-settings-email"  // ADD
  ...
/>

// Button - prefer getByRole instead
<Button onClick={handleSave}>Save</Button>
// Use: page.getByRole('button', {name: 'Save'})

// Tab
<Tab
  eventKey="billing"
  title="Billing"
  data-testid="billing-tab"  // ADD
/>
```

---

## Phase 5: Create Migration Summary

### Step 11: Write Playwright Test

Use Write tool to create the test file.

### Step 12: Document Migration

```markdown
## Migration Summary

**Cypress:** web/cypress/e2e/<file>.cy.ts
**Playwright:** web/playwright/e2e/<dir>/<file>.spec.ts

### Conversions

- Test cases: X migrated
- Intercepts: Y converted to real API, Z kept for error scenarios
- data-testid: N attributes added

### Components Updated

1. web/src/routes/.../Component.tsx
   - Added data-testid="feature-component"

### Run Tests

cd web
npx playwright test e2e/<dir>/<file>.spec.ts
npx playwright test e2e/<dir>/<file>.spec.ts --ui  # Debug mode

### Checklist

- [ ] All tests pass
- [ ] No TypeScript errors
- [ ] Update MIGRATION.md checklist
```

### Step 13: Display Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MIGRATION COMPLETE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Created: web/playwright/e2e/<dir>/<file>.spec.ts
Updated: X component files with data-testid

Next:
  1. Run: cd web && npx playwright test e2e/<dir>/<file>.spec.ts
  2. Update MIGRATION.md checklist
```

---

## Quick Reference

### API Utilities

See `web/playwright/utils/api/` for available utilities (user, organization, repository, team, csrf).

### Fixtures

```typescript
authenticatedPage    // Logged in as testuser
authenticatedRequest // API context with auth
superuserPage        // Logged in as admin
quayConfig           // Quay configuration
uniqueName(prefix)   // Generate unique names
skipUnlessFeature()  // Feature gate helper
```

### Mock Policy

**Do NOT mock. The only acceptable mock is error responses (4xx/5xx).**

| Scenario | Solution |
|----------|----------|
| Feature-dependent behavior | `test.skip(...skipUnlessFeature(quayConfig, 'FEATURE'))` |
| Need specific data state | Create real data via API utilities |
| Test error handling | `page.route()` with error status (only exception) |
| Wait for API response | Remove - Playwright auto-waits |

### Common Pitfalls

- Forget `await` keywords
- Use hardcoded names instead of `uniqueName()`
- Skip cleanup in `afterEach` or at end of test
- Mock when you should use `skipUnlessFeature()`
- Use framework-specific selectors (#pf-tab-0)
- Forget to add `superuserRequest` fixture for user deletion
