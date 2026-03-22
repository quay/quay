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

      // Find row
      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({has: authenticatedPage.getByText('v1.0', {exact: true})});

      // Expand row
      await expect(tagRow).toBeVisible();
      await tagRow.getByRole('button', {name: /toggle row/i}).click();
    });

    test('displays image built timestamp for child manifests', async ({
      authenticatedPage,
    }) => {
      // We are already expanded so we just find the child row
      const childRow = authenticatedPage
        .getByRole('row')
        .filter({hasText: /linux on (amd64|arm64)/})
        .first();

      // find the cell with the timestamp
      const imageBuiltCell = childRow
        .getByRole('cell')
        .filter({hasText: /[A-Z][a-z]{2}\s\d{1,2},\s\d{4}/});

      await expect(imageBuiltCell).toBeVisible();
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
