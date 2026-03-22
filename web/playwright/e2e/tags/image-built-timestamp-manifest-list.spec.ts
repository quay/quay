import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {pushMultiArchImage} from '../../utils/container';

test.describe(
  'Tags - Manifest List Child Timestamps',
  {tag: ['@tags', '@container']},
  () => {
    let testRepo: {namespace: string; name: string; fullName: string};

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      if (!cachedContainerAvailable) return;
      const api = new ApiClient(userContext.request);
      const repoName = `manifest-list-${Date.now()}`;
      await api.createRepository(TEST_USERS.user.username, repoName, 'private');

      testRepo = {
        namespace: TEST_USERS.user.username,
        name: repoName,
        fullName: `${TEST_USERS.user.username}/${repoName}`,
      };

      // Push multi-arch image
      await pushMultiArchImage(
        testRepo.namespace,
        testRepo.name,
        'v1.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
    });

    test.afterAll(async ({userContext}) => {
      if (!testRepo) return;
      const api = new ApiClient(userContext.request);
      try {
        await api.deleteRepository(testRepo.namespace, testRepo.name);
      } catch {
        // ignore cleanup errors
      }
    });

    test('displays image built timestamp for child manifests', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);

      // Find manifest list row
      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({hasText: 'v1.0'});
      await expect(tagRow).toBeVisible();

      // expand the row
      const expandButton = tagRow.getByRole('button', {name: /toggle row/i});
      await expandButton.click();

      // wait for child manifests to be visible
      const childManifest = authenticatedPage.getByText(
        /linux on (amd64|arm64)/,
      );
      await expect(childManifest.first()).toBeVisible();

      // verify that timestamps are showing
      const expandedRows = authenticatedPage.locator(
        'tr[class*="pf-m-expanded"]',
      );
      const firstExpandedRow = expandedRows.first();

      // look for a timestamp pattern
      const imageBuiltText = await firstExpandedRow
        .locator('td')
        .filter({hasText: /\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}/})
        .textContent();

      expect(imageBuiltText).toBeTruthy();
      expect(imageBuiltText).not.toBe('n/a');
    });

    test('displays platform correctly (not "unknown on unknown")', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);

      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({hasText: 'v1.0'});
      const expandButton = tagRow.getByRole('button', {name: /toggle row/i});
      await expandButton.click();

      // verify platform shows correctly
      const platformText = authenticatedPage.getByText(
        /linux on (amd64|arm64)/,
      );
      await expect(platformText.first()).toBeVisible();

      // verify "unknown on unknown" is not shown
      const unknownPlatform = authenticatedPage.getByText('unknown on unknown');
      await expect(unknownPlatform).not.toBeVisible();
    });
  },
);
