import {test, expect} from '../../fixtures';

test.describe(
  'Permission dropdown does not navigate away',
  {tag: ['@organization', '@critical']},
  () => {
    test('inline permission change stays on page', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: org with repo, team, and a read permission
      const org = await api.organization('dropnav');
      const repo = await api.repository(org.name, 'navrepo');
      const team = await api.team(org.name, 'navteam');
      await api.repositoryPermission(
        org.name,
        repo.name,
        'team',
        team.name,
        'read',
      );

      // Navigate to repository settings
      const settingsUrl = `/repository/${org.name}/${repo.name}?tab=settings`;
      await authenticatedPage.goto(settingsUrl);

      // Click the permission dropdown to change role
      const teamRow = authenticatedPage.locator('tr', {hasText: team.name});
      await teamRow.getByText('read').click();

      // Click a permission option — this is where Firefox would navigate away
      await authenticatedPage.getByRole('menuitem', {name: 'Write'}).click();

      // Verify we stayed on the same page (no navigation occurred)
      await expect(authenticatedPage).toHaveURL(settingsUrl);

      // Verify the permission was actually updated
      await expect(teamRow.locator('[data-label="role"]')).toHaveText('write');
    });

    test('default permission dropdown stays on page', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: org with team, robot, and a default permission
      const org = await api.organization('dropnav2');
      const team = await api.team(org.name, 'navteam');
      const robot = await api.robot(org.name, 'navbot');
      await api.prototype(
        org.name,
        'read',
        {name: team.name, kind: 'team'},
        {name: robot.fullName},
      );

      // Navigate to default permissions tab
      const defaultPermsUrl = `/organization/${org.name}?tab=Defaultpermissions`;
      await authenticatedPage.goto(defaultPermsUrl);

      // Wait for data to load
      const tabPanel = authenticatedPage.getByRole('tabpanel', {
        name: 'Default permissions',
      });
      await expect(
        tabPanel.locator('.pf-v6-c-pagination__total-items').first(),
      ).toContainText('1 - 1 of 1', {timeout: 15000});

      // Click permission dropdown toggle
      await authenticatedPage
        .getByTestId(`${robot.fullName}-permission-dropdown-toggle`)
        .click();

      // Click a permission option — this is where Firefox would navigate away
      await authenticatedPage.getByTestId(`${robot.fullName}-WRITE`).click();

      // Verify we stayed on the same page
      await expect(authenticatedPage).toHaveURL(defaultPermsUrl);

      // Verify success alert confirms the change worked
      await expect(
        authenticatedPage.locator('.pf-v6-c-alert.pf-m-success').last(),
      ).toContainText('Permission updated successfully');
    });

    test('create default permission dropdown stays on page', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: org with team
      const org = await api.organization('dropnav3');
      const team = await api.team(org.name, 'navteam');

      // Navigate to default permissions tab
      const defaultPermsUrl = `/organization/${org.name}?tab=Defaultpermissions`;
      await authenticatedPage.goto(defaultPermsUrl);

      // Open create default permission drawer
      await authenticatedPage
        .getByTestId('create-default-permissions-btn')
        .click();

      // Select "Anyone" type
      await authenticatedPage.getByTestId('Anyone').click();

      // Select team
      await authenticatedPage.locator('#applied-to-dropdown').click();
      await authenticatedPage.getByTestId(`${team.name}-team`).click();

      // Click the permission level dropdown
      await authenticatedPage
        .getByTestId('create-default-permission-dropdown-toggle')
        .click();

      // Click "Write" — this is where Firefox would navigate away
      await authenticatedPage
        .getByTestId('create-default-permission-dropdown')
        .getByText('Write')
        .click();

      // Verify we stayed on the same page
      await expect(authenticatedPage).toHaveURL(defaultPermsUrl);

      // Verify the dropdown shows the selected value
      await expect(
        authenticatedPage.getByTestId(
          'create-default-permission-dropdown-toggle',
        ),
      ).toContainText('Write');
    });
  },
);
