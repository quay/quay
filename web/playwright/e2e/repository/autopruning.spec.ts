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
import {TEST_USERS} from '../../global-setup';
import {pushImage, pushMultiArchImage} from '../../utils/container';

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
      const firstForm = authenticatedPage.locator('#autoprune-policy-form-0');
      // Wait for form to be fully loaded before interacting
      await expect(firstForm.getByTestId('auto-prune-method')).toBeVisible();
      await expect(firstForm.getByTestId('auto-prune-method')).toContainText(
        'None',
      );
      await firstForm
        .getByTestId('auto-prune-method')
        .selectOption('number_of_tags');

      // Wait for input to appear and have default value
      const tagCountInput = firstForm.locator(
        'input[aria-label="number of tags"]',
      );
      await expect(tagCountInput).toHaveValue('20');

      await tagCountInput.fill('25');

      await firstForm.getByRole('button', {name: 'Save'}).click();

      // Wait for success message to appear then disappear
      await expect(
        authenticatedPage.getByText(
          'Successfully created repository auto-prune policy',
        ),
      ).toBeVisible();
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
      const secondFormCreate = authenticatedPage.locator(
        '#autoprune-policy-form-1',
      );
      await secondFormCreate
        .getByTestId('auto-prune-method')
        .selectOption('creation_date');
      await secondFormCreate
        .locator('input[aria-label="tag creation date value"]')
        .fill('2');
      await secondFormCreate
        .locator('select[aria-label="tag creation date unit"]')
        .selectOption('w');
      await secondFormCreate.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText(
          'Successfully created repository auto-prune policy',
        ),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(
          'Successfully created repository auto-prune policy',
        ),
      ).not.toBeVisible({timeout: 10000});

      // UPDATE: Find the form that has "By age of tags" (creation_date)
      // After refetch, policy order from the API is non-deterministic,
      // so locate the form by the presence of the creation date input
      // (only visible when method is "creation_date"), get its ID, then
      // use a stable locator since changing method hides the date input
      const creationDateFormEl = authenticatedPage
        .locator('form[id^="autoprune-policy-form-"]')
        .filter({
          has: authenticatedPage.locator(
            'input[aria-label="tag creation date value"]',
          ),
        });
      const formId = await creationDateFormEl.getAttribute('id');
      const updateForm = authenticatedPage.locator(`#${formId}`);
      await updateForm
        .getByTestId('auto-prune-method')
        .selectOption('number_of_tags');
      await updateForm.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText(
          'Successfully updated repository auto-prune policy',
        ),
      ).toBeVisible();

      // After update, both policies are now "By number of tags".
      // Verify we have two forms with tag count inputs: one with 25, one with 20.
      // Use polling because the API refetch may reorder policies,
      // causing React to re-render form values asynchronously.
      const tagCountInputs = authenticatedPage.locator(
        'input[aria-label="number of tags"]',
      );
      await expect(tagCountInputs).toHaveCount(2);
      await expect(async () => {
        const values = await tagCountInputs.evaluateAll(
          (inputs: HTMLInputElement[]) => inputs.map((i) => i.value).sort(),
        );
        expect(values).toEqual(['20', '25']);
      }).toPass({timeout: 10000});

      await expect(
        authenticatedPage.getByText(
          'Successfully updated repository auto-prune policy',
        ),
      ).not.toBeVisible({timeout: 10000});

      // DELETE one of the policies - just delete from the last form
      // (order doesn't matter, we just need to verify deletion works)
      const lastForm = authenticatedPage
        .locator('form[id^="autoprune-policy-form-"]')
        .last();
      await lastForm.getByTestId('auto-prune-method').selectOption('none');
      await lastForm.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText(
          'Successfully deleted repository auto-prune policy',
        ),
      ).toBeVisible();

      // Should only have one form left
      await expect(
        authenticatedPage.locator('form[id^="autoprune-policy-form-"]'),
      ).toHaveCount(1);

      await expect(
        authenticatedPage.getByText(
          'Successfully deleted repository auto-prune policy',
        ),
      ).not.toBeVisible({timeout: 10000});

      // DELETE REMAINING POLICY
      const remainingForm = authenticatedPage.locator(
        '#autoprune-policy-form-0',
      );
      await remainingForm.getByTestId('auto-prune-method').selectOption('none');
      await remainingForm.getByRole('button', {name: 'Save'}).click();

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

test.describe(
  'Repository Auto-Prune Functional Verification',
  {tag: ['@repository', '@feature:AUTO_PRUNE', '@container']},
  () => {
    const user = TEST_USERS.user;

    test('repo-level tag-count pruning removes excess tags', async ({api}) => {
      test.slow();
      const org = await api.organization('repoprunecnt');
      const repo = await api.repository(org.name, 'prunetest');

      await pushImage(org.name, repo.name, 'v1', user.username, user.password);
      await pushImage(org.name, repo.name, 'v2', user.username, user.password);

      const tagsBefore = await api.raw.getTags(org.name, repo.name);
      expect(tagsBefore.tags).toHaveLength(2);

      await api.repoAutoPrunePolicy(org.name, repo.name, {
        method: 'number_of_tags',
        value: 1,
      });

      await expect(async () => {
        const tags = await api.raw.getTags(org.name, repo.name);
        expect(tags.tags).toHaveLength(1);
        expect(tags.tags[0].name).toBe('v2');
      }).toPass({timeout: 120_000, intervals: [5_000]});
    });

    test('repo-level time-based pruning removes old tags', async ({api}) => {
      test.slow();
      const org = await api.organization('repopruneage');
      const repo = await api.repository(org.name, 'prunetest');

      await pushImage(org.name, repo.name, 'v1', user.username, user.password);

      await api.repoAutoPrunePolicy(org.name, repo.name, {
        method: 'creation_date',
        value: '10s',
      });

      await expect(async () => {
        const tags = await api.raw.getTags(org.name, repo.name);
        expect(tags.tags).toHaveLength(0);
      }).toPass({timeout: 180_000, intervals: [10_000]});
    });

    test('auto-pruning does not affect mirror repos', async ({api}) => {
      test.slow();
      const org = await api.organization('prunemirror');
      const normalRepo = await api.repository(org.name, 'normalrepo');
      const mirrorRepo = await api.repository(org.name, 'mirrorrepo');

      await pushImage(
        org.name,
        mirrorRepo.name,
        'v1',
        user.username,
        user.password,
      );
      await pushImage(
        org.name,
        mirrorRepo.name,
        'v2',
        user.username,
        user.password,
      );

      await api.raw.changeRepositoryState(org.name, mirrorRepo.name, 'MIRROR');

      await pushImage(
        org.name,
        normalRepo.name,
        'v1',
        user.username,
        user.password,
      );
      await pushImage(
        org.name,
        normalRepo.name,
        'v2',
        user.username,
        user.password,
      );

      await api.orgAutoPrunePolicy(org.name, {
        method: 'number_of_tags',
        value: 1,
      });

      // Normal repo should get pruned
      await expect(async () => {
        const tags = await api.raw.getTags(org.name, normalRepo.name);
        expect(tags.tags).toHaveLength(1);
      }).toPass({timeout: 120_000, intervals: [5_000]});

      // Mirror repo should retain both tags
      const mirrorTags = await api.raw.getTags(org.name, mirrorRepo.name);
      expect(mirrorTags.tags).toHaveLength(2);
    });

    test('multi-arch image pruning by tag count', async ({api}) => {
      test.slow();
      const org = await api.organization('prunearch');
      const repo = await api.repository(org.name, 'prunetest');

      await pushMultiArchImage(
        org.name,
        repo.name,
        'v1',
        user.username,
        user.password,
      );
      await pushMultiArchImage(
        org.name,
        repo.name,
        'v2',
        user.username,
        user.password,
      );

      await api.orgAutoPrunePolicy(org.name, {
        method: 'number_of_tags',
        value: 1,
      });

      await expect(async () => {
        const tags = await api.raw.getTags(org.name, repo.name);
        const activeNames = tags.tags.map((t) => t.name);
        expect(activeNames).not.toContain('v1');
        expect(activeNames).toContain('v2');
      }).toPass({timeout: 150_000, intervals: [5_000]});
    });

    test('regex tag pattern limits which tags are pruned', async ({api}) => {
      test.slow();
      const org = await api.organization('pruneregex');
      const repo = await api.repository(org.name, 'prunetest');

      await pushImage(
        org.name,
        repo.name,
        'release-1',
        user.username,
        user.password,
      );
      await pushImage(
        org.name,
        repo.name,
        'release-2',
        user.username,
        user.password,
      );
      await pushImage(
        org.name,
        repo.name,
        'dev-1',
        user.username,
        user.password,
      );
      await pushImage(
        org.name,
        repo.name,
        'dev-2',
        user.username,
        user.password,
      );

      await api.repoAutoPrunePolicy(org.name, repo.name, {
        method: 'number_of_tags',
        value: 1,
        tagPattern: '^dev-',
        tagPatternMatches: true,
      });

      await expect(async () => {
        const tags = await api.raw.getTags(org.name, repo.name);
        const names = tags.tags.map((t) => t.name).sort();
        // Both release tags should remain untouched
        expect(names).toContain('release-1');
        expect(names).toContain('release-2');
        // Only the newest dev tag should remain
        expect(names).toContain('dev-2');
        expect(names).not.toContain('dev-1');
      }).toPass({timeout: 120_000, intervals: [5_000]});
    });

    test('multiple repo-level policies coexist without interference', async ({
      api,
    }) => {
      test.slow();
      const org = await api.organization('repomulti');
      const repo = await api.repository(org.name, 'prunetest');

      await pushImage(org.name, repo.name, 'v1', user.username, user.password);
      await pushImage(org.name, repo.name, 'v2', user.username, user.password);

      await api.repoAutoPrunePolicy(org.name, repo.name, {
        method: 'number_of_tags',
        value: 1,
      });
      await api.repoAutoPrunePolicy(org.name, repo.name, {
        method: 'creation_date',
        value: '10s',
      });

      await expect(async () => {
        const tags = await api.raw.getTags(org.name, repo.name);
        expect(tags.tags).toHaveLength(0);
      }).toPass({timeout: 120_000, intervals: [5_000]});
    });

    test('policy removal stops pruning', async ({api}) => {
      test.slow();
      const org = await api.organization('prunestop');
      const repo = await api.repository(org.name, 'prunetest');

      await pushImage(org.name, repo.name, 'v1', user.username, user.password);
      await pushImage(org.name, repo.name, 'v2', user.username, user.password);

      const policy = await api.orgAutoPrunePolicy(org.name, {
        method: 'number_of_tags',
        value: 1,
      });

      // Wait for pruning to take effect
      await expect(async () => {
        const tags = await api.raw.getTags(org.name, repo.name);
        expect(tags.tags).toHaveLength(1);
      }).toPass({timeout: 120_000, intervals: [5_000]});

      // Manually delete the policy mid-test
      await api.raw.deleteOrgAutoPrunePolicy(org.name, policy.uuid);

      // Push new tags — they should not be pruned
      await pushImage(org.name, repo.name, 'v3', user.username, user.password);
      await pushImage(org.name, repo.name, 'v4', user.username, user.password);

      // Wait two pruner cycles, tags should remain
      await new Promise((r) => setTimeout(r, 90_000));
      const tagsAfter = await api.raw.getTags(org.name, repo.name);
      const names = tagsAfter.tags.map((t) => t.name).sort();
      expect(names).toContain('v3');
      expect(names).toContain('v4');
    });

    test('autoprune task status updates succeed without deadlocks (PROJQUAY-11518)', async ({
      api,
    }) => {
      /**
       * Tests that autoprune task status updates handle concurrent operations
       * without database deadlocks.
       *
       * PROJQUAY-11518: Fixed PostgreSQL deadlock in AutoPruneWorker by adding
       * retry logic with exponential backoff to update_autoprune_task().
       *
       * This test verifies the fix by creating multiple autoprune policies across
       * different namespaces and ensuring they all execute successfully. If the
       * deadlock fix were not in place, concurrent task status updates during
       * parallel policy execution would cause transaction conflicts.
       */
      test.slow();
      const user = TEST_USERS.user;

      // Create 3 organizations with repositories and policies
      // This tests concurrent autoprune task updates across namespaces
      const org1 = await api.organization('deadlocktest1');
      const repo1 = await api.repository(org1.name, 'testrepo');
      await pushImage(
        org1.name,
        repo1.name,
        'v1',
        user.username,
        user.password,
      );
      await pushImage(
        org1.name,
        repo1.name,
        'v2',
        user.username,
        user.password,
      );

      const org2 = await api.organization('deadlocktest2');
      const repo2 = await api.repository(org2.name, 'testrepo');
      await pushImage(
        org2.name,
        repo2.name,
        'v1',
        user.username,
        user.password,
      );
      await pushImage(
        org2.name,
        repo2.name,
        'v2',
        user.username,
        user.password,
      );

      const org3 = await api.organization('deadlocktest3');
      const repo3 = await api.repository(org3.name, 'testrepo');
      await pushImage(
        org3.name,
        repo3.name,
        'v1',
        user.username,
        user.password,
      );
      await pushImage(
        org3.name,
        repo3.name,
        'v2',
        user.username,
        user.password,
      );

      // Create autoprune policies for all 3 organizations
      // These will trigger concurrent task status updates
      await api.orgAutoPrunePolicy(org1.name, {
        method: 'number_of_tags',
        value: 1,
      });
      await api.orgAutoPrunePolicy(org2.name, {
        method: 'number_of_tags',
        value: 1,
      });
      await api.orgAutoPrunePolicy(org3.name, {
        method: 'number_of_tags',
        value: 1,
      });

      // Verify all 3 policies execute successfully without deadlock errors
      // The retry logic in update_autoprune_task() should handle any concurrent conflicts
      await expect(async () => {
        const tags1 = await api.raw.getTags(org1.name, repo1.name);
        const tags2 = await api.raw.getTags(org2.name, repo2.name);
        const tags3 = await api.raw.getTags(org3.name, repo3.name);

        // All repos should be pruned to 1 tag (the newest)
        expect(tags1.tags).toHaveLength(1);
        expect(tags2.tags).toHaveLength(1);
        expect(tags3.tags).toHaveLength(1);

        // Only v2 should remain (newest tag)
        expect(tags1.tags[0].name).toBe('v2');
        expect(tags2.tags[0].name).toBe('v2');
        expect(tags3.tags[0].name).toBe('v2');
      }).toPass({timeout: 180_000, intervals: [5_000]});
    });
  },
);
