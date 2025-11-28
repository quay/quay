/**
 * API utilities for Playwright e2e tests
 *
 * These utilities provide real API interactions for creating and managing
 * test data, replacing database seeding with dynamic API calls.
 */

import {APIRequestContext} from '@playwright/test';
import {API_URL} from './config';

// ============================================================================
// CSRF Token Helper
// ============================================================================

/**
 * Get CSRF token from backend
 */
export async function getCsrfToken(
  request: APIRequestContext,
): Promise<string> {
  const response = await request.get(`${API_URL}/csrf_token`, {
    timeout: 5000,
  });
  if (!response.ok()) {
    throw new Error(`Failed to get CSRF token: ${response.status()}`);
  }
  const data = await response.json();
  return data.csrf_token;
}

// ============================================================================
// Repository Utilities
// ============================================================================

export type RepositoryVisibility = 'public' | 'private';

/**
 * Create a new repository
 *
 * @example
 * ```typescript
 * await createRepository(request, 'testuser', 'myrepo', 'private');
 * ```
 */
export async function createRepository(
  request: APIRequestContext,
  namespace: string,
  name: string,
  visibility: RepositoryVisibility = 'private',
  description = '',
): Promise<{namespace: string; name: string; kind: string}> {
  const csrfToken = await getCsrfToken(request);
  const response = await request.post(`${API_URL}/api/v1/repository`, {
    timeout: 5000,
    headers: {
      'X-CSRF-Token': csrfToken,
    },
    data: {
      namespace,
      repository: name,
      visibility,
      description,
      repo_kind: 'image',
    },
  });

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(
      `Failed to create repository ${namespace}/${name}: ${response.status()} - ${body}`,
    );
  }

  return response.json();
}

/**
 * Delete a repository
 *
 * @example
 * ```typescript
 * await deleteRepository(request, 'testuser', 'myrepo');
 * ```
 */
export async function deleteRepository(
  request: APIRequestContext,
  namespace: string,
  name: string,
): Promise<void> {
  const csrfToken = await getCsrfToken(request);
  const response = await request.delete(
    `${API_URL}/api/v1/repository/${namespace}/${name}`,
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
      `Failed to delete repository ${namespace}/${name}: ${response.status()} - ${body}`,
    );
  }
}
