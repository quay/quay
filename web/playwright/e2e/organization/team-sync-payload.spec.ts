import {test, expect} from '../../fixtures';
import {buildTeamSyncRequestData} from '../../utils/api/team-sync-payload';

/**
 * Pure payload mapping coverage for enableTeamSync.
 * Keystone has no Playwright/CI auth environment, so the group_id branch is
 * verified here (and by backend unit tests) rather than via a live Keystone E2E.
 */
test.describe(
  'Team sync request payload',
  {tag: ['@organization', '@feature:TEAM_SYNCING', '@PROJQUAY-12494']},
  () => {
    test('maps ldap to group_dn', () => {
      expect(buildTeamSyncRequestData('ldap', 'cn=devs,ou=groups')).toEqual({
        group_dn: 'cn=devs,ou=groups',
      });
    });

    test('maps oidc to group_name', () => {
      expect(buildTeamSyncRequestData('oidc', 'test_oidc_group')).toEqual({
        group_name: 'test_oidc_group',
      });
    });

    test('maps keystone to group_id', () => {
      expect(buildTeamSyncRequestData('keystone', 'keystone-group-123')).toEqual(
        {
          group_id: 'keystone-group-123',
        },
      );
    });
  },
);
