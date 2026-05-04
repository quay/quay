import {test, expect} from '../../fixtures';

// Relative group DN (relative to the configured LDAP_BASE_DN dc=example,dc=org).
// The UI shows the base DN and asks for the relative part only.
const LDAP_GROUP_RELATIVE_DN = 'cn=test_ldap_group,ou=groups';

test.describe(
  'LDAP Team Sync',
  {tag: ['@organization', '@auth:LDAP', '@feature:TEAM_SYNCING']},
  () => {
    test('team sync lifecycle: validate input, enable, verify config, disable', async ({
      superuserPage: page,
      superuserApi: api,
    }) => {
      const org = await api.organization('ldapteamsync');
      const team = await api.team(org.name, 'ldapsyncteam');

      await page.goto(
        `/organization/${org.name}/teams/${team.name}?tab=Teamsandmembership`,
      );

      // Click Enable Team Sync
      await page.getByRole('button', {name: 'Enable Team Sync'}).click();

      // Modal should appear — LDAP shows the base DN with a relative-DN input prompt
      await expect(page.getByText('relative to the base DN')).toBeVisible();

      // Enable Sync button should be disabled without input
      await expect(
        page.getByRole('button', {name: 'Enable Sync'}),
      ).toBeDisabled();

      // Type whitespace — should stay disabled
      await page.locator('#team-sync-group-name').fill(' ');
      await expect(
        page.getByRole('button', {name: 'Enable Sync'}),
      ).toBeDisabled();

      // Type valid relative LDAP group DN — should enable
      await page.locator('#team-sync-group-name').fill(LDAP_GROUP_RELATIVE_DN);
      await expect(
        page.getByRole('button', {name: 'Enable Sync'}),
      ).toBeEnabled();

      // Enable sync
      await page.getByRole('button', {name: 'Enable Sync'}).click();
      await expect(
        page.getByText('Successfully updated team sync config').first(),
      ).toBeVisible();

      // Verify sync config is displayed with LDAP service details
      await expect(
        page.getByText('synchronized with a group in ldap'),
      ).toBeVisible();
      await expect(page.getByText('Bound to group')).toBeVisible();
      await expect(page.getByText(LDAP_GROUP_RELATIVE_DN)).toBeVisible();
      await expect(page.getByText('Last Updated')).toBeVisible();

      // Verify team membership is in read-only mode — "Add new member" is hidden
      // when LDAP controls membership (pageInReadOnlyMode = true in ManageMembersList)
      await expect(
        page.getByRole('button', {name: 'Add new member'}),
      ).not.toBeVisible();

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
