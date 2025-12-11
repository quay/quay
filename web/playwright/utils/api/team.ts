/**
 * Team API utilities for Playwright e2e tests
 */

import {APIRequestContext} from '@playwright/test';
import {API_URL} from '../config';
import {getCsrfToken} from './csrf';

export type TeamRole = 'member' | 'creator' | 'admin';

/**
 * Create a new team in an organization
 *
 * @example
 * ```typescript
 * await createTeam(request, 'myorg', 'myteam');
 * await createTeam(request, 'myorg', 'adminteam', 'admin');
 * ```
 */
export async function createTeam(
  request: APIRequestContext,
  orgName: string,
  teamName: string,
  role: TeamRole = 'member',
): Promise<{name: string; role: string}> {
  const csrfToken = await getCsrfToken(request);
  const response = await request.put(
    `${API_URL}/api/v1/organization/${orgName}/team/${teamName}`,
    {
      timeout: 5000,
      headers: {
        'X-CSRF-Token': csrfToken,
      },
      data: {
        role,
      },
    },
  );

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(
      `Failed to create team ${teamName} in ${orgName}: ${response.status()} - ${body}`,
    );
  }

  return response.json();
}

/**
 * Delete a team from an organization
 *
 * @example
 * ```typescript
 * await deleteTeam(request, 'myorg', 'myteam');
 * ```
 */
export async function deleteTeam(
  request: APIRequestContext,
  orgName: string,
  teamName: string,
): Promise<void> {
  const csrfToken = await getCsrfToken(request);
  const response = await request.delete(
    `${API_URL}/api/v1/organization/${orgName}/team/${teamName}`,
    {
      timeout: 5000,
      headers: {
        'X-CSRF-Token': csrfToken,
      },
    },
  );

  // 204 = success, 404 = already deleted (acceptable)
  if (!response.ok() && response.status() !== 404) {
    const body = await response.text();
    throw new Error(
      `Failed to delete team ${teamName} from ${orgName}: ${response.status()} - ${body}`,
    );
  }
}
