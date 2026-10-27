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
      authenticatedPage.getByRole('option').filter({hasText: repo.name}),
    ).toBeVisible({timeout: 5000});
  });

  test('search input exposes the combobox contract to assistive tech', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('search-aria');
    const repo = await api.repository(org.name, 'aria-test', 'public');

    await authenticatedPage.goto('/search');

    // getByRole('combobox') only matches if the role is on the input itself.
    const searchInput = authenticatedPage.getByRole('combobox', {
      name: 'Search repositories',
    });
    await expect(searchInput).toHaveAttribute('aria-expanded', 'false');

    await searchInput.pressSequentially(repo.name.slice(0, 8), {delay: 50});
    await expect(searchInput).toHaveAttribute('aria-expanded', 'true', {
      timeout: 5000,
    });

    await searchInput.press('ArrowDown');
    const activeId = await searchInput.getAttribute('aria-activedescendant');
    expect(activeId).toBe('search-suggestion-0');

    // The referenced element must be the option itself, not a wrapper.
    await expect(authenticatedPage.locator(`#${activeId}`)).toHaveAttribute(
      'aria-selected',
      'true',
    );
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
