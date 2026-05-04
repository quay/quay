import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import type {Page} from '@playwright/test';

async function navigateToTeamsTab(page: Page, orgName: string) {
  await page.goto(`/organization/${orgName}?tab=Teamsandmembership`);
  await page.locator('#Teams').click();
}

async function searchForTeam(page: Page, teamName: string) {
  await page.locator('#teams-view-search').fill(teamName);
  await expect(
    page.locator('.pf-v6-c-pagination__total-items').first(),
  ).toContainText('1 - 1 of 1', {timeout: 15000});
}

test.describe('Teams and Membership', {tag: ['@organization']}, () => {
  test('team search filter', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmorg');
    const team = await api.team(org.name, 'searchteam');

    await navigateToTeamsTab(authenticatedPage, org.name);

    await searchForTeam(authenticatedPage, team.name);
  });

  test('member search filter', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmorg');
    const memberTeam = await api.team(org.name, 'memberteam');
    await api.teamMember(org.name, memberTeam.name, TEST_USERS.user.username);

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.locator('#Members').click();

    await authenticatedPage
      .locator('#members-view-search')
      .fill(TEST_USERS.user.username);
    await expect(
      authenticatedPage.locator('.pf-v6-c-pagination__total-items').first(),
    ).toContainText('1 - 1 of 1', {timeout: 15000});
  });

  test('collaborator search filter', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmorg');
    const repo = await api.repository(org.name, 'collabsearch');
    await api.repositoryPermission(
      org.name,
      repo.name,
      'user',
      TEST_USERS.readonly.username,
      'read',
    );

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.locator('#Collaborators').click();

    await authenticatedPage
      .locator('#collaborators-view-search')
      .fill(TEST_USERS.readonly.username);
    await expect(
      authenticatedPage.locator('.pf-v6-c-pagination__total-items').first(),
    ).toContainText('1 - 1 of 1', {timeout: 15000});
  });

  test('create team via wizard', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmorg');
    const repo = await api.repository(org.name, 'wizardrepo');
    const teamName = uniqueName('wizteam');
    const teamDescription = 'team created by playwright wizard test';

    await navigateToTeamsTab(authenticatedPage, org.name);

    // Open create team modal
    await authenticatedPage.getByTestId('create-new-team-button').click();
    await authenticatedPage.getByTestId('new-team-name-input').fill(teamName);
    await authenticatedPage
      .getByTestId('new-team-description-input')
      .fill(teamDescription);
    await authenticatedPage.getByTestId('create-team-confirm').click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully created new team: ${teamName}`);

    // Wizard Step 1: Name & Description (pre-filled)
    await expect(
      authenticatedPage.getByTestId('create-team-wizard-form-name'),
    ).toHaveValue(teamName);
    await expect(
      authenticatedPage.getByTestId('create-team-wizard-form-description'),
    ).toHaveValue(teamDescription);
    await authenticatedPage.getByTestId('next-btn').click();

    // Wizard Step 2: Add to repository
    await authenticatedPage.getByTestId(`checkbox-row-${repo.name}`).click();
    await authenticatedPage.getByTestId('next-btn').click();

    // Wizard Step 3: Add team member
    await authenticatedPage.locator('#search-member-dropdown').click();
    await authenticatedPage
      .locator('#search-member-dropdown-input input')
      .fill(TEST_USERS.admin.username);
    await authenticatedPage.getByTestId(TEST_USERS.admin.username).click();
    await authenticatedPage.getByTestId('next-btn').click();

    // Wizard Step 4: Review and Finish
    await expect(
      authenticatedPage.getByTestId(`${teamName}-team-name-review`),
    ).toHaveValue(teamName);
    await authenticatedPage.getByTestId('review-and-finish-wizard-btn').click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText('Successfully added members to team');

    // Verify new team appears in search
    await authenticatedPage.locator('#teams-view-search').fill(teamName);
    await expect(
      authenticatedPage.locator('.pf-v6-c-pagination__total-items').first(),
    ).toContainText('1 - 1 of 1', {timeout: 15000});
  });

  test('update team role', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmorg');
    const team = await api.team(org.name, 'roleteam', 'member');

    await navigateToTeamsTab(authenticatedPage, org.name);
    await searchForTeam(authenticatedPage, team.name);

    await authenticatedPage
      .getByTestId(`${team.name}-team-dropdown-toggle`)
      .click();
    await authenticatedPage.getByTestId(`${team.name}-Creator`).click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Team role updated successfully for: ${team.name}`);
  });

  test('delete team', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmorg');
    const team = await api.team(org.name, 'delteam');

    await navigateToTeamsTab(authenticatedPage, org.name);
    await searchForTeam(authenticatedPage, team.name);

    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage.getByTestId(`${team.name}-del-option`).click();
    await authenticatedPage.getByTestId(`${team.name}-del-btn`).click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully deleted team: ${team.name}`);
  });

  test('delete collaborator', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmorg');
    const repo = await api.repository(org.name, 'delcollabsearch');
    await api.repositoryPermission(
      org.name,
      repo.name,
      'user',
      TEST_USERS.readonly.username,
      'read',
    );

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );
    await authenticatedPage.locator('#Collaborators').click();

    await authenticatedPage
      .getByTestId(`${TEST_USERS.readonly.username}-del-icon`)
      .click();
    await authenticatedPage
      .getByTestId(`${TEST_USERS.readonly.username}-del-btn`)
      .click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText('Successfully deleted collaborator');
  });

  test('set repository permissions for team', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('tmorg');
    const team = await api.team(org.name, 'repopermteam');
    const repo = await api.repository(org.name, 'repoperm');

    await navigateToTeamsTab(authenticatedPage, org.name);
    await searchForTeam(authenticatedPage, team.name);

    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-set-repo-perms-option`)
      .click();

    // Search for repo in modal
    const repoPermissionsDialog = authenticatedPage.getByRole('dialog');
    await repoPermissionsDialog
      .locator('#set-repo-perm-for-team-search')
      .fill(repo.name);
    await expect(
      repoPermissionsDialog.locator('.pf-v6-c-pagination__total-items'),
    ).toContainText('1 - 1 of 1', {timeout: 15000});

    // Change permission to Write
    await authenticatedPage
      .getByTestId(`${repo.name}-role-dropdown-toggle`)
      .click();
    await authenticatedPage.getByTestId(`${repo.name}-Write`).click();
    await authenticatedPage.locator('#update-team-repo-permissions').click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Updated repo perm for team: ${team.name} successfully`);
  });

  test('bulk update repository permissions for team', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('tmorg');
    const team = await api.team(org.name, 'bulkpermteam');
    await api.repository(org.name, 'bulkperm');

    await navigateToTeamsTab(authenticatedPage, org.name);
    await searchForTeam(authenticatedPage, team.name);

    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-set-repo-perms-option`)
      .click();

    // Bulk select all repos and change role via kebab
    await authenticatedPage
      .locator('[name="add-repository-bulk-select"]')
      .click();
    await authenticatedPage.locator('#toggle-bulk-perms-kebab').click();
    await authenticatedPage.getByTestId('bulk-perm-Write').click();
    await authenticatedPage.locator('#update-team-repo-permissions').click();

    await expect(
      authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
    ).toContainText(`Updated repo perm for team: ${team.name} successfully`);
  });

  test('navigate to team management page', async ({authenticatedPage, api}) => {
    const org = await api.organization('tmorg');
    const team = await api.team(org.name, 'navteam');

    await navigateToTeamsTab(authenticatedPage, org.name);
    await searchForTeam(authenticatedPage, team.name);

    // Click team name link
    await authenticatedPage
      .locator('td')
      .filter({hasText: team.name})
      .getByRole('link', {name: team.name})
      .click();

    await expect(authenticatedPage).toHaveURL(
      (url) => url.pathname === `/organization/${org.name}/teams/${team.name}`,
    );
    await expect(authenticatedPage.getByTestId('teamname-title')).toContainText(
      team.name,
    );
  });
});
