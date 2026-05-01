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

    test.beforeEach(async ({authenticatedPage}) => {
      // Navigate to the page
      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);

      // Wait for the tag to appear in the table
      await expect(
        authenticatedPage.getByText('v1.0', {exact: true}),
      ).toBeVisible();

      // Find and expand the manifest list row
      const tagRow = authenticatedPage
        .getByTestId('table-entry')
        .filter({has: authenticatedPage.getByText('v1.0', {exact: true})});

      // Click the expand button (first button in the row)
      await tagRow.getByRole('button').first().click();

      // Wait for child manifests to appear after expansion
      await expect(
        authenticatedPage.getByText(/linux on (amd64|arm64)/).first(),
      ).toBeVisible();
    });

    test('displays image built timestamp for child manifests', async ({
      authenticatedPage,
    }) => {
      // We are already expanded so we just find the child row
      const childRow = authenticatedPage
        .getByRole('row')
        .filter({hasText: /linux on (amd64|arm64)/})
        .first();

      // Find the Image Built cell using data-label attribute
      const imageBuiltCell = childRow.locator('[data-label="Image Built"]');

      // Verify the timestamp is visible and contains a date (not n/a)
      await expect(imageBuiltCell).toBeVisible();
      await expect(imageBuiltCell).toContainText(
        /[A-Z][a-z]{2}\s\d{1,2},\s\d{4}/,
      );
      await expect(imageBuiltCell).not.toHaveText(/n\/a/i);
    });

    test('displays platform correctly (not "unknown on unknown")', async ({
      authenticatedPage,
    }) => {
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
