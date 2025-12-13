/**
 * User API utilities for Playwright e2e tests
 */

import {APIRequestContext} from '@playwright/test';
import {API_URL} from '../config';
import {getCsrfToken} from './csrf';

export interface CreateUserResponse {
  username: string;
  awaiting_verification?: boolean;
}

/**
 * Create a new user account
 *
 * @example
 * ```typescript
 * const result = await createUser(request, 'newuser', 'password123', 'user@example.com');
 * ```
 */
export async function createUser(
  request: APIRequestContext,
  username: string,
  password: string,
  email: string,
): Promise<CreateUserResponse> {
  const csrfToken = await getCsrfToken(request);
  const response = await request.post(`${API_URL}/api/v1/user/`, {
    timeout: 10000,
    headers: {
      'X-CSRF-Token': csrfToken,
    },
    data: {
      username,
      password,
      email,
    },
  });

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(
      `Failed to create user ${username}: ${response.status()} - ${body}`,
    );
  }

  const result = await response.json();
  // API returns awaiting_verification: true if email verification is required
  // Otherwise returns user object with username
  return {
    username: result.username || username,
    awaiting_verification: result.awaiting_verification,
  };
}

/**
 * Delete a user via superuser API
 *
 * Requires superuserRequest fixture (authenticated as admin)
 *
 * @example
 * ```typescript
 * await deleteUser(superuserRequest, 'testuser123');
 * ```
 */
export async function deleteUser(
  request: APIRequestContext,
  username: string,
): Promise<void> {
  const csrfToken = await getCsrfToken(request);
  const response = await request.delete(
    `${API_URL}/api/v1/superuser/users/${username}`,
    {
      timeout: 10000,
      headers: {
        'X-CSRF-Token': csrfToken,
      },
    },
  );

  // 204 = success, 404 = already deleted (acceptable)
  if (!response.ok() && response.status() !== 404) {
    const body = await response.text();
    throw new Error(
      `Failed to delete user ${username}: ${response.status()} - ${body}`,
    );
  }
}

/**
 * Check if a user exists
 *
 * @example
 * ```typescript
 * const exists = await userExists(request, 'testuser');
 * ```
 */
export async function userExists(
  request: APIRequestContext,
  username: string,
): Promise<boolean> {
  const response = await request.get(`${API_URL}/api/v1/users/${username}`, {
    timeout: 5000,
  });
  return response.ok();
}
