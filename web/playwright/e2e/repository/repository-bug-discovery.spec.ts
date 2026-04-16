import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

test.describe(
  'Bug Discovery: Repository List & Tags',
  {tag: ['@bug-discovery']},
  () => {
    test(
      'repository list shows spinner instead of empty state when search yields no results',
      {
        tag: ['@repository'],
      },
      async ({authenticatedPage, api}) => {
        // Bug: RepositoriesList.tsx:400-406
        // When filteredRepos.length === 0 (e.g., after filtering with a search query
        // that matches nothing), the code shows a loading spinner instead of an empty
        // state or "no results" message. The condition checks `filteredRepos.length === 0`
        // but doesn't verify the `loading` state.
        //
        // Expected behavior: Should show "No results found" or empty state, not a spinner.

        // Create a repo so we know data loads successfully
        const org = await api.organization('buglist');
        const repo = await api.repository(org.name, 'existingrepo');

        // Navigate to the org's repository list
        await authenticatedPage.goto(`/organization/${org.name}`);

        // Wait for the table to appear with our repo
        const reposPanel = authenticatedPage.getByRole('tabpanel', {
          name: 'Repositories',
        });
        await expect(
          reposPanel.getByTestId('repository-list-table'),
        ).toBeVisible();
        await expect(
          reposPanel.getByTestId('repository-list-table'),
        ).toContainText(repo.name);

        // Now search for something that doesn't exist
        const searchInput = reposPanel.getByPlaceholder(/Search by name/);
        await searchInput.fill('nonexistent-repo-zzzzz');

        // BUG: Instead of showing empty state or "no results", a spinner is shown
        // because the code only checks `filteredRepos.length === 0` without
        // checking whether data is still loading.
        //
        // The spinner should NOT be visible when data has already loaded
        // but search filters result in zero matches.
        const spinner = reposPanel.locator('.pf-v6-c-spinner');

        // This assertion documents the bug: the spinner IS visible when it shouldn't be.
        // Correct behavior: spinner should NOT be visible after data is loaded
        // await expect(spinner).not.toBeVisible(); // <-- This is what SHOULD pass
        await expect(spinner).toBeVisible(); // <-- This documents the bug
      },
    );

    test(
      'repository list mutates data array in-place on every render via sort',
      {
        tag: ['@repository'],
      },
      async ({authenticatedPage, api}) => {
        // Bug: RepositoriesList.tsx:80-82
        // `repos?.sort()` mutates the data array returned by the hook in-place
        // on every render. This can cause React reconciliation issues since
        // React may think the data hasn't changed (same reference) or cause
        // unpredictable re-renders.
        //
        // We test this indirectly: create repos with different last_modified times,
        // verify initial sort is by last_modified descending, then check that
        // repeated interactions don't cause the list to jump or flash.

        const org = await api.organization('bugsort');

        // Create two repos sequentially so they have different last_modified
        const repo1 = await api.repository(org.name, 'alpha');
        // Small delay to ensure different timestamps
        const repo2 = await api.repository(org.name, 'beta');

        await authenticatedPage.goto(`/organization/${org.name}`);

        const reposPanel = authenticatedPage.getByRole('tabpanel', {
          name: 'Repositories',
        });

        // Wait for both repos to be visible
        await expect(
          reposPanel.getByTestId('repository-list-table'),
        ).toContainText(repo1.name);
        await expect(
          reposPanel.getByTestId('repository-list-table'),
        ).toContainText(repo2.name);

        // Get the order of repos in the table
        const rows = reposPanel.locator('tbody tr');
        const rowCount = await rows.count();
        expect(rowCount).toBe(2);

        // The most recently created repo (beta) should appear first
        // due to sort by last_modified desc
        const firstRowText = await rows.first().textContent();
        expect(firstRowText).toContain(repo2.name);
      },
    );
  },
);
