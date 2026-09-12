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

import path from 'path';
import {APIRequestContext} from '@playwright/test';
import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {getV2Token} from '../../utils/api/auth';
import {API_URL} from '../../utils/config';
import {
  pushImage,
  pushMultiArchImage,
  pushUniqueImage,
  orasAttach,
  isOrasAvailable,
} from '../../utils/container';

/**
 * Creates a Cosign tag-schema `.sig` tag for an image tag
 * (`sha256-<hex>.sig` pointing at the image digest).
 */
async function createCosignSigTag(
  api: ApiClient,
  namespace: string,
  repo: string,
  imageTag: string,
): Promise<string> {
  const tags = await api.getTags(namespace, repo, {specificTag: imageTag});
  if (tags.tags.length === 0) {
    throw new Error(`Tag ${imageTag} not found in ${namespace}/${repo}`);
  }
  const digest = tags.tags[0].manifest_digest;
  const sigName = `${digest.replace(':', '-')}.sig`;
  await api.createTag(namespace, repo, sigName, digest);
  return sigName;
}

async function countReferrers(
  request: APIRequestContext,
  token: string,
  namespace: string,
  repo: string,
  digest: string,
): Promise<number> {
  const response = await request.get(
    `${API_URL}/v2/${namespace}/${repo}/referrers/${digest}`,
    {headers: {authorization: `Bearer ${token}`}},
  );
  if (!response.ok()) {
    const body = await response.text();
    throw new Error(
      `Failed to list referrers for ${digest}: ${response.status()} - ${body}`,
    );
  }
  const body = await response.json();
  return body.manifests?.length ?? 0;
}

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

    test(
      'tag-count pruning excludes cosign .sig tags and cascades on prune',
      {tag: '@PROJQUAY-11682'},
      async ({api}) => {
        test.slow();
        const org = await api.organization('prunesigcnt');
        const repo = await api.repository(org.name, 'prunetest');

        // Unique digests so each image tag gets a distinct Cosign .sig name
        await pushUniqueImage(
          org.name,
          repo.name,
          'v1',
          user.username,
          user.password,
        );
        await pushUniqueImage(
          org.name,
          repo.name,
          'v2',
          user.username,
          user.password,
        );

        const sigV1 = await createCosignSigTag(
          api.raw,
          org.name,
          repo.name,
          'v1',
        );
        const sigV2 = await createCosignSigTag(
          api.raw,
          org.name,
          repo.name,
          'v2',
        );
        expect(sigV1).not.toBe(sigV2);

        const tagsBefore = await api.raw.getTags(org.name, repo.name);
        expect(tagsBefore.tags).toHaveLength(4);

        await api.repoAutoPrunePolicy(org.name, repo.name, {
          method: 'number_of_tags',
          value: 1,
        });

        // Keep-1 only counts image tags: prune v1 (and cascade its .sig), keep v2 + .sig
        await expect(async () => {
          const tags = await api.raw.getTags(org.name, repo.name);
          const names = tags.tags.map((t) => t.name);
          expect(names).toContain('v2');
          expect(names).toContain(sigV2);
          expect(names).not.toContain('v1');
          expect(names).not.toContain(sigV1);
          expect(tags.tags).toHaveLength(2);
        }).toPass({timeout: 120_000, intervals: [5_000]});
      },
    );

    test(
      'creation-date pruning does not age-prune cosign .sig tags',
      {tag: '@PROJQUAY-11682'},
      async ({api}) => {
        test.slow();
        const org = await api.organization('prunesigage');
        const repo = await api.repository(org.name, 'prunetest');

        await pushImage(
          org.name,
          repo.name,
          'v1',
          user.username,
          user.password,
        );
        const sigName = await createCosignSigTag(
          api.raw,
          org.name,
          repo.name,
          'v1',
        );

        const v1Tags = await api.raw.getTags(org.name, repo.name, {
          specificTag: 'v1',
        });
        const digest = v1Tags.tags[0].manifest_digest;

        // Age both tags past the upcoming 60s policy threshold
        await new Promise((r) => setTimeout(r, 70_000));

        // Refresh only the image tag so it is young; .sig stays old
        await api.raw.createTag(org.name, repo.name, 'v1', digest);

        await api.repoAutoPrunePolicy(org.name, repo.name, {
          method: 'creation_date',
          value: '60s',
        });

        // One prune cycle: .sig (~115s) would age-prune without exclusion;
        // refreshed v1 (~45s) stays under the 60s threshold
        await new Promise((r) => setTimeout(r, 45_000));

        const tags = await api.raw.getTags(org.name, repo.name);
        const names = tags.tags.map((t) => t.name);
        expect(names).toContain('v1');
        expect(names).toContain(sigName);
      },
    );

    test(
      'autoprune of last subject tag allows Cosign V3 referrer GC',
      {tag: ['@PROJQUAY-12396', '@container']},
      async ({api, playwright}) => {
        test.slow();
        test.skip(
          !(await isOrasAvailable()),
          'oras CLI required for referrer attach',
        );

        const org = await api.organization('pruneref');
        const repo = await api.repository(org.name, 'prunetest');

        // Single subject tag so prune removes the last visible alias
        await pushImage(
          org.name,
          repo.name,
          'v1',
          user.username,
          user.password,
        );

        const v1Tags = await api.raw.getTags(org.name, repo.name, {
          specificTag: 'v1',
        });
        expect(v1Tags.tags.length).toBeGreaterThan(0);
        const digest = v1Tags.tags[0].manifest_digest;

        const fixturesDir = path.resolve(__dirname, '../../fixtures/oras');
        orasAttach(
          org.name,
          repo.name,
          'v1',
          user.username,
          user.password,
          'application/spdx+json',
          'producer=syft 0.63.0',
          path.join(fixturesDir, 'referrer.spdx.json'),
        );

        const request = await playwright.request.newContext({
          ignoreHTTPSErrors: true,
        });
        try {
          const scope = `repository:${org.name}/${repo.name}:pull,push`;
          const v2Token = await getV2Token(
            request,
            API_URL,
            user.username,
            user.password,
            scope,
          );

          await expect
            .poll(
              async () =>
                countReferrers(request, v2Token, org.name, repo.name, digest),
              {
                message: 'Waiting for ORAS referrer to appear',
                timeout: 30_000,
                intervals: [500, 1_000, 2_000],
              },
            )
            .toBe(1);

          await api.repoAutoPrunePolicy(org.name, repo.name, {
            method: 'creation_date',
            value: '10s',
          });

          // Autoprune removes the last subject tag
          await expect(async () => {
            const tags = await api.raw.getTags(org.name, repo.name);
            expect(tags.tags).toHaveLength(0);
          }).toPass({timeout: 180_000, intervals: [10_000]});

          // Temp-tag expiry unblocks GC of the referrer manifest
          await expect
            .poll(
              async () =>
                countReferrers(request, v2Token, org.name, repo.name, digest),
              {
                message: 'Waiting for referrer GC after subject autoprune',
                timeout: 240_000,
                intervals: [10_000],
              },
            )
            .toBe(0);
        } finally {
          await request.dispose();
        }
      },
    );
  },
);
