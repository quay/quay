import {test, expect} from '../../fixtures';

const SEARCH_LABEL = 'Search repositories and organizations';

test.describe('Header search bar', {tag: ['@ui', '@PROJQUAY-12269']}, () => {
  test('is present in the masthead on ordinary pages', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/organization');

    await expect(
      authenticatedPage.getByRole('combobox', {name: SEARCH_LABEL}),
    ).toBeVisible();
  });

  test('is hidden on the search page, which has its own input', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/search');

    await expect(
      authenticatedPage.getByRole('combobox', {name: SEARCH_LABEL}),
    ).toBeHidden();
    await expect(
      authenticatedPage.getByPlaceholder('Search repositories...'),
    ).toBeVisible();
  });

  test('submitting a term navigates to the search page', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('hdr-submit');
    const repo = await api.repository(org.name, 'hdr-findme', 'public');

    await authenticatedPage.goto('/organization');

    const searchInput = authenticatedPage.getByRole('combobox', {
      name: SEARCH_LABEL,
    });
    await searchInput.fill(repo.name);
    await searchInput.press('Enter');

    await expect(authenticatedPage).toHaveURL(new RegExp(`/search\\?q=`));
    await expect(
      authenticatedPage.getByRole('link', {name: repo.fullName}),
    ).toBeVisible();
  });

  test('suggests repositories and navigates on click', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('hdr-repo');
    const repo = await api.repository(org.name, 'hdr-suggest', 'public');

    await authenticatedPage.goto('/organization');

    const searchInput = authenticatedPage.getByRole('combobox', {
      name: SEARCH_LABEL,
    });
    await searchInput.pressSequentially(repo.name.slice(0, 10), {delay: 50});

    const suggestion = authenticatedPage
      .getByRole('option')
      .filter({hasText: repo.name});
    await expect(suggestion).toBeVisible({timeout: 5000});
    await suggestion.click();

    await expect(authenticatedPage).toHaveURL(
      new RegExp(`/repository/${org.name}/${repo.name}`),
    );
  });

  test('suggests organizations as well as repositories', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('hdr-org');
    // Namespace suggestions inner-join Repository, so an empty org is never
    // returned by /find/all. Give it a visible repository.
    await api.repository(org.name, 'hdr-org-repo', 'public');

    await authenticatedPage.goto('/organization');

    const searchInput = authenticatedPage.getByRole('combobox', {
      name: SEARCH_LABEL,
    });
    await searchInput.pressSequentially(org.name.slice(0, 10), {delay: 50});

    await expect(
      authenticatedPage.getByRole('option').filter({hasText: org.name}),
    ).toBeVisible({timeout: 5000});
  });

  test('is keyboard navigable and exposes the combobox contract', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('hdr-keys');
    const repo = await api.repository(org.name, 'hdr-arrow', 'public');

    await authenticatedPage.goto('/organization');

    const searchInput = authenticatedPage.getByRole('combobox', {
      name: SEARCH_LABEL,
    });
    await expect(searchInput).toHaveAttribute('aria-expanded', 'false');

    await searchInput.pressSequentially(repo.name.slice(0, 10), {delay: 50});
    await expect(searchInput).toHaveAttribute('aria-expanded', 'true', {
      timeout: 5000,
    });

    await searchInput.press('ArrowDown');
    const activeId = await searchInput.getAttribute('aria-activedescendant');
    expect(activeId).toBe('header-search-suggestion-0');

    // aria-activedescendant must reference the option itself so a screen
    // reader can announce the highlighted suggestion.
    await expect(authenticatedPage.locator(`#${activeId}`)).toHaveAttribute(
      'aria-selected',
      'true',
    );

    await searchInput.press('Enter');
    await expect(authenticatedPage).not.toHaveURL(/\/organization$/);
  });

  test('Escape closes the dropdown and it stays closed', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('hdr-esc');
    const repo = await api.repository(org.name, 'hdr-escape', 'public');

    await authenticatedPage.goto('/organization');

    const searchInput = authenticatedPage.getByRole('combobox', {
      name: SEARCH_LABEL,
    });
    await searchInput.pressSequentially(repo.name.slice(0, 10), {delay: 50});
    await expect(
      authenticatedPage.getByRole('option').filter({hasText: repo.name}),
    ).toBeVisible({timeout: 5000});

    await searchInput.press('Escape');
    await expect(authenticatedPage.getByRole('option')).toHaveCount(0);

    // Must not reappear once a background refetch settles.
    await authenticatedPage.waitForTimeout(1000);
    await expect(authenticatedPage.getByRole('option')).toHaveCount(0);
  });

  test(
    'anonymous users get the header search bar',
    {tag: ['@feature:ANONYMOUS_ACCESS']},
    async ({unauthenticatedPage, api}) => {
      const org = await api.organization('hdr-anon');
      await api.repository(org.name, 'hdr-anon-repo', 'public');

      await unauthenticatedPage.goto('/organization');

      await expect(
        unauthenticatedPage.getByRole('combobox', {name: SEARCH_LABEL}),
      ).toBeVisible();
    },
  );
});
