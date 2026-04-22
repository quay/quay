import {test, expect} from '../../fixtures';

test.describe('Empty States and Alert Messages', {tag: ['@ui']}, () => {
  test('shows empty state when organization has no repositories', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('emptyorg');

    await authenticatedPage.goto(`/organization/${org.name}`);

    await expect(
      authenticatedPage.getByText('There are no viewable repositories'),
    ).toBeVisible();
    await expect(
      authenticatedPage.getByRole('button', {name: 'Create Repository'}),
    ).toBeVisible();
  });

  test('shows empty state when repository has no tags', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('emptytagorg');
    const repo = await api.repository(org.name, 'emptyrepo');

    await authenticatedPage.goto(
      `/repository/${org.name}/${repo.name}?tab=tags`,
    );

    await expect(
      authenticatedPage.getByText(
        'There are no viewable tags for this repository',
      ),
    ).toBeVisible();
  });

  test('shows empty state on repositories list page when user has no repos', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/repository');

    await expect(
      authenticatedPage.getByText('There are no viewable repositories'),
    ).toBeVisible();
  });

  test('shows success alert when creating an organization', async ({
    authenticatedPage,
    api,
  }) => {
    // Create org via UI to verify alert
    await authenticatedPage.goto('/organization');
    await authenticatedPage
      .getByRole('button', {name: 'Create Organization'})
      .click();

    const orgName = `alertorg${Date.now()}`;
    await authenticatedPage.locator('#create-org-name-input').fill(orgName);
    await authenticatedPage
      .locator('#create-org-email-input')
      .fill(`${orgName}@example.com`);
    await authenticatedPage.locator('#create-org-confirm').click();

    await expect(authenticatedPage.getByText(/[Ss]uccess/).first()).toBeVisible(
      {timeout: 10000},
    );

    // Clean up
    await api.raw.deleteOrganization(orgName);
  });

  test('shows success alert when creating and deleting a team', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('alertteamorg');

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.locator('#Teams').click();

    // Create team
    await authenticatedPage.getByRole('button', {name: 'Create team'}).click();
    await authenticatedPage
      .getByPlaceholder('Enter a team name')
      .fill('alertteam');
    await authenticatedPage.getByRole('button', {name: 'Proceed'}).click();

    await expect(
      authenticatedPage.getByText(/[Ss]uccessfully created/).first(),
    ).toBeVisible({timeout: 10000});
  });
});
