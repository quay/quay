import {test, expect, uniqueName} from '../../fixtures';
import {ApiClient} from '../../utils/api';

/**
 * Helper to set up a test organization with teams and robots.
 * Returns cleanup function and test data.
 */
async function setupTestOrg(api: ApiClient) {
  const orgName = uniqueName('testorg');
  const createdRobots: string[] = [];
  const createdTeams: string[] = [];

  // Create organization
  await api.createOrganization(orgName);

  // Create teams for testing
  await api.createTeam(orgName, 'arsenal', 'member');
  createdTeams.push('arsenal');
  await api.createTeam(orgName, 'liverpool', 'member');
  createdTeams.push('liverpool');

  // Create robots for testing
  await api.createRobot(orgName, 'testrobot', 'Test robot 1');
  createdRobots.push('testrobot');
  await api.createRobot(orgName, 'testrobot2', 'Test robot 2');
  createdRobots.push('testrobot2');

  // Create repository for wizard tests
  await api.createRepository(orgName, 'premierleague', 'private');

  const cleanup = async () => {
    // Delete organization (this also deletes repos, teams, robots, prototypes)
    try {
      await api.deleteOrganization(orgName);
    } catch {
      // Already deleted
    }
  };

  return {
    orgName,
    createdRobots,
    createdTeams,
    cleanup,
  };
}

test.describe('Default Permissions', {tag: ['@organization']}, () => {
  test('search filter works', async ({
    authenticatedPage,
    authenticatedRequest,
  }) => {
    const api = new ApiClient(authenticatedRequest);
    const {orgName, cleanup} = await setupTestOrg(api);

    try {
      const robotName = `${orgName}+testrobot`;

      // Create a default permission via API first
      await api.createPrototype(
        orgName,
        'read',
        {name: 'arsenal', kind: 'team'},
        {name: robotName},
      );

      await authenticatedPage.goto(
        `/organization/${orgName}?tab=Defaultpermissions`,
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
      await searchInput.fill(robotName);
      await expect(paginationInfo).toContainText('1 - 1 of 1');

      // Now filter for non-existent
      await searchInput.fill('somethingrandome');
      await expect(paginationInfo).toContainText('0 - 0 of 0');
    } finally {
      await cleanup();
    }
  });

  test('can update permission for default permission', async ({
    authenticatedPage,
    authenticatedRequest,
  }) => {
    const api = new ApiClient(authenticatedRequest);
    const {orgName, cleanup} = await setupTestOrg(api);

    try {
      const robotName = `${orgName}+testrobot`;

      // Create a default permission via API
      await api.createPrototype(
        orgName,
        'read',
        {name: 'arsenal', kind: 'team'},
        {name: robotName},
      );

      await authenticatedPage.goto(
        `/organization/${orgName}?tab=Defaultpermissions`,
      );

      // Scope to the tab panel for more reliable locators
      const tabPanel = authenticatedPage.getByRole('tabpanel', {
        name: 'Default permissions',
      });

      // Search for the permission
      const searchInput = authenticatedPage.locator(
        '#default-permissions-search',
      );
      await searchInput.fill(robotName);
      await expect(
        tabPanel.locator('.pf-v5-c-pagination__total-items').first(),
      ).toContainText('1 - 1 of 1');

      // Click on the permission dropdown toggle
      await authenticatedPage
        .getByTestId(`${robotName}-permission-dropdown-toggle`)
        .click();

      // Select Write permission (key is uppercase)
      await authenticatedPage.getByTestId(`${robotName}-WRITE`).click();

      // Verify success alert (use .last() to get most recent)
      await expect(
        authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
      ).toContainText('Permission updated successfully');
    } finally {
      await cleanup();
    }
  });

  test('can delete default permission', async ({
    authenticatedPage,
    authenticatedRequest,
  }) => {
    const api = new ApiClient(authenticatedRequest);
    const {orgName, cleanup} = await setupTestOrg(api);

    try {
      const robotName = `${orgName}+testrobot`;

      // Create a default permission via API
      await api.createPrototype(
        orgName,
        'read',
        {name: 'arsenal', kind: 'team'},
        {name: robotName},
      );

      await authenticatedPage.goto(
        `/organization/${orgName}?tab=Defaultpermissions`,
      );

      // Scope to the tab panel
      const tabPanel = authenticatedPage.getByRole('tabpanel', {
        name: 'Default permissions',
      });

      // Search for the permission
      const searchInput = authenticatedPage.locator(
        '#default-permissions-search',
      );
      await searchInput.fill(robotName);
      await expect(
        tabPanel.locator('.pf-v5-c-pagination__total-items').first(),
      ).toContainText('1 - 1 of 1');

      // Click kebab menu within the table
      const table = authenticatedPage.getByTestId('default-permissions-table');
      await table.getByTestId(`${robotName}-toggle-kebab`).click();

      // Click delete option
      await table.getByTestId(`${robotName}-del-option`).click();

      // Verify success alert (use .last() to get most recent)
      await expect(
        authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
      ).toContainText(
        `Permission created by: ${robotName} successfully deleted`,
      );
    } finally {
      await cleanup();
    }
  });

  // Parameterized test for creating default permissions
  ['Specific user', 'Anyone'].forEach((userType) => {
    test(`can create default permission for ${userType}`, async ({
      authenticatedPage,
      authenticatedRequest,
    }) => {
      const api = new ApiClient(authenticatedRequest);
      const {orgName, cleanup} = await setupTestOrg(api);

      try {
        const robotName = `${orgName}+testrobot2`;
        const teamName = userType === 'Specific user' ? 'arsenal' : 'liverpool';

        await authenticatedPage.goto(
          `/organization/${orgName}?tab=Defaultpermissions`,
        );

        // Click create button
        await authenticatedPage
          .getByTestId('create-default-permissions-btn')
          .click();

        // Select user type
        await authenticatedPage.getByTestId(userType).click();

        // If Specific user, select the robot
        if (userType === 'Specific user') {
          await authenticatedPage
            .locator('#repository-creator-dropdown')
            .click();
          await authenticatedPage
            .getByTestId(`${robotName}-robot-accnt`)
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
            `Successfully created default permission for creator: ${robotName}`,
          );
        } else {
          await expect(successAlert).toContainText(
            `Successfully applied default permission to: ${teamName}`,
          );
        }
      } finally {
        await cleanup();
      }
    });
  });

  test('can create default permission with new team and existing robot', async ({
    authenticatedPage,
    authenticatedRequest,
  }) => {
    const api = new ApiClient(authenticatedRequest);
    const {orgName, cleanup} = await setupTestOrg(api);

    try {
      const newTeamName = uniqueName('burnley').substring(0, 20);
      const teamDescription = 'underdog club';
      const repoName = 'premierleague';
      const robotName = `${orgName}+testrobot2`;

      await authenticatedPage.goto(
        `/organization/${orgName}?tab=Defaultpermissions`,
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
      await authenticatedPage.getByTestId(`checkbox-row-${repoName}`).click();
      await expect(
        authenticatedPage.getByTestId(`${repoName}-permission-dropdown-toggle`),
      ).toContainText('Read');
      await authenticatedPage.getByTestId('next-btn').click();

      // Step: Add team member
      await authenticatedPage.locator('#search-member-dropdown').click();
      await authenticatedPage.getByTestId(`${robotName}-robot-accnt`).click();
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
      ).toHaveValue(repoName);
      await expect(
        authenticatedPage.getByTestId('selected-team-members-review'),
      ).toHaveValue(robotName);
      await authenticatedPage
        .getByTestId('review-and-finish-wizard-btn')
        .click();

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
    } finally {
      await cleanup();
    }
  });

  test('can create default permission with new team and new robot', async ({
    authenticatedPage,
    authenticatedRequest,
  }) => {
    const api = new ApiClient(authenticatedRequest);
    const {orgName, cleanup} = await setupTestOrg(api);

    try {
      const newTeamName = uniqueName('fulham').substring(0, 20);
      const teamDescription = 'relegation club';
      const repoName = 'premierleague';
      // Robot names must match ^[a-z][a-z0-9_]{1,254}$ - no dashes allowed
      const newRobotShortname = `wengerbot${Date.now()}`.substring(0, 20);
      const newRobotDescription = 'premier league manager';

      await authenticatedPage.goto(
        `/organization/${orgName}?tab=Defaultpermissions`,
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
      await authenticatedPage.getByTestId(`checkbox-row-${repoName}`).click();
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
      ).toHaveValue(repoName);
      await expect(
        authenticatedPage.getByTestId('selected-team-members-review'),
      ).toHaveValue(`${orgName}+${newRobotShortname}`);
      await authenticatedPage
        .getByTestId('review-and-finish-wizard-btn')
        .click();

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
    } finally {
      await cleanup();
    }
  });

  test('can create default permission for repository creator with new robot', async ({
    authenticatedPage,
    authenticatedRequest,
  }) => {
    const api = new ApiClient(authenticatedRequest);
    const {orgName, cleanup} = await setupTestOrg(api);

    try {
      // Robot names must match ^[a-z][a-z0-9_]{1,254}$ - no dashes allowed
      const newRobotShortname = `kloppbot${Date.now()}`.substring(0, 20);
      const newRobotDescription = 'premier league manager';
      const addToTeam = 'arsenal';
      const addToRepo = 'premierleague';
      const appliedToTeam = 'liverpool';

      await authenticatedPage.goto(
        `/organization/${orgName}?tab=Defaultpermissions`,
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
      await authenticatedPage.getByTestId(`checkbox-row-${addToTeam}`).click();
      await authenticatedPage.getByTestId('next-btn').click();

      // Step: Add to repository
      await authenticatedPage.getByTestId(`checkbox-row-${addToRepo}`).click();
      await authenticatedPage.getByTestId('next-btn').click();

      // Step: Default permissions (optional)
      await expect(
        authenticatedPage.getByTestId('applied-to-input'),
      ).toHaveValue(newRobotShortname);
      await authenticatedPage.getByTestId('next-btn').click();

      // Step: Review and Finish
      await authenticatedPage.getByTestId('review-and-finish-btn').click();

      // Verify robot creation success alert
      await expect(
        authenticatedPage.locator('.pf-v5-c-alert.pf-m-success').last(),
      ).toContainText(
        `Successfully created robot account with robot name: ${orgName}+${newRobotShortname}`,
      );

      // Verify robot is selected in dropdown
      await expect(
        authenticatedPage.locator('#repository-creator-dropdown input'),
      ).toHaveValue(`${orgName}+${newRobotShortname}`);

      // Select applied-to team
      await authenticatedPage.locator('#applied-to-dropdown').click();
      await authenticatedPage.getByTestId(`${appliedToTeam}-team`).click();

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
        `Successfully created default permission for creator: ${orgName}+${newRobotShortname}`,
      );
    } finally {
      await cleanup();
    }
  });

  test('can bulk delete default permissions', async ({
    authenticatedPage,
    authenticatedRequest,
  }) => {
    const api = new ApiClient(authenticatedRequest);
    const bulkOrgName = uniqueName('bulkorg');

    // Create organization for bulk delete test
    await api.createOrganization(bulkOrgName);

    try {
      // Create robots and teams in the new org
      await api.createRobot(bulkOrgName, 'robot1');
      await api.createRobot(bulkOrgName, 'robot2');
      await api.createTeam(bulkOrgName, 'teamone', 'member');

      // Create two prototypes
      const robot1Name = `${bulkOrgName}+robot1`;
      const robot2Name = `${bulkOrgName}+robot2`;

      await api.createPrototype(
        bulkOrgName,
        'read',
        {name: 'teamone', kind: 'team'},
        {name: robot1Name},
      );
      await api.createPrototype(
        bulkOrgName,
        'write',
        {name: 'teamone', kind: 'team'},
        {name: robot2Name},
      );

      await authenticatedPage.goto(
        `/organization/${bulkOrgName}?tab=Defaultpermissions`,
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
      await searchInput.fill(bulkOrgName);
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
      await searchInput.fill(bulkOrgName);
      await expect(paginationInfo).toContainText('0 - 0 of 0');
    } finally {
      // Cleanup the bulk org
      try {
        await api.deleteOrganization(bulkOrgName);
      } catch {
        // Already deleted
      }
    }
  });
});
