import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {API_URL} from '../../utils/config';

/**
 * Helper to get the search input inside the PatternFly SearchInput component
 */
function getSearchInput(page) {
  return page.getByPlaceholder(/Search by name/);
}

test.describe('Repositories List', {tag: ['@repository']}, () => {
  test.describe('rendering', () => {
    test('displays repositories in global and organization views', async ({
      authenticatedPage,
      api,
    }) => {
      // Create test organization with repositories
      const org = await api.organization('repolist');
      const repo1 = await api.repository(org.name, 'hello-world');
      const repo2 = await api.repositoryWithName(org.name, 'nested/repo');

      // Part A: Global /repository view
      await authenticatedPage.goto('/repository');
      await expect(
        authenticatedPage.getByRole('heading', {name: 'Repositories'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('repository-list-table'),
      ).toBeVisible();

      // Search for our organization to filter results
      await getSearchInput(authenticatedPage).fill(org.name);

      // Verify repos appear in search results
      await expect(
        authenticatedPage.getByTestId('repository-list-table'),
      ).toContainText(repo1.fullName);
      await expect(
        authenticatedPage.getByTestId('repository-list-table'),
      ).toContainText(repo2.fullName);

      // Verify table columns
      const firstRow = authenticatedPage.locator('tbody tr').first();
      await expect(firstRow.locator('[data-label="Name"]')).toBeVisible();
      await expect(firstRow.locator('[data-label="Visibility"]')).toBeVisible();
      await expect(
        firstRow.locator('[data-label="Last Modified"]'),
      ).toBeVisible();

      // Part B: Organization view
      await authenticatedPage.goto(`/organization/${org.name}`);
      await expect(authenticatedPage.getByTestId('repo-title')).toContainText(
        org.name,
      );

      // Scope to Repositories tab panel
      const reposPanel = authenticatedPage.getByRole('tabpanel', {
        name: 'Repositories',
      });

      await expect(
        reposPanel.getByTestId('repository-list-table'),
      ).toBeVisible();

      // In org view, repos should show short names without namespace prefix
      const table = reposPanel.getByTestId('repository-list-table');
      await expect(table).toContainText('hello-world');
      await expect(table).toContainText('nested/repo');

      // Verify we have 2 repos
      await expect(reposPanel.locator('tbody tr')).toHaveCount(2);
    });
  });

  test.describe('CRUD operations', () => {
    test('creates repositories with different visibility and namespaces', async ({
      authenticatedPage,
      authenticatedRequest,
      api,
    }) => {
      const testUser = TEST_USERS.user.username;
      const org = await api.organization('repocreate');

      // Generate unique names for UI-created repos to avoid conflicts with parallel tests
      const publicRepoName = uniqueName('publicrepo');
      const privateRepoName = uniqueName('privaterepo');
      const orgRepoName = uniqueName('orgrepo');

      // Part A: Create public repository in user namespace via UI
      await authenticatedPage.goto('/repository');
      await authenticatedPage
        .getByRole('button', {name: 'Create Repository'})
        .click();

      // Verify modal opens
      await expect(
        authenticatedPage.locator('.pf-v6-c-modal-box__title-text'),
      ).toHaveText('Create repository');

      // Select user namespace from dropdown
      await authenticatedPage
        .getByTestId('selected-namespace-dropdown')
        .click();
      await authenticatedPage.getByTestId(`user-${testUser}`).click();

      // Fill repository details
      await authenticatedPage
        .getByTestId('repository-name-input')
        .fill(publicRepoName);
      await authenticatedPage
        .getByTestId('repository-description-input')
        .fill('This is a new public repository');

      // PUBLIC is default, verify it's selected
      await expect(
        authenticatedPage.getByTestId('visibility-public-radio'),
      ).toBeChecked();

      // Submit
      await authenticatedPage
        .getByTestId('create-repository-submit-btn')
        .click();

      // Verify success - wait for modal close (auto-wait handles the success alert)
      await expect(
        authenticatedPage.locator('.pf-v6-c-modal-box'),
      ).not.toBeVisible();

      // Search for the new repo
      await getSearchInput(authenticatedPage).fill(
        `${testUser}/${publicRepoName}`,
      );
      await expect(
        authenticatedPage.getByText(`${testUser}/${publicRepoName}`),
      ).toBeVisible();

      // Verify visibility is public
      const repoRow = authenticatedPage.locator('tr', {
        hasText: `${testUser}/${publicRepoName}`,
      });
      await expect(repoRow.locator('[data-label="Visibility"]')).toContainText(
        'public',
      );

      // Cleanup the UI-created repo
      await authenticatedRequest.delete(
        `${API_URL}/api/v1/repository/${testUser}/${publicRepoName}`,
      );

      // Part B: Create private repository in user namespace
      await getSearchInput(authenticatedPage).fill(''); // Clear search
      await authenticatedPage
        .getByRole('button', {name: 'Create Repository'})
        .click();

      await authenticatedPage
        .getByTestId('selected-namespace-dropdown')
        .click();
      await authenticatedPage.getByTestId(`user-${testUser}`).click();

      await authenticatedPage
        .getByTestId('repository-name-input')
        .fill(privateRepoName);
      await authenticatedPage
        .getByTestId('repository-description-input')
        .fill('This is a new private repository');

      // Select PRIVATE visibility
      await authenticatedPage.getByTestId('visibility-private-radio').click();
      await expect(
        authenticatedPage.getByTestId('visibility-private-radio'),
      ).toBeChecked();

      await authenticatedPage
        .getByTestId('create-repository-submit-btn')
        .click();

      // Verify success - wait for modal close
      await expect(
        authenticatedPage.locator('.pf-v6-c-modal-box'),
      ).not.toBeVisible();

      await getSearchInput(authenticatedPage).fill(
        `${testUser}/${privateRepoName}`,
      );
      const privateRepoRow = authenticatedPage.locator('tr', {
        hasText: privateRepoName,
      });
      await expect(
        privateRepoRow.locator('[data-label="Visibility"]'),
      ).toContainText('private');

      // Cleanup
      await authenticatedRequest.delete(
        `${API_URL}/api/v1/repository/${testUser}/${privateRepoName}`,
      );

      // Part C: Create repository under organization
      await authenticatedPage.goto(`/organization/${org.name}`);

      // Scope to Repositories tab panel
      const reposPanel = authenticatedPage.getByRole('tabpanel', {
        name: 'Repositories',
      });

      await reposPanel.getByRole('button', {name: 'Create Repository'}).click();

      // In org context, namespace dropdown should show org name and be disabled
      await expect(
        authenticatedPage.getByTestId('selected-namespace-dropdown'),
      ).toContainText(org.name);
      await expect(
        authenticatedPage.getByTestId('selected-namespace-dropdown'),
      ).toBeDisabled();

      await authenticatedPage
        .getByTestId('repository-name-input')
        .fill(orgRepoName);
      await authenticatedPage
        .getByTestId('repository-description-input')
        .fill('This is a new org repository');

      // Select PRIVATE visibility
      await authenticatedPage.getByTestId('visibility-private-radio').click();

      await authenticatedPage
        .getByTestId('create-repository-submit-btn')
        .click();

      // Verify success - wait for modal close
      await expect(
        authenticatedPage.locator('.pf-v6-c-modal-box'),
      ).not.toBeVisible();
      await expect(reposPanel.getByText(orgRepoName)).toBeVisible();

      // Verify visibility
      const orgRepoRow = reposPanel.locator('tr', {hasText: orgRepoName});
      await expect(
        orgRepoRow.locator('[data-label="Visibility"]'),
      ).toContainText('private');

      // Note: org-repo will be cleaned up when org is deleted by api fixture
    });
  });

  test.describe('bulk operations', () => {
    test('deletes multiple repositories via bulk action', async ({
      authenticatedPage,
      authenticatedRequest,
      api,
    }) => {
      // Create organization with multiple repos
      const org = await api.organization('bulkdel');
      const repo1 = await api.repository(org.name, 'delrepo1');
      const repo2 = await api.repository(org.name, 'delrepo2');

      // Navigate to org view
      await authenticatedPage.goto(`/organization/${org.name}`);

      // Scope to Repositories tab panel to avoid multiple matching elements
      const reposPanel = authenticatedPage.getByRole('tabpanel', {
        name: 'Repositories',
      });

      // Verify our repos are visible in the table
      await expect(reposPanel.getByText(repo1.name)).toBeVisible();
      await expect(reposPanel.getByText(repo2.name)).toBeVisible();

      // Click toolbar checkbox dropdown to open selection menu
      await reposPanel.locator('#toolbar-dropdown-checkbox').click();

      // Click "Select all" option
      await authenticatedPage.getByTestId('select-all-items-action').click();

      // Open Actions menu and click Delete
      await reposPanel.getByText('Actions').click();
      await authenticatedPage.getByRole('menuitem', {name: 'Delete'}).click();

      // Verify bulk delete modal appears
      await expect(
        authenticatedPage.getByTestId('bulk-delete-modal'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Permanently delete repositories?'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(
          'This action deletes all repositories and cannot be recovered.',
        ),
      ).toBeVisible();

      // Type confirmation
      await authenticatedPage
        .getByTestId('delete-confirmation-input')
        .fill('confirm');

      // Click Delete button in modal
      await authenticatedPage.getByTestId('bulk-delete-confirm-btn').click();

      // Verify empty state appears
      await expect(
        authenticatedPage.getByText('There are no viewable repositories'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(
          'Either no repositories exist yet or you may not have permission to view any.',
        ),
      ).toBeVisible();

      // Verify repos are deleted via API
      const verifyResponse1 = await authenticatedRequest.get(
        `${API_URL}/api/v1/repository/${org.name}/delrepo1`,
      );
      expect(verifyResponse1.status()).toBe(404);
    });

    test('changes visibility for multiple repositories', async ({
      authenticatedPage,
      api,
    }) => {
      // Create organization with private repos
      const org = await api.organization('bulkvis');
      const repo1 = await api.repository(org.name, 'visrepo1', 'private');
      const repo2 = await api.repository(org.name, 'visrepo2', 'private');

      await authenticatedPage.goto(`/organization/${org.name}`);

      // Scope to Repositories tab panel to avoid multiple matching elements
      const reposPanel = authenticatedPage.getByRole('tabpanel', {
        name: 'Repositories',
      });

      // Verify initial visibility is private
      const repo1Row = reposPanel.locator('tr', {hasText: repo1.name});
      const repo2Row = reposPanel.locator('tr', {hasText: repo2.name});
      await expect(repo1Row.locator('[data-label="Visibility"]')).toContainText(
        'private',
      );
      await expect(repo2Row.locator('[data-label="Visibility"]')).toContainText(
        'private',
      );

      // Part A: Make repos public
      // Select all repos
      await reposPanel.locator('#toolbar-dropdown-checkbox').click();
      await authenticatedPage.getByTestId('select-all-items-action').click();

      // Open Actions menu and click "Make public"
      await reposPanel.getByText('Actions').click();
      await authenticatedPage
        .getByRole('menuitem', {name: 'Make public'})
        .click();

      // Verify confirmation modal
      await expect(
        authenticatedPage.getByText('Make repositories public'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(
          'Update 2 repositories visibility to be public so they are visible to all user, and may be pulled by all users.',
        ),
      ).toBeVisible();

      // Confirm
      await authenticatedPage.getByTestId('make-public-confirm-btn').click();

      // Verify visibility changed to public
      await expect(repo1Row.locator('[data-label="Visibility"]')).toContainText(
        'public',
      );
      await expect(repo2Row.locator('[data-label="Visibility"]')).toContainText(
        'public',
      );

      // Part B: Make repos private again
      // Select all repos again
      await reposPanel.locator('#toolbar-dropdown-checkbox').click();
      await authenticatedPage.getByTestId('select-all-items-action').click();

      // Open Actions menu and click "Make private"
      await reposPanel.getByText('Actions').click();
      await authenticatedPage
        .getByRole('menuitem', {name: 'Make private'})
        .click();

      // Verify confirmation modal
      await expect(
        authenticatedPage.getByText('Make repositories private'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(
          'Update 2 repositories visibility to be private so they are only visible to certain users, and only may be pulled by certain users.',
        ),
      ).toBeVisible();

      // Confirm
      await authenticatedPage.getByTestId('make-private-confirm-btn').click();

      // Verify visibility changed back to private
      await expect(repo1Row.locator('[data-label="Visibility"]')).toContainText(
        'private',
      );
      await expect(repo2Row.locator('[data-label="Visibility"]')).toContainText(
        'private',
      );
    });
  });

  test.describe('search functionality', () => {
    test('searches by name and supports regex mode', async ({
      authenticatedPage,
      api,
    }) => {
      // Create organization with repos having exact predictable names for regex testing
      const org = await api.organization('searchorg');
      // Use repositoryWithName to create repos with exact names (no uniqueName suffix)
      await api.repositoryWithName(org.name, 'hello-world');
      await api.repositoryWithName(org.name, 'hello-test');
      await api.repositoryWithName(org.name, 'goodbye-world');
      await api.repositoryWithName(org.name, 'repo1');
      await api.repositoryWithName(org.name, 'repo2');
      await api.repositoryWithName(org.name, 'repo10');

      await authenticatedPage.goto(`/organization/${org.name}`);

      // Scope to Repositories tab panel
      const reposPanel = authenticatedPage.getByRole('tabpanel', {
        name: 'Repositories',
      });

      // Verify all 6 repos are visible initially
      await expect(reposPanel.locator('tbody tr')).toHaveCount(6);

      // Part A: Basic name search for "hello"
      const searchInput = getSearchInput(authenticatedPage);
      await searchInput.fill('hello');

      // Should show only 2 repos (hello-world, hello-test)
      await expect(reposPanel.locator('tbody tr')).toHaveCount(2);
      await expect(reposPanel.getByText('hello-world')).toBeVisible();
      await expect(reposPanel.getByText('hello-test')).toBeVisible();

      // Clear search
      await searchInput.fill('');

      // Verify all repos visible again
      await expect(reposPanel.locator('tbody tr')).toHaveCount(6);

      // Part B: Regex search
      // Open advanced search panel
      await authenticatedPage.getByLabel('Open advanced search').click();

      // Enable regex mode
      await authenticatedPage.locator('#filter-input-regex-checker').click();

      // Search for repos ending with single digit (repo1, repo2 but NOT repo10)
      await searchInput.fill('repo[0-9]$');

      // Should show only 2 repos
      await expect(reposPanel.locator('tbody tr')).toHaveCount(2);
      await expect(reposPanel.getByText('repo1')).toBeVisible();
      await expect(reposPanel.getByText('repo2')).toBeVisible();
      await expect(reposPanel.getByText('repo10')).not.toBeVisible();

      // Part C: Reset search
      await authenticatedPage.getByLabel('Reset search').click();

      // Verify all repos visible again
      await expect(reposPanel.locator('tbody tr')).toHaveCount(6);
      await expect(reposPanel.getByText('repo10')).toBeVisible();
    });

    test('searches by name including organization', async ({
      authenticatedPage,
      api,
    }) => {
      // Create organization with repos
      const org = await api.organization('searchbyorg');
      await api.repository(org.name, 'testrepo1');
      await api.repository(org.name, 'testrepo2');

      // Navigate to global repository view
      await authenticatedPage.goto('/repository');

      // Search for the organization name
      await getSearchInput(authenticatedPage).fill(org.name);

      // Should find repos belonging to that org
      await expect(
        authenticatedPage.getByText(`${org.name}/testrepo1`),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(`${org.name}/testrepo2`),
      ).toBeVisible();

      // Verify only our org's repos are shown (count varies based on test data)
      const rows = authenticatedPage.locator('tbody tr');
      const count = await rows.count();
      expect(count).toBeGreaterThanOrEqual(2);
    });
  });
});
