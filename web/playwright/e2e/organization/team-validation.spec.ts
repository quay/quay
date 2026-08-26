import {test, expect} from '../../fixtures';

test.describe('Team Naming and Management', {tag: ['@organization']}, () => {
  test('rejects invalid team names and accepts valid ones', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('teamvalidorg');

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.locator('#Teams').click();
    await authenticatedPage
      .getByRole('button', {name: 'Create new team'})
      .click();

    const nameInput = authenticatedPage.getByTestId('new-team-name-input');

    // Invalid names: must match ^([a-z0-9]+(?:[._-][a-z0-9]+)*)$
    const invalidNames = ['_q', '.a', '-0', 'A12', 'a@12'];
    for (const name of invalidNames) {
      await nameInput.fill(name);
      await expect(
        authenticatedPage.getByTestId('create-team-confirm'),
      ).toBeDisabled();
    }

    // Valid name
    await nameInput.fill('validteam');
    await expect(
      authenticatedPage.getByTestId('create-team-confirm'),
    ).toBeEnabled();

    // Create and verify
    await authenticatedPage.getByTestId('create-team-confirm').click();
    await expect(
      authenticatedPage.getByText(/[Ss]uccessfully created/).first(),
    ).toBeVisible({timeout: 10000});
  });

  test('team pagination works with many teams', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('teampagorg');

    // Create 15 teams via API for pagination
    for (let i = 0; i < 15; i++) {
      await api.team(org.name, `pagteam${String(i).padStart(2, '0')}`);
    }

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.locator('#Teams').click();

    // Verify pagination exists and shows correct count
    const paginationInfo = authenticatedPage
      .locator('.pf-v6-c-pagination__total-items')
      .first();
    await expect(paginationInfo).toContainText('of 1', {timeout: 15000});

    // Verify the owners team (auto-created) brings total to 16
    await expect(paginationInfo).toContainText('16');
  });

  test('navigates to team manage members page', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('inviteorg');
    const team = await api.team(org.name, 'inviteteam');

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.locator('#Teams').click();

    // Open manage members for the team
    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-manage-team-member-option`)
      .click();

    // Verify the manage members page loaded
    await expect(authenticatedPage).toHaveURL(
      new RegExp(`/organization/${org.name}/teams/${team.name}`),
    );
  });
});
