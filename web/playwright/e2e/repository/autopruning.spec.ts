/**
 * Repository Auto-Prune Policies E2E Tests
 *
 * Tests for repository-level auto-pruning policy management including:
 * - Policy lifecycle (create, update, delete)
 * - Multiple policies management
 * - Tag pattern filtering
 * - Namespace policy display in repository settings
 * - Registry policy display
 * - Error handling
 *
 * Requires AUTO_PRUNE feature to be enabled.
 *
 * Migrated from: web/cypress/e2e/repository-autopruning.cy.ts (17 tests consolidated to 6)
 */

import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

test.describe(
  'Repository Auto-Prune Policies',
  {tag: ['@repository', '@feature:AUTO_PRUNE']},
  () => {
    test('policy lifecycle: create by tag number, update to tag age, delete', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: Create repository (auto-cleaned)
      const repo = await api.repository(undefined, 'autoprunetest');

      // Navigate to repo settings → Auto-Prune Policies
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=settings`);
      await authenticatedPage
        .getByText('Repository Auto-Prune Policies')
        .click();

      // Verify initial state - method should be "None"
      await expect(
        authenticatedPage.getByTestId('auto-prune-method'),
      ).toContainText('None');

      // CREATE: Select "By number of tags" and set value to 25
      await authenticatedPage
        .getByTestId('auto-prune-method')
        .selectOption('number_of_tags');

      const tagCountInput = authenticatedPage.locator(
        'input[aria-label="number of tags"]',
      );
      await expect(tagCountInput).toHaveValue('20');

      // Use triple-click to select all, then fill new value
      await tagCountInput.click({clickCount: 3});
      await tagCountInput.fill('25');

      await authenticatedPage.getByRole('button', {name: 'Save'}).click();

      // Verify creation success
      await expect(
        authenticatedPage.getByText(
          'Successfully created repository auto-prune policy',
        ),
      ).toBeVisible();
      await expect(
        authenticatedPage.locator('input[aria-label="number of tags"]'),
      ).toHaveValue('25');

      // Wait for success message to disappear (ensures form has refetched with uuid)
      await expect(
        authenticatedPage.getByText(
          'Successfully created repository auto-prune policy',
        ),
      ).not.toBeVisible({timeout: 10000});

      // UPDATE: Change to "By age of tags" (2 weeks)
      await authenticatedPage
        .getByTestId('auto-prune-method')
        .selectOption('creation_date');
      await expect(
        authenticatedPage.locator(
          'input[aria-label="tag creation date value"]',
        ),
      ).toHaveValue('7');

      // Change to 2 weeks
      await authenticatedPage
        .locator('input[aria-label="tag creation date value"]')
        .fill('2');
      await authenticatedPage
        .locator('select[aria-label="tag creation date unit"]')
        .selectOption('w');

      await authenticatedPage.getByRole('button', {name: 'Save'}).click();

      // Verify update success
      await expect(
        authenticatedPage.getByText(
          'Successfully updated repository auto-prune policy',
        ),
      ).toBeVisible();
      await expect(
        authenticatedPage.locator(
          'input[aria-label="tag creation date value"]',
        ),
      ).toHaveValue('2');
      await expect(
        authenticatedPage.locator(
          'select[aria-label="tag creation date unit"]',
        ),
      ).toContainText('weeks');

      // Wait for success message to disappear before delete
      await expect(
        authenticatedPage.getByText(
          'Successfully updated repository auto-prune policy',
        ),
      ).not.toBeVisible({timeout: 10000});

      // DELETE: Set method to "None"
      await authenticatedPage
        .getByTestId('auto-prune-method')
        .selectOption('none');
      await authenticatedPage.getByRole('button', {name: 'Save'}).click();

      // Verify deletion success
      await expect(
        authenticatedPage.getByText(
          'Successfully deleted repository auto-prune policy',
        ),
      ).toBeVisible();
    });

    test('creates policy with tag pattern filter', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: Create repository
      const repo = await api.repository(undefined, 'autoprunefilter');

      // Navigate to repo settings → Auto-Prune Policies
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=settings`);
      await authenticatedPage
        .getByText('Repository Auto-Prune Policies')
        .click();

      // Select "By age of tags"
      await authenticatedPage
        .getByTestId('auto-prune-method')
        .selectOption('creation_date');

      // Set to 2 weeks
      await authenticatedPage
        .locator('input[aria-label="tag creation date value"]')
        .fill('2');
      await authenticatedPage
        .locator('select[aria-label="tag creation date unit"]')
        .selectOption('w');

      // Add tag pattern filter
      await authenticatedPage.getByTestId('tag-pattern').fill('v1.*');
      await authenticatedPage
        .locator('select[aria-label="tag pattern matches"]')
        .selectOption('doesnotmatch');

      await authenticatedPage.getByRole('button', {name: 'Save'}).click();

      // Verify success
      await expect(
        authenticatedPage.getByText(
          'Successfully created repository auto-prune policy',
        ),
      ).toBeVisible();
    });

    test('multiple policies lifecycle: create, update, delete', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: Create organization and repository
      const org = await api.organization('multipolicy');
      const repo = await api.repository(org.name, 'testrepo');

      // Navigate to repo settings → Auto-Prune Policies
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=settings`);
      await authenticatedPage
        .getByText('Repository Auto-Prune Policies')
        .click();

      // CREATE FIRST POLICY: By number of tags (25)
      await authenticatedPage
        .getByTestId('auto-prune-method')
        .selectOption('number_of_tags');

      // Wait for input to appear and have default value
      const tagCountInput = authenticatedPage.locator(
        'input[aria-label="number of tags"]',
      );
      await expect(tagCountInput).toHaveValue('20');

      // Use triple-click to select all, then type new value
      await tagCountInput.click({clickCount: 3});
      await tagCountInput.fill('25');

      await authenticatedPage.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText(
          'Successfully created repository auto-prune policy',
        ),
      ).toBeVisible();

      // Wait for success message to disappear before adding second policy
      await expect(
        authenticatedPage.getByText(
          'Successfully created repository auto-prune policy',
        ),
      ).not.toBeVisible({timeout: 10000});

      // ADD SECOND POLICY
      await authenticatedPage.getByRole('button', {name: 'Add Policy'}).click();
      await expect(
        authenticatedPage.locator('#autoprune-policy-form-1'),
      ).toBeVisible();

      // CREATE SECOND POLICY: By age of tags (2 weeks) in second form
      const secondForm = authenticatedPage.locator('#autoprune-policy-form-1');
      await secondForm
        .getByTestId('auto-prune-method')
        .selectOption('creation_date');
      await secondForm
        .locator('input[aria-label="tag creation date value"]')
        .fill('2');
      await secondForm
        .locator('select[aria-label="tag creation date unit"]')
        .selectOption('w');
      await secondForm.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText(
          'Successfully created repository auto-prune policy',
        ),
      ).toBeVisible();

      // Wait for success message to disappear before update
      await expect(
        authenticatedPage.getByText(
          'Successfully created repository auto-prune policy',
        ),
      ).not.toBeVisible({timeout: 10000});

      // UPDATE SECOND POLICY: Change to "By number of tags"
      await secondForm
        .getByTestId('auto-prune-method')
        .selectOption('number_of_tags');
      await secondForm.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText(
          'Successfully updated repository auto-prune policy',
        ),
      ).toBeVisible();
      await expect(
        secondForm.locator('input[aria-label="number of tags"]'),
      ).toHaveValue('20');

      // Wait for success message to disappear before delete
      await expect(
        authenticatedPage.getByText(
          'Successfully updated repository auto-prune policy',
        ),
      ).not.toBeVisible({timeout: 10000});

      // DELETE SECOND POLICY
      await secondForm.getByTestId('auto-prune-method').selectOption('none');
      await secondForm.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText(
          'Successfully deleted repository auto-prune policy',
        ),
      ).toBeVisible();
      await expect(
        authenticatedPage.locator('#autoprune-policy-form-1'),
      ).not.toBeVisible();

      // Wait for success message to disappear before deleting first policy
      await expect(
        authenticatedPage.getByText(
          'Successfully deleted repository auto-prune policy',
        ),
      ).not.toBeVisible({timeout: 10000});

      // DELETE FIRST POLICY
      const firstForm = authenticatedPage.locator('#autoprune-policy-form-0');
      await firstForm.getByTestId('auto-prune-method').selectOption('none');
      await firstForm.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText(
          'Successfully deleted repository auto-prune policy',
        ),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('auto-prune-method'),
      ).toContainText('None');
    });

    test('shows namespace auto-prune policy in repository settings', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: Create organization and repository
      const org = await api.organization('nspolicy');
      const repo = await api.repository(org.name, 'testrepo');

      // Navigate to organization settings → Auto-Prune Policies
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByText('Auto-Prune Policies').click();

      // Create namespace policy: By number of tags (25) with tag pattern
      await authenticatedPage
        .getByTestId('auto-prune-method')
        .selectOption('number_of_tags');
      await authenticatedPage.getByTestId('tag-pattern').fill('v1.*');
      await authenticatedPage
        .locator('select[aria-label="tag pattern matches"]')
        .selectOption('doesnotmatch');
      await authenticatedPage
        .locator('input[aria-label="number of tags"]')
        .press('End');
      await authenticatedPage
        .locator('input[aria-label="number of tags"]')
        .press('Backspace');
      await authenticatedPage
        .locator('input[aria-label="number of tags"]')
        .type('5');
      await authenticatedPage.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText('Successfully created auto-prune policy'),
      ).toBeVisible();

      // Navigate to repository settings → Auto-Prune Policies
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=settings`);
      await authenticatedPage
        .getByText('Repository Auto-Prune Policies')
        .click();

      // Verify namespace policy is displayed (use role selector to avoid matching Registry heading with same testid)
      await expect(
        authenticatedPage.getByRole('heading', {
          name: 'Namespace Auto-Pruning Policies',
        }),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('namespace-autoprune-policy-method'),
      ).toContainText('Number of Tags');
      await expect(
        authenticatedPage.getByTestId('namespace-autoprune-policy-value'),
      ).toContainText('25');
      await expect(
        authenticatedPage.getByTestId('namespace-autoprune-policy-tag-pattern'),
      ).toContainText('v1.*');
      await expect(
        authenticatedPage.getByTestId(
          'namespace-autoprune-policy-tag-pattern-matches',
        ),
      ).toContainText('does not match');
    });

    test('shows registry auto-prune policy when configured', async ({
      authenticatedPage,
      api,
      quayConfig,
    }) => {
      // Skip if registry autoprune policy is not configured
      const hasRegistryPolicy =
        quayConfig?.config?.DEFAULT_NAMESPACE_AUTOPRUNE_POLICY != null;
      test.skip(
        !hasRegistryPolicy,
        'DEFAULT_NAMESPACE_AUTOPRUNE_POLICY not configured',
      );

      // Setup: Create organization and repository
      const org = await api.organization('regpolicy');
      const repo = await api.repository(org.name, 'testrepo');

      // Navigate to repository settings → Auto-Prune Policies
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=settings`);
      await authenticatedPage
        .getByText('Repository Auto-Prune Policies')
        .click();

      // Verify registry policy is displayed
      await expect(
        authenticatedPage.getByTestId('registry-autoprune-policy-method'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('registry-autoprune-policy-value'),
      ).toBeVisible();
    });

    test('displays error when failing to load auto-prune policies', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: Create repository
      const repo = await api.repository(undefined, 'autoprune-error');

      // Mock GET autoprunepolicy with 500 error
      await authenticatedPage.route('**/autoprunepolicy/**', async (route) => {
        if (route.request().method() === 'GET') {
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({error_message: 'Internal server error'}),
          });
        } else {
          await route.continue();
        }
      });

      // Navigate to repo settings → Auto-Prune Policies
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=settings`);
      await authenticatedPage
        .getByText('Repository Auto-Prune Policies')
        .click();

      // Verify error message
      await expect(
        authenticatedPage.getByText('Unable to complete request'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(/unexpected issue occurred/i),
      ).toBeVisible();
    });
  },
);
