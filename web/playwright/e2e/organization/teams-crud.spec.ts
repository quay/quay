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
      .getByRole('button', {name: 'Create New Team'})
      .click();

    // Fill team name
    const nameInput = authenticatedPage.getByPlaceholder('Enter a team name');
    await nameInput.fill(teamName);

    // Fill description
    const descInput = authenticatedPage.getByPlaceholder('Enter a description');
    if (await descInput.isVisible({timeout: 1000}).catch(() => false)) {
      await descInput.fill('Test team description');
    }

    // Submit
    await authenticatedPage.getByRole('button', {name: 'Proceed'}).click();

    // Wait for wizard or close modal
    // Team should appear in the teams list after creation
    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    await expect(
      authenticatedPage.getByRole('cell', {name: teamName}),
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
      authenticatedPage.getByRole('cell', {name: team.name}),
    ).toBeVisible();

    // Click kebab for the team row
    const teamRow = authenticatedPage
      .getByRole('row')
      .filter({hasText: team.name});
    await teamRow.getByRole('button', {name: /actions|kebab/i}).click();

    await authenticatedPage.getByText('Delete').click();

    // Confirm deletion in modal
    const deleteBtn = authenticatedPage.getByRole('button', {name: 'Delete'});
    await deleteBtn.click();

    // Team should be removed
    await expect(
      authenticatedPage.getByRole('cell', {name: team.name}),
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
    await api.team(org.name, 'permteam');
    await api.repository(org.name, 'permrepo');

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    const teamRow = authenticatedPage
      .getByRole('row')
      .filter({hasText: 'permteam'});
    await teamRow.getByRole('button', {name: /actions|kebab/i}).click();

    await authenticatedPage.getByText('Set repository permissions').click();

    await expect(
      authenticatedPage.getByText('Set repository permissions', {exact: false}),
    ).toBeVisible();
  });

  test('manage members link navigates to team page', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('tmmanage');
    await api.team(org.name, 'manageteam');

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    const teamLink = authenticatedPage.getByRole('link', {
      name: 'manageteam',
    });
    await expect(teamLink).toBeVisible();
    await teamLink.click();

    await expect(authenticatedPage).toHaveURL(
      new RegExp(`/organization/${org.name}/teams/manageteam`),
    );
  });
});
