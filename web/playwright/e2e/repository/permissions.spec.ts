import {test, expect} from '../../fixtures';

test.describe(
  'Repository Permissions',
  {tag: ['@repository', '@critical']},
  () => {
    test('displays and manages inline permission operations', async ({
      authenticatedPage,
      api,
    }) => {
      // Create test organization with repository, team, and robot
      const org = await api.organization('perm');
      const repo = await api.repository(org.name, 'permrepo');
      const team = await api.team(org.name, 'permteam');
      const robot = await api.robot(org.name, 'permbot');

      // Add permissions via API
      await api.repositoryPermission(
        org.name,
        repo.name,
        'team',
        team.name,
        'read',
      );
      await api.repositoryPermission(
        org.name,
        repo.name,
        'user',
        robot.fullName,
        'read',
      );

      // Navigate to repository settings (permissions is default tab)
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=settings`,
      );

      // 1. Verify initial permissions display
      // Check team row displays correctly
      const teamRow = authenticatedPage.locator('tr', {hasText: team.name});
      await expect(teamRow.locator('[data-label="membername"]')).toHaveText(
        team.name,
      );
      await expect(teamRow.locator('[data-label="type"]')).toContainText(
        'Team',
      );
      await expect(teamRow.locator('[data-label="role"]')).toHaveText('read');

      // Check robot row displays correctly
      const robotRow = authenticatedPage.locator('tr', {
        hasText: robot.fullName,
      });
      await expect(robotRow.locator('[data-label="membername"]')).toHaveText(
        robot.fullName,
      );
      await expect(robotRow.locator('[data-label="type"]')).toContainText(
        'Robot',
      );
      await expect(robotRow.locator('[data-label="role"]')).toHaveText('read');

      // 2. Change team permission inline (read → write)
      await teamRow.getByText('read').click();
      await authenticatedPage.getByRole('menuitem', {name: 'Write'}).click();
      await expect(teamRow.locator('[data-label="role"]')).toHaveText('write');

      // 3. Delete robot permission via kebab menu
      await robotRow.getByTestId(`${robot.fullName}-toggle-kebab`).click();
      await authenticatedPage.getByText('Delete Permission').click();
      // Verify robot is no longer in the table
      await expect(
        authenticatedPage.locator('tr', {hasText: robot.fullName}),
      ).not.toBeVisible();
    });

    test('bulk operations: change and delete permissions', async ({
      authenticatedPage,
      api,
    }) => {
      // Create test organization with repository, teams, and robot
      const org = await api.organization('bulk');
      const repo = await api.repository(org.name, 'bulkrepo');
      const team1 = await api.team(org.name, 'bulkteam1');
      const team2 = await api.team(org.name, 'bulkteam2');
      const robot = await api.robot(org.name, 'bulkbot');

      // Add multiple permissions
      await api.repositoryPermission(
        org.name,
        repo.name,
        'team',
        team1.name,
        'read',
      );
      await api.repositoryPermission(
        org.name,
        repo.name,
        'team',
        team2.name,
        'read',
      );
      await api.repositoryPermission(
        org.name,
        repo.name,
        'user',
        robot.fullName,
        'read',
      );

      // Navigate to repository settings
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=settings`,
      );

      // Wait for permissions table to load
      await expect(
        authenticatedPage.locator('tr', {hasText: team1.name}),
      ).toBeVisible();

      // 1. Bulk change permissions to write
      // Select all permissions
      await authenticatedPage
        .locator('[name="permissions-select-all"]')
        .click();

      // Open Actions menu and change permissions
      await authenticatedPage.getByText('Actions').click();
      await authenticatedPage.getByText('Change Permissions').hover();
      await authenticatedPage
        .getByTestId('change-permissions-menu-list')
        .getByText('Write')
        .click();

      // Verify all roles changed to write
      const team1Row = authenticatedPage.locator('tr', {hasText: team1.name});
      const team2Row = authenticatedPage.locator('tr', {hasText: team2.name});
      const robotRow = authenticatedPage.locator('tr', {
        hasText: robot.fullName,
      });

      await expect(team1Row.locator('[data-label="role"]')).toHaveText('write');
      await expect(team2Row.locator('[data-label="role"]')).toHaveText('write');
      await expect(robotRow.locator('[data-label="role"]')).toHaveText('write');

      // 2. Bulk delete teams (select just teams, not robot)
      // The bulk change operation deselects all items, so re-select teams
      await team1Row.locator('input[type="checkbox"]').check();
      await team2Row.locator('input[type="checkbox"]').check();

      // Verify only teams are selected (not robot)
      await expect(team1Row.locator('input[type="checkbox"]')).toBeChecked();
      await expect(team2Row.locator('input[type="checkbox"]')).toBeChecked();
      await expect(
        robotRow.locator('input[type="checkbox"]'),
      ).not.toBeChecked();

      // Open Actions menu and delete
      await authenticatedPage.getByText('Actions').click();
      await authenticatedPage.locator('#bulk-delete-permissions').click();

      // Verify only robot remains
      await expect(
        authenticatedPage.locator('tr', {hasText: team1.name}),
      ).not.toBeVisible();
      await expect(
        authenticatedPage.locator('tr', {hasText: team2.name}),
      ).not.toBeVisible();
      await expect(
        authenticatedPage.locator('tr', {hasText: robot.fullName}),
      ).toBeVisible();
    });

    test('adds permissions for robot and team', async ({
      authenticatedPage,
      api,
    }) => {
      // Create test organization with repository, team, and robot to add
      const org = await api.organization('addperm');
      const repo = await api.repository(org.name, 'addrepo');
      const teamToAdd = await api.team(org.name, 'addteam');
      const robotToAdd = await api.robot(org.name, 'addbot');

      // Navigate to repository settings
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=settings`,
      );

      // 1. Add robot permission
      await authenticatedPage.getByTestId('add-permissions-btn').click();

      // Wait for the add permission form to appear
      const addForm = authenticatedPage.locator('#add-permission-form');
      await expect(addForm).toBeVisible();

      // Search and select robot
      const searchInput = addForm.getByPlaceholder(
        'Search for user, add/create robot account',
      );
      await searchInput.click();
      await searchInput.fill(robotToAdd.shortname);

      // Wait for dropdown options to load and click the robot option by text
      const robotOption = authenticatedPage.locator('button', {
        hasText: robotToAdd.fullName,
      });
      await expect(robotOption).toBeVisible();
      await robotOption.click();

      // Change permission from admin (default) to Read
      await addForm.getByText('admin').click();
      await authenticatedPage.getByRole('menuitem', {name: 'Read'}).click();

      // Submit
      await authenticatedPage.getByTestId('permissions-submit-btn').click();

      // Verify robot appears in table with correct role
      const robotRow = authenticatedPage.locator('tr', {
        hasText: robotToAdd.fullName,
      });
      await expect(robotRow.locator('[data-label="membername"]')).toHaveText(
        robotToAdd.fullName,
      );
      await expect(robotRow.locator('[data-label="type"]')).toContainText(
        'Robot',
      );
      await expect(robotRow.locator('[data-label="role"]')).toHaveText('read');

      // 2. Add team permission
      await authenticatedPage.getByTestId('add-permissions-btn').click();

      // Wait for the add permission form to appear again
      await expect(addForm).toBeVisible();

      // Search and select team
      await searchInput.click();
      await searchInput.fill(teamToAdd.name);

      // Click the team option by text
      const teamOption = authenticatedPage.locator('button', {
        hasText: teamToAdd.name,
      });
      await expect(teamOption).toBeVisible();
      await teamOption.click();

      // Change permission from admin (default) to Read
      await addForm.getByText('admin').click();
      await authenticatedPage.getByRole('menuitem', {name: 'Read'}).click();

      // Submit
      await authenticatedPage.getByTestId('permissions-submit-btn').click();

      // Verify team appears in table with correct role
      const teamRow = authenticatedPage.locator('tr', {
        hasText: teamToAdd.name,
      });
      await expect(teamRow.locator('[data-label="membername"]')).toHaveText(
        teamToAdd.name,
      );
      await expect(teamRow.locator('[data-label="type"]')).toContainText(
        'Team',
      );
      await expect(teamRow.locator('[data-label="role"]')).toHaveText('read');
    });
  },
);
