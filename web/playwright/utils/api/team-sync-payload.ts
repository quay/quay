export type TeamSyncService = 'ldap' | 'oidc' | 'keystone';

/**
 * Build the request body for POST .../team/{team}/syncing.
 * Mirrors web/src/resources/TeamSyncResource.ts so Playwright helpers stay aligned.
 */
export function buildTeamSyncRequestData(
  service: TeamSyncService,
  groupIdentifier: string,
): {group_dn: string} | {group_name: string} | {group_id: string} {
  if (service === 'oidc') {
    return {group_name: groupIdentifier};
  }
  if (service === 'keystone') {
    return {group_id: groupIdentifier};
  }
  return {group_dn: groupIdentifier};
}
