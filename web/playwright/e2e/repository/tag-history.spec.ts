import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {pushImage} from '../../utils/container';

test.describe(
  'Repository Details - Tag History',
  {tag: ['@tags', '@repository', '@container']},
  () => {
    let sharedRepo: {namespace: string; name: string; fullName: string};

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      if (!cachedContainerAvailable) return;

      const api = new ApiClient(userContext.request);
      const repoName = `tag-history-${Date.now()}`;
      await api.createRepository(TEST_USERS.user.username, repoName, 'private');

      sharedRepo = {
        namespace: TEST_USERS.user.username,
        name: repoName,
        fullName: `${TEST_USERS.user.username}/${repoName}`,
      };

      // Push initial image as 'latest'
      await pushImage(
        sharedRepo.namespace,
        sharedRepo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Poll for the tag to be indexed (push is sync but indexing may lag)
      let latestDigest: string | undefined;
      for (let attempt = 0; attempt < 10; attempt++) {
        const tags = await api.getTags(sharedRepo.namespace, sharedRepo.name, {
          specificTag: 'latest',
        });
        if (tags.tags.length > 0) {
          latestDigest = tags.tags[0].manifest_digest;
          break;
        }
        await new Promise((r) => setTimeout(r, 1000));
      }
      if (!latestDigest) {
        throw new Error('Pushed tag was not indexed after 10 attempts');
      }

      // Create additional tag 'histtag' pointing to same digest
      await api.createTag(
        sharedRepo.namespace,
        sharedRepo.name,
        'histtag',
        latestDigest,
      );

      // Delete 'histtag' to create a "deleted" history entry
      await api.deleteTag(sharedRepo.namespace, sharedRepo.name, 'histtag');

      // Set expiration on 'latest' to 2 weeks from now (for future entries test)
      const twoWeeksFromNow = Math.floor(Date.now() / 1000) + 14 * 24 * 60 * 60;
      await api.setTagExpiration(
        sharedRepo.namespace,
        sharedRepo.name,
        'latest',
        twoWeeksFromNow,
      );
    });

    test.afterAll(async ({userContext}) => {
      if (!sharedRepo) return;
      const api = new ApiClient(userContext.request);
      try {
        await api.deleteRepository(sharedRepo.namespace, sharedRepo.name);
      } catch {
        // Ignore cleanup errors
      }
    });

    test('renders history list with tag changes', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(
        `/repository/${sharedRepo.fullName}?tab=tags`,
      );
      await authenticatedPage.getByText('Tag history').click();

      const historyTable = authenticatedPage.locator('#tag-history-table');
      await expect(historyTable).toBeVisible();

      const rows = historyTable.locator('tbody tr');
      const rowCount = await rows.count();
      expect(rowCount).toBeGreaterThan(0);

      const firstRow = rows.first();
      await expect(firstRow.locator('[data-label="tag-change"]')).toBeVisible();
      await expect(
        firstRow.locator('[data-label="date-modified"]'),
      ).toBeVisible();

      await expect(historyTable).toContainText('latest');
    });

    test('search history by tag name', async ({authenticatedPage}) => {
      await authenticatedPage.goto(
        `/repository/${sharedRepo.fullName}?tab=tags`,
      );
      await authenticatedPage.getByText('Tag history').click();

      await authenticatedPage
        .getByPlaceholder('Search by tag name...')
        .fill('histtag');

      const historyTable = authenticatedPage.locator('#tag-history-table');
      const rows = historyTable.locator('tbody tr');
      const count = await rows.count();
      expect(count).toBeGreaterThan(0);
      for (let i = 0; i < count; i++) {
        await expect(
          rows.nth(i).locator('[data-label="tag-change"]'),
        ).toContainText('histtag');
      }
    });

    test('show future entries toggle', async ({authenticatedPage}) => {
      await authenticatedPage.goto(
        `/repository/${sharedRepo.fullName}?tab=tags`,
      );
      await authenticatedPage.getByText('Tag history').click();

      // Future entries hidden by default
      await expect(
        authenticatedPage.getByText(/latest will expire/),
      ).not.toBeAttached();

      // Toggle to show future entries
      await authenticatedPage.locator('#show-future-checkbox').click();
      await expect(
        authenticatedPage.getByText(/latest will expire/),
      ).toBeVisible();
    });

    test('filter by date range', async ({authenticatedPage}) => {
      await authenticatedPage.goto(
        `/repository/${sharedRepo.fullName}?tab=tags`,
      );
      await authenticatedPage.getByText('Tag history').click();
      await authenticatedPage.locator('#show-future-checkbox').click();

      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const startDateStr = yesterday.toISOString().split('T')[0];

      await authenticatedPage
        .locator('#start-time-picker')
        .locator('input[aria-label="Date picker"]')
        .fill(startDateStr);

      const historyTable = authenticatedPage.locator('#tag-history-table');
      const rows = historyTable.locator('tbody tr');
      const count = await rows.count();
      expect(count).toBeGreaterThan(0);

      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const endDateStr = tomorrow.toISOString().split('T')[0];

      await authenticatedPage
        .locator('#end-time-picker')
        .locator('input[aria-label="Date picker"]')
        .fill(endDateStr);

      const filteredCount = await rows.count();
      expect(filteredCount).toBeGreaterThan(0);
    });

    test('revert tag to previous digest', async ({authenticatedPage, api}) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'revtag',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Delete the tag to create a restorable history entry
      const rawApi = api.raw;
      await rawApi.deleteTag(repo.namespace, repo.name, 'revtag');

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await authenticatedPage.getByRole('tab', {name: 'Tag history'}).click();

      // Wait for history table to load
      const historyTable = authenticatedPage.locator('#tag-history-table');
      await expect(historyTable).toBeVisible();
      await expect(historyTable).toContainText('revtag was deleted');

      // Click Restore link
      const restoreLink = authenticatedPage.getByText(/Restore to/);
      await expect(restoreLink.first()).toBeVisible();
      await restoreLink.first().click();

      await expect(
        authenticatedPage.getByText('Restore Tag', {exact: true}),
      ).toBeVisible();

      await authenticatedPage
        .getByRole('button', {name: 'Restore tag'})
        .click();
      await expect(
        authenticatedPage.getByText(/Restored tag .* successfully/),
      ).toBeVisible();
    });

    test('permanently delete historical tag', async ({
      authenticatedPage,
      api,
      quayConfig,
    }) => {
      test.skip(
        !quayConfig.config?.PERMANENTLY_DELETE_TAGS,
        'PERMANENTLY_DELETE_TAGS not enabled',
      );

      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'testdelete',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Delete the tag via API to create a dead history entry
      const rawApi = api.raw;
      await rawApi.deleteTag(repo.namespace, repo.name, 'testdelete');

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await authenticatedPage.getByRole('tab', {name: 'Tag history'}).click();

      const historyTable = authenticatedPage.locator('#tag-history-table');
      await expect(historyTable).toBeVisible();
      await expect(historyTable).toContainText('testdelete was deleted');

      // The permanent delete button is in the Revert column for dead tags
      // It shows as "Delete <tagname> <digest>" link
      const deleteLink = historyTable.getByText(/Delete testdelete/);
      await expect(deleteLink.first()).toBeVisible();
      await deleteLink.first().click();

      await expect(
        authenticatedPage.getByText('Permanently Delete Tag', {exact: true}),
      ).toBeVisible();

      await authenticatedPage
        .getByRole('button', {name: 'Permanently delete tag'})
        .click();

      await expect(
        authenticatedPage.getByText(/Permanently deleted tag testdelete/),
      ).toBeVisible();
    });

    test('non-writable repo hides revert and delete actions', async ({
      readonlyPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // View history as readonly user
      await readonlyPage.goto(`/repository/${repo.fullName}?tab=history`);

      await expect(readonlyPage.getByText(/latest was created/)).toBeVisible();

      // Verify no revert or delete actions visible
      await expect(readonlyPage.getByText('Restore to')).not.toBeAttached();
      await expect(
        readonlyPage.getByText('Permanently delete'),
      ).not.toBeAttached();
    });
  },
);
