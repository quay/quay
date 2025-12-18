import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe('Shorthand URL Navigation', {tag: ['@repository']}, () => {
  test('redirects shorthand URL /:org/:repo to /repository/:org/:repo', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository(undefined, 'shorthand');

    await authenticatedPage.goto(`/${repo.namespace}/${repo.name}`);

    await expect(authenticatedPage).toHaveURL(`/repository/${repo.fullName}`);
    await expect(authenticatedPage.getByTestId('repo-title')).toContainText(
      repo.name,
    );
  });

  test('redirects multi-segment repository names correctly', async ({
    authenticatedPage,
    api,
  }) => {
    // Create repo with / in name (e.g., "release/installer")
    const namespace = TEST_USERS.user.username;
    const basePrefix = uniqueName('release');
    const repo = await api.repositoryWithName(
      namespace,
      `${basePrefix}/installer`,
    );

    await authenticatedPage.goto(`/${namespace}/${repo.name}`);

    await expect(authenticatedPage).toHaveURL(`/repository/${repo.fullName}`);
    await expect(authenticatedPage.getByTestId('repo-title')).toContainText(
      'installer',
    );
  });

  test('does not redirect reserved route prefixes', async ({
    authenticatedPage,
  }) => {
    const testUser = TEST_USERS.user.username;

    await authenticatedPage.goto(`/user/${testUser}`);

    // Should NOT redirect to /repository/user/testuser
    await expect(authenticatedPage).toHaveURL(`/user/${testUser}`);
    // Use repo-title testid which shows the username on user profile page
    await expect(authenticatedPage.getByTestId('repo-title')).toContainText(
      testUser,
    );
  });

  test('redirects single-segment org URL to /organization/:org', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('navorg');

    await authenticatedPage.goto(`/${org.name}`);

    await expect(authenticatedPage).toHaveURL(`/organization/${org.name}`);
    await expect(authenticatedPage.getByTestId('repo-title')).toContainText(
      org.name,
    );
  });

  test('preserves query parameters and hash fragments for organization redirects', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('navorg');

    // Test query params
    await authenticatedPage.goto(`/${org.name}?tab=teams`);
    await expect(authenticatedPage).toHaveURL(
      `/organization/${org.name}?tab=teams`,
    );

    // Test hash fragments
    await authenticatedPage.goto(`/${org.name}#section`);
    await expect(authenticatedPage).toHaveURL(
      new RegExp(`/organization/${org.name}#section`),
    );
  });

  test('preserves query parameters and hash fragments during repository redirect', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository(undefined, 'shorthand');

    // Test query params
    await authenticatedPage.goto(`/${repo.namespace}/${repo.name}?tab=tags`);
    await expect(authenticatedPage).toHaveURL(
      `/repository/${repo.fullName}?tab=tags`,
    );
    await expect(
      authenticatedPage.getByRole('tab', {selected: true}),
    ).toContainText('Tags');

    // Test hash fragments
    await authenticatedPage.goto(`/${repo.namespace}/${repo.name}#section`);
    await expect(authenticatedPage).toHaveURL(
      new RegExp(`/repository/${repo.fullName}#section`),
    );

    // Test both
    await authenticatedPage.goto(
      `/${repo.namespace}/${repo.name}?tab=tags#section`,
    );
    await expect(authenticatedPage).toHaveURL(
      new RegExp(`/repository/${repo.fullName}\\?tab=tags#section`),
    );
  });

  test('shows errors when resources do not exist', async ({
    authenticatedPage,
  }) => {
    const nonExistentOrg = uniqueName('nonexistent');
    const nonExistentRepo = uniqueName('fakerepo');

    // Test repository 404 - navigate to non-existent repo
    await authenticatedPage.goto(`/${nonExistentOrg}/${nonExistentRepo}`);
    await expect(authenticatedPage).toHaveURL(
      `/repository/${nonExistentOrg}/${nonExistentRepo}`,
    );
    await expect(
      authenticatedPage.getByText('Unable to get repository'),
    ).toBeVisible();

    // Test organization 404 - navigate to non-existent org
    await authenticatedPage.goto(`/${nonExistentOrg}`);
    await expect(authenticatedPage).toHaveURL(
      `/organization/${nonExistentOrg}`,
    );
    // Organization page handles 404 display
  });
});
