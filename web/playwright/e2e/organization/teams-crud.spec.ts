import {test, expect} from '../../fixtures';

test.describe('Teams CRUD', {tag: ['@organization']}, () => {
  test('create team via modal and verify in list', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('tmcrud');
    const teamName = `team${Date.now()}`.substring(0, 20).toLowerCase();

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    await authenticatedPage
      .getByRole('button', {name: 'Create new team'})
      .click();

    // Fill team name via testid
    await authenticatedPage.getByTestId('new-team-name-input').fill(teamName);

    // Fill description via testid
    const descInput = authenticatedPage.getByTestId(
      'new-team-description-input',
    );
    if (await descInput.isVisible({timeout: 1000}).catch(() => false)) {
      await descInput.fill('Test team description');
    }

    // Submit — "Proceed" opens a 4-step wizard; team is created on step 1
    await authenticatedPage.getByRole('button', {name: 'Proceed'}).click();

    // Wait for the wizard to appear (team is created on Proceed)
    await expect(
      authenticatedPage.getByText('Team name and description'),
    ).toBeVisible();

    // Close the wizard — remaining steps are optional
    await authenticatedPage
      .getByRole('dialog')
      .getByRole('button', {name: 'Cancel'})
      .click();

    // Reload to verify team was created
    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    await expect(
      authenticatedPage.getByRole('link', {name: teamName}),
    ).toBeVisible();

    // Cleanup
    const {API_URL} = await import('../../utils/config');
    const csrfResponse = await api['client']['request'].get(
      `${API_URL}/csrf_token`,
    );
    const csrfData = await csrfResponse.json();
    await api['client']['request'].delete(
      `${API_URL}/api/v1/organization/${org.name}/team/${teamName}`,
      {headers: {'X-CSRF-Token': csrfData.csrf_token}},
    );
  });

  test('delete team via kebab menu', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmdel');
    const team = await api.team(org.name, 'delteam');

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    await expect(
      authenticatedPage.getByRole('link', {name: team.name}),
    ).toBeVisible();

    // Click kebab for the team row
    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();

    await authenticatedPage.getByTestId(`${team.name}-del-option`).click();

    // Confirm deletion in modal
    const deleteBtn = authenticatedPage.getByRole('button', {name: 'Delete'});
    await deleteBtn.click();

    // Team should be removed
    await expect(
      authenticatedPage.getByRole('link', {name: team.name}),
    ).not.toBeVisible();
  });

  test('teams list shows team role column', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('tmrole');
    await api.team(org.name, 'roleteam');

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    await expect(
      authenticatedPage.getByRole('columnheader', {name: 'Team role'}),
    ).toBeVisible();
  });

  test('set repo permissions link opens modal', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('tmrepoperm');
    const team = await api.team(org.name, 'permteam');
    await api.repository(org.name, 'permrepo');

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();

    await authenticatedPage
      .getByTestId(`${team.name}-set-repo-perms-option`)
      .click();

    await expect(
      authenticatedPage.getByText('Set repository permissions', {exact: false}),
    ).toBeVisible();
  });

  test('manage members link navigates to team page', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('tmmanage');
    const team = await api.team(org.name, 'manageteam');

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    const teamLink = authenticatedPage.getByRole('link', {
      name: team.name,
    });
    await expect(teamLink).toBeVisible();
    await teamLink.click();

    await expect(authenticatedPage).toHaveURL(
      new RegExp(
        `/organization/${org.name}/teams/${team.name}`.replace(
          /[.*+?^${}()|[\]\\]/g,
          '\\$&',
        ),
      ),
    );
  });
});
