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
      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);
      // Verify that column header exists
      await expect(
        authenticatedPage.getByRole('columnheader', {name: `Image Built`}),
      ).toBeVisible();

      // Verify at least one tag shows a built timestamp (not n/a)
      // The pushed image should have a built timestamp from Docker
      const imageBuiltCell = authenticatedPage
        .getByRole('row')
        .filter({hasText: 'latest'})
        .getByRole('cell', {name: /Image Built/});

      await expect(imageBuiltCell).toBeVisible();

      // Check that it's not n/a (pushed images from Docker should have a timestamp)
      const cellText = await imageBuiltCell.textContent();
      expect(cellText).not.toBe('N/A');
    });
  },
);
