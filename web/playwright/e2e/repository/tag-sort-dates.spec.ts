import {test, expect, getTestUsers} from '../../fixtures';
import {ApiClient} from '../../utils/api';
import {pushImage} from '../../utils/container';

test.describe(
  'Repository Details - Tag Date Column Sorting (PROJQUAY-11351)',
  {tag: ['@tags', '@repository', '@container']},
  () => {
    let user: {username: string; password: string};

    test.beforeAll(({cachedQuayConfig}) => {
      user = getTestUsers(cachedQuayConfig).user;
    });

    let repo: {namespace: string; name: string; fullName: string};

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      test.setTimeout(180000);
      if (!cachedContainerAvailable) return;

      const api = new ApiClient(userContext.request);
      const repoName = `tag-sort-dates-${Date.now()}`;
      await api.createRepository(user.username, repoName, 'private');

      repo = {
        namespace: user.username,
        name: repoName,
        fullName: `${user.username}/${repoName}`,
      };

      const ensureDistinctTimestamp = () =>
        new Promise((resolve) => setTimeout(resolve, 1100));

      await pushImage(
        repo.namespace,
        repo.name,
        'first',
        user.username,
        user.password,
      );
      await ensureDistinctTimestamp();
      await pushImage(
        repo.namespace,
        repo.name,
        'second',
        user.username,
        user.password,
      );
      await ensureDistinctTimestamp();
      await pushImage(
        repo.namespace,
        repo.name,
        'third',
        user.username,
        user.password,
      );
    });

    test.afterAll(async ({userContext}) => {
      if (!repo) return;
      const api = new ApiClient(userContext.request);
      try {
        await api.deleteRepository(repo.namespace, repo.name);
      } catch {
        // Ignore cleanup errors
      }
    });

    test('Last Modified column sorts tags chronologically', async ({
      authenticatedPage,
      cachedContainerAvailable,
    }) => {
      test.skip(
        !cachedContainerAvailable,
        'Requires cached container image to push test tags',
      );
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      // Wait for all 3 tags to render
      await expect(
        authenticatedPage.getByRole('link', {name: 'first'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'second'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'third'}),
      ).toBeVisible();

      // Get the sort button for "Last Modified" column header
      const lastModifiedHeader = authenticatedPage.getByRole('button', {
        name: /Last Modified/,
      });

      // Click to sort ascending (oldest first)
      await lastModifiedHeader.click();

      // Get all tag names in display order
      let tagNames = await authenticatedPage
        .getByTestId('table-entry')
        .locator('[data-label="Tag"] a')
        .allTextContents();

      // In ascending order, "first" (earliest) should come before "third" (latest)
      const firstIdxAsc = tagNames.indexOf('first');
      const secondIdxAsc = tagNames.indexOf('second');
      const thirdIdxAsc = tagNames.indexOf('third');
      expect(firstIdxAsc).toBeLessThan(secondIdxAsc);
      expect(secondIdxAsc).toBeLessThan(thirdIdxAsc);

      // Click again to sort descending (newest first)
      await lastModifiedHeader.click();

      tagNames = await authenticatedPage
        .getByTestId('table-entry')
        .locator('[data-label="Tag"] a')
        .allTextContents();

      const firstIdxDesc = tagNames.indexOf('first');
      const secondIdxDesc = tagNames.indexOf('second');
      const thirdIdxDesc = tagNames.indexOf('third');
      expect(thirdIdxDesc).toBeLessThan(secondIdxDesc);
      expect(secondIdxDesc).toBeLessThan(firstIdxDesc);
    });
  },
);
