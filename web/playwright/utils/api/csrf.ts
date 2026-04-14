/**
 * CSRF token handling for Playwright tests.
 */

import {APIRequestContext} from '@playwright/test';

/**
 * Request a CSRF token from the Quay server.
 *
 * This is the low-level fetch — callers are responsible for caching.
 * Used by RawApiClient (caches per-instance) and auth helpers (no cache).
 */
export async function requestCsrfToken(
  request: APIRequestContext,
  baseUrl: string,
): Promise<string> {
  const response = await request.get(`${baseUrl}/csrf_token`, {
    headers: {'X-Requested-With': 'XMLHttpRequest'},
  });
  if (!response.ok()) {
    throw new Error(`Failed to get CSRF token: ${response.status()}`);
  }
  const data = await response.json();
  return data.csrf_token;
}
