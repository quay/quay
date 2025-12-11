/**
 * Organization API utilities for Playwright e2e tests
 */

import {APIRequestContext} from '@playwright/test';
import {API_URL} from '../config';
import {getCsrfToken} from './csrf';

/**
 * Create a new organization
 *
 * @example
 * ```typescript
 * await createOrganization(request, 'myorg');
 * await createOrganization(request, 'myorg', 'org@example.com');
 * ```
 */
export async function createOrganization(
  request: APIRequestContext,
  name: string,
  email?: string,
): Promise<{name: string}> {
  const csrfToken = await getCsrfToken(request);
  const response = await request.post(`${API_URL}/api/v1/organization/`, {
    timeout: 5000,
    headers: {
      'X-CSRF-Token': csrfToken,
    },
    data: {
      name,
      email: email || `${name}@example.com`,
    },
  });

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(
      `Failed to create organization ${name}: ${response.status()} - ${body}`,
    );
  }

  return response.json();
}

/**
 * Delete an organization
 *
 * @example
 * ```typescript
 * await deleteOrganization(request, 'myorg');
 * ```
 */
export async function deleteOrganization(
  request: APIRequestContext,
  name: string,
): Promise<void> {
  const csrfToken = await getCsrfToken(request);
  const response = await request.delete(
    `${API_URL}/api/v1/organization/${name}`,
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
      `Failed to delete organization ${name}: ${response.status()} - ${body}`,
    );
  }
}
