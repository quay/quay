import {test, expect} from '../../fixtures';

test.describe(
  'Read-only Superuser Repository Visibility',
  {tag: ['@feature:SUPERUSERS_FULL_ACCESS', '@repository', '@PROJQUAY-6631']},
  () => {
    test('can see repositories from all organizations on top-level repos page', async ({
      readonlyPage,
      api,
    }) => {
      // Setup: regular user creates org + repo (readonly superuser is NOT a member)
      const org = await api.organization('readonly-test');
      const repo = await api.repository(org.name, 'visible-repo');

      // Navigate to top-level Repositories page as readonly superuser
      await readonlyPage.goto('/repository');

      // Assert: repo from other user's org is visible
      await expect(readonlyPage.getByText(repo.fullName)).toBeVisible({
        timeout: 15000,
      });
    });

    test('can view repositories inside an org they are not a member of', async ({
      readonlyPage,
      api,
    }) => {
      // Setup: create org + repo as regular user
      const org = await api.organization('drill-test');
      const repo = await api.repository(org.name, 'drill-repo');

      // Navigate into the org as readonly superuser
      await readonlyPage.goto(`/organization/${org.name}`);

      // Assert: repo is visible in the org's repo list
      await expect(readonlyPage.getByText(repo.name)).toBeVisible({
        timeout: 15000,
      });
    });

    test('cannot create or delete repositories', async ({
      readonlyPage,
      api,
    }) => {
      const org = await api.organization('nowrite-test');
      await api.repository(org.name, 'nowrite-repo');

      // Navigate to org's repo list
      await readonlyPage.goto(`/organization/${org.name}`);

      // Wait for repos to load
      await expect(readonlyPage.getByText('nowrite-repo')).toBeVisible({
        timeout: 15000,
      });

      // Assert: no "Create Repository" button visible
      await expect(
        readonlyPage.getByRole('button', {name: /create repository/i}),
      ).not.toBeVisible();

      // Assert: no selection checkboxes (row selection is hidden for readonly)
      // Scope to the active tab panel to avoid matching checkboxes from hidden tabs
      await expect(
        readonlyPage.locator(
          '[role="tabpanel"]:not([hidden]) input[type="checkbox"]',
        ),
      ).toHaveCount(0);
    });
  },
);
