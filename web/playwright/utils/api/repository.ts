/**
 * Repository API utilities for Playwright e2e tests
 */

import {APIRequestContext} from '@playwright/test';
import {API_URL} from '../config';
import {getCsrfToken} from './csrf';

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
