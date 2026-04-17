import {test, expect} from '../../fixtures';

/**
 * Bug Discovery Tests: Repository List & Repository Details
 *
 * These tests reproduce potential UI bugs found via static analysis
 * of the React frontend source code. Failing tests confirm the bug;
 * passing tests indicate a false positive.
 */
test.describe(
  'Bug Discovery: Repository List',
  {tag: ['@bug-discovery']},
  () => {
    test('search for non-existent repo should show empty state, not spinner', {
      tag: ['@repository'],
    }, async ({authenticatedPage, api}) => {
      // Bug: RepositoriesList.tsx:400-406
      // When filteredRepos.length === 0 (search returns no matches),
      // the code unconditionally renders a Spinner instead of an empty state.
      // The condition does not distinguish between "data loading" and
      // "search returned no results", so users see an infinite spinner
      // when searching for a repo that doesn't exist.
      //
      // Expected behavior: show "No matching repositories" or similar message
      // Actual behavior: shows an infinite loading spinner

      // 1. Create a repo so the list is non-empty (prevents the early-return empty state)
      const repo = await api.repository(undefined, 'searchbug');

      // 2. Navigate to the global repositories list
      await authenticatedPage.goto('/repository');

      // 3. Wait for repos to load
      await expect(
        authenticatedPage.getByTestId('repository-list-table'),
      ).toBeVisible();
      // Verify our repo is visible to confirm data has loaded
      await expect(
        authenticatedPage.getByTestId('repository-list-table'),
      ).toContainText(repo.name);

      // 4. Search for a string that will match no repos
      await authenticatedPage
        .getByPlaceholder(/search by name/i)
        .fill('zzz_nonexistent_repo_xyz_12345');

      // 5. Assert correct behavior: table should NOT show a spinner
      // The Spinner component renders with role="progressbar"
      const tableBody = authenticatedPage.getByTestId('repository-list-table');
      await expect(
        tableBody.locator('[role="progressbar"]'),
      ).not.toBeVisible({timeout: 5000});

      // The table should show some indication that no results were found
      // (e.g., "No matching repositories" or an empty table without spinner)
      // Currently the bug causes a Spinner to appear instead
    });

    test('search with special regex characters should not crash', {
      tag: ['@repository'],
    }, async ({authenticatedPage, api}) => {
      // Bug: FilterInput.tsx supports regex mode, and the search filter
      // in RepositoriesList applies the search. Special characters in
      // the search query could cause a RegExp constructor crash if the
      // regex mode is enabled and the input is not escaped.
      //
      // Expected behavior: search gracefully handles special characters
      // Actual behavior: potential unhandled RegExp syntax error

      const repo = await api.repository(undefined, 'regexbug');

      await authenticatedPage.goto('/repository');
      await expect(
        authenticatedPage.getByTestId('repository-list-table'),
      ).toBeVisible();

      // Type special regex characters that would crash RegExp constructor
      const searchInput = authenticatedPage.getByPlaceholder(/search by name/i);
      await searchInput.fill('[invalid(regex');

      // The page should not crash — no unhandled error
      await expect(
        authenticatedPage.getByTestId('repository-list-table'),
      ).toBeVisible();

      // Clear search and verify repos are visible again
      await searchInput.fill('');
      await expect(
        authenticatedPage.getByTestId('repository-list-table'),
      ).toContainText(repo.name);
    });
  },
);

test.describe(
  'Bug Discovery: Repository Details',
  {tag: ['@bug-discovery']},
  () => {
    test('navigating with invalid tab param should show default tab', {
      tag: ['@repository'],
    }, async ({authenticatedPage, api}) => {
      // Bug: RepositoryDetails.tsx:142-145
      // setState is called during render to sync tab state with URL params.
      // When an invalid tab param is provided, getTabIndex returns undefined,
      // so the condition is false and the default tab (Information) should show.
      // This test validates that the fallback works correctly.
      //
      // Expected behavior: Information tab is shown for invalid ?tab= values
      // Actual behavior: should work, but the setState-during-render pattern
      // could cause issues in edge cases (extra renders, flash of wrong content)

      const repo = await api.repository(undefined, 'tabbug');

      // Navigate with an invalid tab parameter
      await authenticatedPage.goto(
        `/repository/${repo.fullName}?tab=nonexistent`,
      );

      // The Information tab should be active (default fallback)
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Information'}),
      ).toHaveAttribute('aria-selected', 'true');
    });

    test('tab state should stay in sync with URL across navigation', {
      tag: ['@repository'],
    }, async ({authenticatedPage, api}) => {
      // Bug: RepositoryDetails.tsx:142-145
      // The tab state is synced via setState during render, which in React 18
      // causes an extra synchronous re-render. This test validates that rapid
      // tab navigation via URL params stays consistent.
      //
      // Expected behavior: each tab param shows the correct tab content
      // Actual behavior: extra re-renders could cause flicker or stale state

      const repo = await api.repository(undefined, 'tabsyncbug');

      // Navigate to Tags tab via URL
      await authenticatedPage.goto(
        `/repository/${repo.fullName}?tab=tags`,
      );
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Tags'}),
      ).toHaveAttribute('aria-selected', 'true');

      // Navigate to Tag history tab via URL
      await authenticatedPage.goto(
        `/repository/${repo.fullName}?tab=history`,
      );
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Tag history'}),
      ).toHaveAttribute('aria-selected', 'true');

      // Navigate to Settings tab via URL (as owner/admin)
      await authenticatedPage.goto(
        `/repository/${repo.fullName}?tab=settings`,
      );
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Settings'}),
      ).toHaveAttribute('aria-selected', 'true');

      // Navigate back to Information tab
      await authenticatedPage.goto(
        `/repository/${repo.fullName}?tab=information`,
      );
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Information'}),
      ).toHaveAttribute('aria-selected', 'true');
    });

    test('settings tab should not be accessible via URL for non-admin users', {
      tag: ['@repository'],
    }, async ({authenticatedPage, readonlyPage, api}) => {
      // Bug: RepositoryDetails.tsx:142-145 + 349
      // The tab param is applied via setState during render WITHOUT checking
      // if the target tab is hidden. The Settings tab has isHidden={!can_admin},
      // but setActiveTabKey('settings') is called regardless of permissions.
      // This means a non-admin user navigating to ?tab=settings would have
      // the Settings tab content mounted (via mountOnEnter) even though the
      // tab header is hidden.
      //
      // Expected behavior: non-admin user sees the default tab (Information)
      // Actual behavior: Settings content may render without visible tab header

      // Create a public repo owned by testuser
      const org = await api.organization('tabaccess');
      const repo = await api.repository(org.name, 'pubrepo', 'public');

      // Navigate as readonly user to the repo with ?tab=settings
      await readonlyPage.goto(
        `/repository/${repo.fullName}?tab=settings`,
      );

      // The Settings tab should NOT be selected since readonly user is not admin
      // Instead, the default Information tab should be shown
      const settingsTab = readonlyPage.getByRole('tab', {name: 'Settings'});

      // Settings tab header should not be visible for non-admin
      await expect(settingsTab).not.toBeVisible();

      // Information tab should be the active/selected tab
      await expect(
        readonlyPage.getByRole('tab', {name: 'Information'}),
      ).toHaveAttribute('aria-selected', 'true');
    });
  },
);
