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

    const emailInput = authenticatedPage.locator('#create-org-email-input');
    if (await emailInput.isVisible({timeout: 1000}).catch(() => false)) {
      await emailInput.fill(`${orgName}@example.com`);
    }

    await authenticatedPage.locator('#create-org-confirm').click();

    await expect(authenticatedPage.getByText(/[Ss]uccess/).first()).toBeVisible(
      {timeout: 10000},
    );

    // Clean up
    await api.raw.deleteOrganization(orgName);
  });

  test('shows success alert when creating a team', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('alertteamorg');

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.locator('#Teams').click();

    // Create team
    await authenticatedPage
      .getByRole('button', {name: 'Create new team'})
      .click();
    await authenticatedPage
      .getByTestId('new-team-name-input')
      .fill('alertteam');
    await authenticatedPage.getByTestId('create-team-confirm').click();

    await expect(
      authenticatedPage.getByText(/[Ss]uccessfully created/).first(),
    ).toBeVisible({timeout: 10000});
  });
});
