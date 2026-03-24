import {test, expect} from '../../fixtures';

test.describe(
  'OIDC Team Sync',
  {tag: ['@organization', '@auth:OIDC', '@feature:TEAM_SYNCING']},
  () => {
    test('team sync lifecycle: validate input, enable, verify config, disable', async ({
      superuserPage: page,
      superuserApi: api,
    }) => {
      const org = await api.organization('teamsync');
      const team = await api.team(org.name, 'syncteam');

      await page.goto(
        `/organization/${org.name}/teams/${team.name}?tab=Teamsandmembership`,
      );

      // Click Enable Team Sync
      await page.getByRole('button', {name: 'Enable Team Sync'}).click();

      // Modal should appear with group name input
      await expect(
        page.getByText(
          "Enter the Group Name you'd like to sync membership with:",
        ),
      ).toBeVisible();

      // Enable Sync button should be disabled without input
      await expect(
        page.getByRole('button', {name: 'Enable Sync'}),
      ).toBeDisabled();

      // Type whitespace — should stay disabled
      await page.locator('#team-sync-group-name').fill(' ');
      await expect(
        page.getByRole('button', {name: 'Enable Sync'}),
      ).toBeDisabled();

      // Type valid group name — should enable
      await page.locator('#team-sync-group-name').fill('test_oidc_group');
      await expect(
        page.getByRole('button', {name: 'Enable Sync'}),
      ).toBeEnabled();

      // Enable sync
      await page.getByRole('button', {name: 'Enable Sync'}).click();
      await expect(
        page.getByText('Successfully updated team sync config').first(),
      ).toBeVisible();

      // Verify sync config is displayed
      await expect(
        page.getByText('synchronized with a group in oidc'),
      ).toBeVisible();
      await expect(page.getByText('Bound to group')).toBeVisible();
      await expect(page.getByText('test_oidc_group')).toBeVisible();

      // Remove sync
      await page.getByRole('button', {name: 'Remove synchronization'}).click();
      await expect(
        page.getByText(
          'Are you sure you want to disable group syncing on this team?',
        ),
      ).toBeVisible();
      await page.getByRole('button', {name: 'Confirm'}).click();
      await expect(
        page.getByText('Successfully removed team synchronization').first(),
      ).toBeVisible();
    });
  },
);
