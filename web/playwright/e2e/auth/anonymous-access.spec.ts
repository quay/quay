import {test, expect} from '../../fixtures';

test.describe(
  'Anonymous access',
  {
    tag: ['@auth', '@critical', '@feature:ANONYMOUS_ACCESS', '@PROJQUAY-10610'],
  },
  () => {
    test('renders public repository page for unauthenticated user', async ({
      unauthenticatedPage,
      api,
    }) => {
      const org = await api.organization('anon');
      const repo = await api.repository(org.name, 'public', 'public');

      await unauthenticatedPage.goto(`/repository/${repo.fullName}`);

      // Should NOT redirect to /signin
      await expect(unauthenticatedPage).toHaveURL(
        new RegExp(`/repository/${repo.fullName}`),
      );

      // Repo title should be visible on the page
      await expect(unauthenticatedPage.getByTestId('repo-title')).toContainText(
        repo.name,
        {timeout: 10000},
      );

      // Sign In link should be visible instead of user menu
      await expect(
        unauthenticatedPage.getByRole('link', {name: /sign in/i}),
      ).toBeVisible();
      await expect(
        unauthenticatedPage.getByTestId('user-menu-toggle'),
      ).not.toBeVisible();
    });

    test('renders organization list page for unauthenticated user', async ({
      unauthenticatedPage,
    }) => {
      await unauthenticatedPage.goto('/organization');

      // Should render without redirecting to /signin
      await expect(unauthenticatedPage).toHaveURL(/\/organization/);
      await expect(
        unauthenticatedPage.getByRole('heading', {name: /organizations/i}),
      ).toBeVisible({timeout: 10000});
    });

    test('redirects shorthand URL to repository page for unauthenticated user', async ({
      unauthenticatedPage,
      api,
    }) => {
      const org = await api.organization('anon');
      const repo = await api.repository(org.name, 'public', 'public');

      // Use shorthand URL (/:org/:repo instead of /repository/:org/:repo)
      await unauthenticatedPage.goto(`/${org.name}/${repo.name}`);

      // Should redirect to /repository/org/repo (not /signin)
      await expect(unauthenticatedPage).toHaveURL(
        new RegExp(`/repository/${repo.fullName}`),
      );
    });

    test('lists public repos on /repository page for unauthenticated user', async ({
      unauthenticatedPage,
      api,
    }) => {
      const org = await api.organization('anon');
      const repo = await api.repository(org.name, 'public', 'public');

      await unauthenticatedPage.goto('/repository');

      // Should NOT redirect to /signin
      await expect(unauthenticatedPage).toHaveURL(/\/repository/);

      // Public repo should appear in the list
      await expect(
        unauthenticatedPage.getByRole('link', {name: repo.fullName}),
      ).toBeVisible({timeout: 10000});
    });

    test('navigates to signin page via Sign In link', async ({
      unauthenticatedPage,
      api,
    }) => {
      const org = await api.organization('anon');
      const repo = await api.repository(org.name, 'public', 'public');

      await unauthenticatedPage.goto(`/repository/${repo.fullName}`);

      await unauthenticatedPage.getByRole('link', {name: /sign in/i}).click();

      await expect(unauthenticatedPage).toHaveURL(/\/signin/);
    });
  },
);
