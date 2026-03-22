import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {pushImage} from '../../utils/container';

test.describe(
  'Tags - Image Built Timestamp',
  {tag: ['@tags', '@container']},
  () => {
    let testRepo: {namespace: string; name: string; fullName: string};
    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      if (!cachedContainerAvailable) return;
      const api = new ApiClient(userContext.request);
      const repoName = `image-built-${Date.now()}`;
      await api.createRepository(TEST_USERS.user.username, repoName, 'private');

      testRepo = {
        namespace: TEST_USERS.user.username,
        name: repoName,
        fullName: `${TEST_USERS.user.username}/${repoName}`,
      };

      // push test image
      await pushImage(
        testRepo.namespace,
        testRepo.name,
        'latest',
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

    test('displays image built timestamp column', async ({
      authenticatedPage,
    }) => {
      // Load the page
      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);

      // Wait for the latest tag to appear
      const latestTagLink = authenticatedPage.getByRole('link', {
        name: 'latest',
        exact: true,
      });
      await expect(latestTagLink).toBeVisible();

      // Find row that contains the latest tag
      const targetRow = authenticatedPage
        .getByRole('row')
        .filter({has: latestTagLink});

      // Target the image built cell. 'Image Built' column should be column 4 in the output.
      const imageBuiltCell = targetRow.getByRole('cell').nth(4);

      // Verify that the timestamp is visible
      await expect(imageBuiltCell).toBeVisible();
      await expect(imageBuiltCell).not.toHaveText(/n\/a/i);
    });
  },
);
