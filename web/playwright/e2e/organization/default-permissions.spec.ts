import {test, expect, uniqueName} from '../../fixtures';

test.describe('Default Permissions', {tag: ['@organization']}, () => {
  test('search filter works', async ({authenticatedPage, api}) => {
    // Setup test resources
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'arsenal');
    const robot = await api.robot(org.name, 'testrobot');

    // Create a default permission via API
    await api.prototype(
      org.name,
      'read',
      {name: team.name, kind: 'team'},
      {
        name: robot.fullName,
      },
    );

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Defaultpermissions`,
    );

    // Filter for the created default permission
    const searchInput = authenticatedPage.locator(
      '#default-permissions-search',
    );

    // Locate pagination within the Default Permissions tab panel
    const tabPanel = authenticatedPage.getByRole('tabpanel', {
      name: 'Default permissions',
    });
    const paginationInfo = tabPanel
      .locator('.pf-v5-c-pagination__total-items')
      .first();

    // Wait for initial data load (with extended timeout for API response)
    await expect(paginationInfo).toContainText('1 - 1 of 1', {
      timeout: 15000,
    });

    // Type search and verify filtering
    await searchInput.fill(robot.fullName);
    await expect(paginationInfo).toContainText('1 - 1 of 1');

    // Now filter for non-existent
    await searchInput.fill('somethingrandome');
    await expect(paginationInfo).toContainText('0 - 0 of 0');
  });

  test('can update permission for default permission', async ({
    authenticatedPage,
    api,
  }) => {
    // Setup test resources
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'arsenal');
    const robot = await api.robot(org.name, 'testrobot');

    // Create a default permission via API
    await api.prototype(
      org.name,
      'read',
      {name: team.name, kind: 'team'},
      {
        name: robot.fullName,
      },
    );

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Defaultpermissions`,
    );

    // Scope to the tab panel for more reliable locators
    const tabPanel = authenticatedPage.getByRole('tabpanel', {
      name: 'Default permissions',
    });

    // Search for the permission
    const searchInput = authenticatedPage.locator(
      '#default-permissions-search',
    );
    await searchInput.fill(robot.fullName);
    await expect(
      tabPanel.locator('.pf-v5-c-pagination__total-items').first(),
    ).toContainText('1 - 1 of 1');

    // Click on the permission dropdown toggle
    await authenticatedPage
      .getByTestId(`${robot.fullName}-permission-dropdown-toggle`)
      .click();

    // Select Write permission (key is uppercase)
    await authenticatedPage.getByTestId(`${robot.fullName}-WRITE`).click();

    // Verify success alert (use .last() to get most recent)
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText('Permission updated successfully');
  });

  test('can delete default permission', async ({authenticatedPage, api}) => {
    // Setup test resources
    const org = await api.organization('testorg');
    const team = await api.team(org.name, 'arsenal');
    const robot = await api.robot(org.name, 'testrobot');

    // Create a default permission via API
    await api.prototype(
      org.name,
      'read',
      {name: team.name, kind: 'team'},
      {
        name: robot.fullName,
      },
    );

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Defaultpermissions`,
    );

    // Scope to the tab panel
    const tabPanel = authenticatedPage.getByRole('tabpanel', {
      name: 'Default permissions',
    });

    // Search for the permission
    const searchInput = authenticatedPage.locator(
      '#default-permissions-search',
    );
    await searchInput.fill(robot.fullName);
    await expect(
      tabPanel.locator('.pf-v5-c-pagination__total-items').first(),
    ).toContainText('1 - 1 of 1');

    // Click kebab menu within the table
    const table = authenticatedPage.getByTestId('default-permissions-table');
    await table.getByTestId(`${robot.fullName}-toggle-kebab`).click();

    // Click delete option
    await table.getByTestId(`${robot.fullName}-del-option`).click();

    // Verify success alert (use .last() to get most recent)
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(
      `Permission created by: ${robot.fullName} successfully deleted`,
    );
  });

  // Parameterized test for creating default permissions
  ['Specific user', 'Anyone'].forEach((userType) => {
    test(`can create default permission for ${userType}`, async ({
      authenticatedPage,
      api,
    }) => {
      // Setup test resources
      const org = await api.organization('testorg');
      const team1 = await api.team(org.name, 'team1');
      const team2 = await api.team(org.name, 'team2');
      const robot = await api.robot(org.name, 'testrobot2');

      const teamName = userType === 'Specific user' ? team1.name : team2.name;

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Defaultpermissions`,
      );

      // Click create button
      await authenticatedPage
        .getByTestId('create-default-permissions-btn')
        .click();

      // Select user type
      await authenticatedPage.getByTestId(userType).click();

      // If Specific user, select the robot
      if (userType === 'Specific user') {
        await authenticatedPage.locator('#repository-creator-dropdown').click();
        await authenticatedPage
          .getByTestId(`${robot.fullName}-robot-accnt`)
          .click();
      }

      // Select team from applied-to dropdown
      await authenticatedPage.locator('#applied-to-dropdown').click();
      await authenticatedPage.getByTestId(`${teamName}-team`).click();

      // Select permission level
      await authenticatedPage
        .getByTestId('create-default-permission-dropdown-toggle')
        .click();
      await authenticatedPage
        .getByTestId('create-default-permission-dropdown')
        .getByText('Write')
        .click();

      // Click create
      await authenticatedPage.getByTestId('create-permission-button').click();

      // Verify success alert (use .last() to get most recent)
      const successAlert = authenticatedPage
        .locator('.pf-v5-c-alert.pf-m-success')
        .last();
      if (userType === 'Specific user') {
        await expect(successAlert).toContainText(
          `Successfully created default permission for creator: ${robot.fullName}`,
        );
      } else {
        await expect(successAlert).toContainText(
          `Successfully applied default permission to: ${teamName}`,
        );
      }
    });
  });

  test('can create default permission with new team and existing robot', async ({
    authenticatedPage,
    api,
  }) => {
    // Setup test resources
    const org = await api.organization('testorg');
    const repo = await api.repository(org.name, 'testrepo');
    const robot = await api.robot(org.name, 'testrobot2');

    const newTeamName = uniqueName('newteam').substring(0, 20);
    const teamDescription = 'underdog club';

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Defaultpermissions`,
    );

    // Click create button
    await authenticatedPage
      .getByTestId('create-default-permissions-btn')
      .click();

    // Select Anyone
    await authenticatedPage.getByTestId('Anyone').click();

    // Open applied-to dropdown and create new team
    await authenticatedPage.locator('#applied-to-dropdown').click();
    await authenticatedPage.getByTestId('create-new-team-btn').click();

    // Fill create team modal
    await authenticatedPage
      .getByTestId('new-team-name-input')
      .fill(newTeamName);
    await authenticatedPage
      .getByTestId('new-team-description-input')
      .fill(teamDescription);
    await authenticatedPage.getByTestId('create-team-confirm').click();

    // Verify team creation success alert
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully created new team: ${newTeamName}`);

    // Team wizard - Step: Name & Description (verify pre-filled)
    await expect(
      authenticatedPage.getByTestId('create-team-wizard-form-name'),
    ).toHaveValue(newTeamName);
    await expect(
      authenticatedPage.getByTestId('create-team-wizard-form-description'),
    ).toHaveValue(teamDescription);
    await authenticatedPage.getByTestId('next-btn').click();

    // Step: Add to repository
    await authenticatedPage.getByTestId(`checkbox-row-${repo.name}`).click();
    await expect(
      authenticatedPage.getByTestId(`${repo.name}-permission-dropdown-toggle`),
    ).toContainText('Read');
    await authenticatedPage.getByTestId('next-btn').click();

    // Step: Add team member
    await authenticatedPage.locator('#search-member-dropdown').click();
    await authenticatedPage
      .getByTestId(`${robot.fullName}-robot-accnt`)
      .click();
    await authenticatedPage.getByTestId('next-btn').click();

    // Step: Review and Finish
    await expect(
      authenticatedPage.getByTestId(`${newTeamName}-team-name-review`),
    ).toHaveValue(newTeamName);
    await expect(
      authenticatedPage.getByTestId(`${teamDescription}-team-descr-review`),
    ).toHaveValue(teamDescription);
    await expect(
      authenticatedPage.getByTestId('selected-repos-review'),
    ).toHaveValue(repo.name);
    await expect(
      authenticatedPage.getByTestId('selected-team-members-review'),
    ).toHaveValue(robot.fullName);
    await authenticatedPage.getByTestId('review-and-finish-wizard-btn').click();

    // Verify team is selected in dropdown
    await expect(
      authenticatedPage.locator('#applied-to-dropdown input'),
    ).toHaveValue(newTeamName);

    // Select permission level
    await authenticatedPage
      .getByTestId('create-default-permission-dropdown-toggle')
      .click();
    await authenticatedPage
      .getByTestId('create-default-permission-dropdown')
      .getByText('Write')
      .click();

    // Click create
    await authenticatedPage.getByTestId('create-permission-button').click();

    // Verify success alert
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toBeVisible();
  });

  test('can create default permission with new team and new robot', async ({
    authenticatedPage,
    api,
  }) => {
    // Setup test resources
    const org = await api.organization('testorg');
    const repo = await api.repository(org.name, 'testrepo');

    const newTeamName = uniqueName('newteam').substring(0, 20);
    const teamDescription = 'relegation club';
    // Robot names must match ^[a-z][a-z0-9_]{1,254}$ - no dashes allowed
    const newRobotShortname = `newbot${Date.now()}`.substring(0, 20);
    const newRobotDescription = 'premier league manager';

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Defaultpermissions`,
    );

    // Click create button
    await authenticatedPage
      .getByTestId('create-default-permissions-btn')
      .click();

    // Select Anyone
    await authenticatedPage.getByTestId('Anyone').click();

    // Open applied-to dropdown and create new team
    await authenticatedPage.locator('#applied-to-dropdown').click();
    await authenticatedPage.getByTestId('create-new-team-btn').click();

    // Fill create team modal
    await authenticatedPage
      .getByTestId('new-team-name-input')
      .fill(newTeamName);
    await authenticatedPage
      .getByTestId('new-team-description-input')
      .fill(teamDescription);
    await authenticatedPage.getByTestId('create-team-confirm').click();

    // Verify team creation success alert
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(`Successfully created new team: ${newTeamName}`);

    // Team wizard - Step: Name & Description
    await expect(
      authenticatedPage.getByTestId('create-team-wizard-form-name'),
    ).toHaveValue(newTeamName);
    await expect(
      authenticatedPage.getByTestId('create-team-wizard-form-description'),
    ).toHaveValue(teamDescription);
    await authenticatedPage.getByTestId('next-btn').click();

    // Step: Add to repository
    await authenticatedPage.getByTestId(`checkbox-row-${repo.name}`).click();
    await authenticatedPage.getByTestId('next-btn').click();

    // Step: Add team member - create new robot
    await authenticatedPage.locator('#search-member-dropdown').click();
    await authenticatedPage.getByTestId('create-new-robot-accnt-btn').click();
    await authenticatedPage
      .getByTestId('new-robot-name-input')
      .fill(newRobotShortname);
    await authenticatedPage
      .getByTestId('new-robot-description-input')
      .fill(newRobotDescription);
    await authenticatedPage
      .getByTestId('create-robot-accnt-drawer-btn')
      .click();

    await authenticatedPage.getByTestId('next-btn').click();

    // Step: Review and Finish
    await expect(
      authenticatedPage.getByTestId(`${newTeamName}-team-name-review`),
    ).toHaveValue(newTeamName);
    await expect(
      authenticatedPage.getByTestId(`${teamDescription}-team-descr-review`),
    ).toHaveValue(teamDescription);
    await expect(
      authenticatedPage.getByTestId('selected-repos-review'),
    ).toHaveValue(repo.name);
    await expect(
      authenticatedPage.getByTestId('selected-team-members-review'),
    ).toHaveValue(`${org.name}+${newRobotShortname}`);
    await authenticatedPage.getByTestId('review-and-finish-wizard-btn').click();

    // Verify team is selected in dropdown
    await expect(
      authenticatedPage.locator('#applied-to-dropdown input'),
    ).toHaveValue(newTeamName);

    // Select permission level
    await authenticatedPage
      .getByTestId('create-default-permission-dropdown-toggle')
      .click();
    await authenticatedPage
      .getByTestId('create-default-permission-dropdown')
      .getByText('Write')
      .click();

    // Click create
    await authenticatedPage.getByTestId('create-permission-button').click();

    // Verify success alert
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toBeVisible();
  });

  test('can create default permission for repository creator with new robot', async ({
    authenticatedPage,
    api,
  }) => {
    // Setup test resources
    const org = await api.organization('testorg');
    const addToTeam = await api.team(org.name, 'team1');
    const appliedToTeam = await api.team(org.name, 'team2');
    const addToRepo = await api.repository(org.name, 'testrepo');

    // Robot names must match ^[a-z][a-z0-9_]{1,254}$ - no dashes allowed
    const newRobotShortname = `newbot${Date.now()}`.substring(0, 20);
    const newRobotDescription = 'premier league manager';

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Defaultpermissions`,
    );

    // Click create button
    await authenticatedPage
      .getByTestId('create-default-permissions-btn')
      .click();

    // Select Specific user
    await authenticatedPage.getByTestId('Specific user').click();

    // Open repository creator dropdown and create new robot
    await authenticatedPage.locator('#repository-creator-dropdown').click();
    await authenticatedPage.getByTestId('create-new-robot-accnt-btn').click();

    // Robot wizard - Step: Name & Description
    await authenticatedPage
      .getByTestId('new-robot-name-input')
      .fill(newRobotShortname);
    await authenticatedPage
      .getByTestId('new-robot-description-input')
      .fill(newRobotDescription);
    await authenticatedPage.getByTestId('next-btn').click();

    // Step: Add to team (optional)
    await authenticatedPage
      .getByTestId(`checkbox-row-${addToTeam.name}`)
      .click();
    await authenticatedPage.getByTestId('next-btn').click();

    // Step: Add to repository
    await authenticatedPage
      .getByTestId(`checkbox-row-${addToRepo.name}`)
      .click();
    await authenticatedPage.getByTestId('next-btn').click();

    // Step: Default permissions (optional)
    await expect(authenticatedPage.getByTestId('applied-to-input')).toHaveValue(
      newRobotShortname,
    );
    await authenticatedPage.getByTestId('next-btn').click();

    // Step: Review and Finish
    await authenticatedPage.getByTestId('review-and-finish-btn').click();

    // Verify robot creation success alert
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(
      `Successfully created robot account with robot name: ${org.name}+${newRobotShortname}`,
    );

    // Verify robot is selected in dropdown
    await expect(
      authenticatedPage.locator('#repository-creator-dropdown input'),
    ).toHaveValue(`${org.name}+${newRobotShortname}`);

    // Select applied-to team
    await authenticatedPage.locator('#applied-to-dropdown').click();
    await authenticatedPage.getByTestId(`${appliedToTeam.name}-team`).click();

    // Select permission level
    await authenticatedPage
      .getByTestId('create-default-permission-dropdown-toggle')
      .click();
    await authenticatedPage
      .getByTestId('create-default-permission-dropdown')
      .getByText('Write')
      .click();

    // Click create
    await authenticatedPage.getByTestId('create-permission-button').click();

    // Verify success alert
    await expect(
      authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
    ).toContainText(
      `Successfully created default permission for creator: ${org.name}+${newRobotShortname}`,
    );
  });

  test('can bulk delete default permissions', async ({
    authenticatedPage,
    api,
  }) => {
    // Create organization for bulk delete test
    const org = await api.organization('bulkorg');
    const robot1 = await api.robot(org.name, 'robot1');
    const robot2 = await api.robot(org.name, 'robot2');
    const team = await api.team(org.name, 'teamone');

    // Create two prototypes
    await api.prototype(
      org.name,
      'read',
      {name: team.name, kind: 'team'},
      {
        name: robot1.fullName,
      },
    );
    await api.prototype(
      org.name,
      'write',
      {name: team.name, kind: 'team'},
      {
        name: robot2.fullName,
      },
    );

    await authenticatedPage.goto(
      `/organization/${org.name}?tab=Defaultpermissions`,
    );

    // Scope to the tab panel
    const tabPanel = authenticatedPage.getByRole('tabpanel', {
      name: 'Default permissions',
    });
    const paginationInfo = tabPanel
      .locator('.pf-v5-c-pagination__total-items')
      .first();

    // Search for prototypes in this org
    const searchInput = authenticatedPage.locator(
      '#default-permissions-search',
    );
    await searchInput.fill(org.name);
    await expect(paginationInfo).toContainText('1 - 2 of 2');

    // Select all using bulk select checkbox
    await authenticatedPage
      .locator('[name="default-perm-bulk-select"]')
      .click();

    // Click bulk delete icon
    await authenticatedPage
      .getByTestId('default-perm-bulk-delete-icon')
      .click();

    // Type confirmation
    await authenticatedPage
      .locator('#delete-confirmation-input')
      .fill('confirm');

    // Click confirm delete
    await authenticatedPage.getByTestId('bulk-delete-confirm-btn').click();

    // Verify items are deleted
    await searchInput.fill('');
    await searchInput.fill(org.name);
    await expect(paginationInfo).toContainText('0 - 0 of 0');
  });
});
