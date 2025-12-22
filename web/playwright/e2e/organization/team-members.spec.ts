import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe('Manage Team Members', {tag: ['@organization', '@team']}, () => {
  test('navigates to manage team members and displays members', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('members');
    const team = await api.team(org.name, 'testteam');
    const robot = await api.robot(org.name, 'testrobot');
    await api.teamMember(org.name, team.name, robot.fullName);

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    // Locate the Teams tab panel for scoped selectors
    const tabPanel = authenticatedPage.getByRole('tabpanel', {
      name: 'Teams and membership',
    });
    const paginationInfo = tabPanel
      .locator('.pf-v5-c-pagination__total-items')
      .first();

    await authenticatedPage.getByRole('tab', {name: 'Teams'}).click();

    // Search for team
    await authenticatedPage.locator('#teams-view-search').fill(team.name);
    await expect(paginationInfo).toContainText('1 - 1 of 1', {timeout: 10000});

    // Open manage members
    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-manage-team-member-option`)
      .click();

    // Verify URL and member visible
    await expect(authenticatedPage).toHaveURL(
      new RegExp(`teams/${team.name}\\?tab=Teamsandmembership`),
    );
    // Use getByTestId to avoid matching multiple elements
    await expect(authenticatedPage.getByTestId(robot.fullName)).toBeVisible();
  });

  test('filters by team member and robot account toggle views', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('filter');
    const team = await api.team(org.name, 'filterteam');
    const robot = await api.robot(org.name, 'filterrobot');
    await api.teamMember(org.name, team.name, robot.fullName);

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    // Locate the Teams tab panel for scoped selectors
    const tabPanel = authenticatedPage.getByRole('tabpanel', {
      name: 'Teams and membership',
    });
    const paginationInfo = tabPanel
      .locator('.pf-v5-c-pagination__total-items')
      .first();

    await authenticatedPage.getByRole('tab', {name: 'Teams'}).click();
    await authenticatedPage.locator('#teams-view-search').fill(team.name);
    await expect(paginationInfo).toContainText('1 - 1 of 1', {timeout: 10000});
    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-manage-team-member-option`)
      .click();

    // Re-scope pagination to manage members view
    const manageMembersPagination = authenticatedPage
      .locator('.pf-v5-c-pagination__total-items')
      .first();

    // Test Team Member toggle - robot should not appear
    await authenticatedPage.getByTestId('Team Member').click();
    await authenticatedPage
      .locator('#team-member-search-input')
      .fill(robot.fullName);
    await expect(manageMembersPagination).toContainText('0 - 0 of 0');
    await authenticatedPage.locator('#team-member-search-input').clear();

    // Test Robot Accounts toggle - robot should appear
    await authenticatedPage.getByTestId('Robot Accounts').click();
    await authenticatedPage
      .locator('#team-member-search-input')
      .fill(robot.fullName);
    await expect(manageMembersPagination).toContainText('1 - 1 of 1');
  });

  test('updates team description', async ({authenticatedPage, api}) => {
    const org = await api.organization('desc');
    const team = await api.team(org.name, 'descteam');
    const teamDescription = 'Updated team description for testing';

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    // Locate the Teams tab panel for scoped selectors
    const tabPanel = authenticatedPage.getByRole('tabpanel', {
      name: 'Teams and membership',
    });
    const paginationInfo = tabPanel
      .locator('.pf-v5-c-pagination__total-items')
      .first();

    await authenticatedPage.getByRole('tab', {name: 'Teams'}).click();
    await authenticatedPage.locator('#teams-view-search').fill(team.name);
    await expect(paginationInfo).toContainText('1 - 1 of 1', {timeout: 10000});
    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-manage-team-member-option`)
      .click();

    await authenticatedPage.getByTestId('edit-team-description-btn').click();
    await authenticatedPage
      .getByTestId('team-description-text-area')
      .fill(teamDescription);
    await authenticatedPage.getByTestId('save-team-description-btn').click();

    // Use .last() to get the most recent success alert
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully updated team:${team.name} description`);
    await expect(
      authenticatedPage.getByTestId('team-description-text'),
    ).toContainText(teamDescription);
  });

  test('removes robot account from team', async ({authenticatedPage, api}) => {
    const org = await api.organization('remove');
    const team = await api.team(org.name, 'removeteam');
    const robot = await api.robot(org.name, 'removerobot');
    await api.teamMember(org.name, team.name, robot.fullName);

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    // Locate the Teams tab panel for scoped selectors
    const tabPanel = authenticatedPage.getByRole('tabpanel', {
      name: 'Teams and membership',
    });
    const paginationInfo = tabPanel
      .locator('.pf-v5-c-pagination__total-items')
      .first();

    await authenticatedPage.getByRole('tab', {name: 'Teams'}).click();
    await authenticatedPage.locator('#teams-view-search').fill(team.name);
    await expect(paginationInfo).toContainText('1 - 1 of 1', {timeout: 10000});
    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-manage-team-member-option`)
      .click();

    // Delete robot via UI
    await authenticatedPage
      .getByTestId(`${robot.fullName}-delete-icon`)
      .click();
    await authenticatedPage.getByTestId(`${robot.fullName}-del-btn`).click();

    // Use .last() to get the most recent success alert
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully deleted team member: ${robot.fullName}`);
  });

  test('adds new robot account to team via wizard', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('addrobot');
    const team = await api.team(org.name, 'addteam');
    const repo = await api.repository(org.name, 'testrepo');
    const robotShortname = uniqueName('newrobot').replace(/-/g, '_');

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    // Locate the Teams tab panel for scoped selectors
    const tabPanel = authenticatedPage.getByRole('tabpanel', {
      name: 'Teams and membership',
    });
    const paginationInfo = tabPanel
      .locator('.pf-v5-c-pagination__total-items')
      .first();

    await authenticatedPage.locator('#teams-view-search').fill(team.name);
    await expect(paginationInfo).toContainText('1 - 1 of 1', {timeout: 10000});
    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-manage-team-member-option`)
      .click();

    await authenticatedPage.getByTestId('add-new-member-button').click();
    await authenticatedPage.locator('#repository-creator-dropdown').click();
    await authenticatedPage.getByTestId('create-new-robot-accnt-btn').click();

    // Wizard: Name & Description
    await authenticatedPage
      .getByTestId('robot-wizard-form-name')
      .fill(robotShortname);
    await authenticatedPage
      .getByTestId('robot-wizard-form-description')
      .fill('Test robot description');
    await authenticatedPage.getByTestId('next-btn').click();

    // Wizard: Add to team (optional) - skip
    await authenticatedPage.getByTestId('next-btn').click();

    // Wizard: Add to repository
    await authenticatedPage.getByTestId(`checkbox-row-${repo.name}`).click();
    await authenticatedPage.getByTestId('next-btn').click();

    // Wizard: Default permissions - verify and skip
    await expect(authenticatedPage.getByTestId('applied-to-input')).toHaveValue(
      robotShortname,
    );
    await authenticatedPage.getByTestId('next-btn').click();

    // Wizard: Review and Finish
    await authenticatedPage.getByTestId('create-robot-submit').click();

    // Verify robot is selected and submit
    const robotFullName = `${org.name}+${robotShortname}`;
    await expect(
      authenticatedPage.locator('#repository-creator-dropdown input'),
    ).toHaveValue(robotFullName);
    await authenticatedPage.getByTestId('add-new-member-submit-btn').click();

    // Use .last() to get the most recent success alert
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully added "${robotFullName}" to team`);
    await expect(authenticatedPage.getByTestId(robotFullName)).toBeVisible();
  });

  test('adds existing user to team', async ({authenticatedPage, api}) => {
    const org = await api.organization('adduser');
    const team = await api.team(org.name, 'userteam');
    // Use the test user from global setup
    const userName = TEST_USERS.user.username;

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Teamsandmembership`,
    );

    // Locate the Teams tab panel for scoped selectors
    const tabPanel = authenticatedPage.getByRole('tabpanel', {
      name: 'Teams and membership',
    });
    const paginationInfo = tabPanel
      .locator('.pf-v5-c-pagination__total-items')
      .first();

    await authenticatedPage.locator('#teams-view-search').fill(team.name);
    await expect(paginationInfo).toContainText('1 - 1 of 1', {timeout: 10000});
    await authenticatedPage.getByTestId(`${team.name}-toggle-kebab`).click();
    await authenticatedPage
      .getByTestId(`${team.name}-manage-team-member-option`)
      .click();

    await authenticatedPage.getByTestId('add-new-member-button').click();
    // Click to open the dropdown, then type to search for user
    await authenticatedPage.locator('#repository-creator-dropdown').click();
    await authenticatedPage
      .locator('#repository-creator-dropdown input')
      .fill(userName);
    // Wait for search results and click on the user
    await authenticatedPage.getByTestId(userName).click();

    await expect(
      authenticatedPage.locator('#repository-creator-dropdown input'),
    ).toHaveValue(userName);
    await authenticatedPage.getByTestId('add-new-member-submit-btn').click();

    // Use .last() to get the most recent success alert
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully added "${userName}" to team`);
    await expect(authenticatedPage.getByTestId(userName)).toBeVisible();
  });
});
