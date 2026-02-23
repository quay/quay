import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import type {Page} from '@playwright/test';

async function navigateToManageTeamMembers(
  page: Page,
  orgName: string,
  teamName: string,
) {
  await page.goto(`/organization/${orgName}?tab=Teamsandmembership`);
  await page.locator('#Teams').click();

  await page.locator('#teams-view-search').fill(teamName);
  await expect(
    page.locator('.pf-v5-c-pagination__total-items').first(),
  ).toContainText('1 - 1 of 1', {timeout: 15000});

  await page.getByTestId(`${teamName}-toggle-kebab`).click();
  await page.getByTestId(`${teamName}-manage-team-member-option`).click();
}

test.describe('Manage Team Members', {tag: ['@organization']}, () => {
  test('can search for member', async ({authenticatedPage, api}) => {
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'searchteam');
    await api.teamMember(org.name, team.name, TEST_USERS.user.username);

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await expect(authenticatedPage).toHaveURL(
      new RegExp(`teams/${team.name}\\?tab=Teamsandmembership`),
    );
    await expect(
      authenticatedPage.locator('[data-label="Team member"]'),
    ).toContainText(TEST_USERS.user.username);
  });

  test('team member filter toggle', async ({authenticatedPage, api}) => {
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'filterteam');
    const robot = await api.robot(org.name, 'filterbot');
    await api.teamMember(org.name, team.name, TEST_USERS.user.username);
    await api.teamMember(org.name, team.name, robot.fullName);

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await authenticatedPage.getByTestId('Team Member').click();

    const searchInput = authenticatedPage.locator('#team-member-search-input');
    const paginationInfo = authenticatedPage
      .locator('.pf-v5-c-pagination__total-items')
      .first();

    // Verify team member is shown
    await searchInput.fill(TEST_USERS.user.username);
    await expect(paginationInfo).toContainText('1 - 1 of 1');

    // Verify robot account is not shown
    await searchInput.fill(robot.fullName);
    await expect(paginationInfo).toContainText('0 - 0 of 0');
  });

  test('robot accounts filter toggle', async ({authenticatedPage, api}) => {
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'robotfilter');
    const robot = await api.robot(org.name, 'robotbot');
    await api.teamMember(org.name, team.name, TEST_USERS.user.username);
    await api.teamMember(org.name, team.name, robot.fullName);

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await authenticatedPage.getByTestId('Robot Accounts').click();

    const searchInput = authenticatedPage.locator('#team-member-search-input');
    const paginationInfo = authenticatedPage
      .locator('.pf-v5-c-pagination__total-items')
      .first();

    // Verify robot account is shown
    await searchInput.fill(robot.fullName);
    await expect(paginationInfo).toContainText('1 - 1 of 1');

    // Verify team member is not shown
    await searchInput.fill(TEST_USERS.user.username);
    await expect(paginationInfo).toContainText('0 - 0 of 0');
  });

  test('can update team description', async ({authenticatedPage, api}) => {
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'descrteam');
    const teamDescription = 'Updated team description for testing';

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await authenticatedPage.getByTestId('edit-team-description-btn').click();
    await authenticatedPage
      .getByTestId('team-description-text-area')
      .fill(teamDescription);
    await authenticatedPage.getByTestId('save-team-description-btn').click();

    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully updated team:${team.name} description`);
    await expect(
      authenticatedPage.getByTestId('team-description-text'),
    ).toContainText(teamDescription);
  });

  test('can delete robot from team', async ({authenticatedPage, api}) => {
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'delrobotteam');
    const robot = await api.robot(org.name, 'delbot');
    await api.teamMember(org.name, team.name, robot.fullName);

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await authenticatedPage
      .getByTestId(`${robot.fullName}-delete-icon`)
      .click();
    await authenticatedPage.getByTestId(`${robot.fullName}-del-btn`).click();

    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully deleted team member: ${robot.fullName}`);
  });

  test('can add new robot via wizard', async ({authenticatedPage, api}) => {
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'addrobotteam');
    const repo = await api.repository(org.name, 'wizardrepo');
    // Robot names must match ^[a-z][a-z0-9_]{1,254}$
    const newRobotName = `testbot${Date.now()}`.substring(0, 20);
    const newRobotDescription = 'robot created via wizard';

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await authenticatedPage.getByTestId('add-new-member-button').click();

    await authenticatedPage.locator('#repository-creator-dropdown').click();
    await authenticatedPage.getByTestId('create-new-robot-accnt-btn').click();

    // Step 1: Name & Description
    await authenticatedPage
      .getByTestId('robot-wizard-form-name')
      .fill(newRobotName);
    await authenticatedPage
      .getByTestId('robot-wizard-form-description')
      .fill(newRobotDescription);
    await authenticatedPage.getByTestId('next-btn').click();

    // Step 2: Add to team (skip)
    await authenticatedPage.getByTestId('next-btn').click();

    // Step 3: Add to repository
    await authenticatedPage.getByTestId(`checkbox-row-${repo.name}`).click();
    await authenticatedPage.getByTestId('next-btn').click();

    // Step 4: Default permissions
    await expect(authenticatedPage.getByTestId('applied-to-input')).toHaveValue(
      newRobotName,
    );
    await authenticatedPage.getByTestId('next-btn').click();

    // Step 5: Review and Finish
    await authenticatedPage.getByTestId('create-robot-submit').click();

    // Verify robot is auto-selected in dropdown
    await expect(
      authenticatedPage.locator('#repository-creator-dropdown input'),
    ).toHaveValue(`${org.name}+${newRobotName}`);

    // Submit add member
    await authenticatedPage.getByTestId('add-new-member-submit-btn').click();

    // Verify success
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully added "${org.name}+${newRobotName}" to team`);
    await expect(
      authenticatedPage.getByTestId(`${org.name}+${newRobotName}`),
    ).toContainText(`${org.name}+${newRobotName}`);
  });

  test('can add user to team', async ({authenticatedPage, api}) => {
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'adduserteam');
    const userToAdd = TEST_USERS.admin.username;

    await navigateToManageTeamMembers(authenticatedPage, org.name, team.name);

    await authenticatedPage.getByTestId('add-new-member-button').click();

    await authenticatedPage.locator('#repository-creator-dropdown').click();
    await authenticatedPage
      .locator('#repository-creator-dropdown input')
      .fill(userToAdd);
    await authenticatedPage.getByTestId(userToAdd).click();

    // Verify user is selected in dropdown
    await expect(
      authenticatedPage.locator('#repository-creator-dropdown input'),
    ).toHaveValue(userToAdd);

    // Submit add member
    await authenticatedPage.getByTestId('add-new-member-submit-btn').click();

    // Verify success
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully added "${userToAdd}" to team`);
    await expect(authenticatedPage.getByTestId(userToAdd)).toContainText(
      userToAdd,
    );
  });
});
