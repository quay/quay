import {test, expect} from '../../fixtures';

test.describe('Search Page', {tag: ['@ui', '@PROJQUAY-12269']}, () => {
  test('renders search page at /search', async ({authenticatedPage}) => {
    await authenticatedPage.goto('/search');

    await expect(
      authenticatedPage.getByRole('heading', {name: 'Search'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.getByPlaceholder('Search repositories...'),
    ).toBeVisible();
  });

  test('does not redirect /search to /organization/search', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/search');

    await expect(authenticatedPage).toHaveURL(/\/search$/);
    await expect(authenticatedPage).not.toHaveURL(/\/organization\/search/);
  });

  test('lists repositories on load without query', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('search-list');
    const repo = await api.repository(org.name, 'search-test', 'public');

    await authenticatedPage.goto('/search');

    await expect(
      authenticatedPage.getByRole('link', {name: repo.fullName}),
    ).toBeVisible();
  });

  test('searches repositories by query', async ({authenticatedPage, api}) => {
    const org = await api.organization('search-query');
    const repo = await api.repository(org.name, 'findme', 'public');
    await api.repository(org.name, 'other', 'public');

    await authenticatedPage.goto('/search');

    const searchInput = authenticatedPage.getByPlaceholder(
      'Search repositories...',
    );
    await searchInput.fill(repo.name);
    await searchInput.press('Enter');

    await expect(authenticatedPage).toHaveURL(new RegExp(`q=${repo.name}`));
    await expect(
      authenticatedPage.getByRole('link', {name: repo.fullName}),
    ).toBeVisible();
  });

  test(
    'anonymous user can access search and find public repos',
    {tag: ['@feature:ANONYMOUS_ACCESS']},
    async ({unauthenticatedPage, api}) => {
      const org = await api.organization('search-anon');
      const repo = await api.repository(org.name, 'anon-vis', 'public');

      await unauthenticatedPage.goto('/search');

      await expect(
        unauthenticatedPage.getByRole('heading', {name: 'Search'}),
      ).toBeVisible();
      await expect(
        unauthenticatedPage.getByRole('link', {name: repo.fullName}),
      ).toBeVisible();
    },
  );

  test('shows typeahead suggestions while typing', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('search-suggest');
    const repo = await api.repository(org.name, 'suggest-test', 'public');

    await authenticatedPage.goto('/search');

    const searchInput = authenticatedPage.getByPlaceholder(
      'Search repositories...',
    );
    await searchInput.pressSequentially(repo.name.slice(0, 10), {delay: 50});

    await expect(
      authenticatedPage.getByRole('menuitem').filter({hasText: repo.name}),
    ).toBeVisible({timeout: 5000});
  });

  test('shows empty state when no results match', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/search');

    const searchInput = authenticatedPage.getByPlaceholder(
      'Search repositories...',
    );
    await searchInput.fill('zzz-nonexistent-repo-xyz');
    await searchInput.press('Enter');

    await expect(
      authenticatedPage.getByText('No matching repositories found'),
    ).toBeVisible();
  });
});
