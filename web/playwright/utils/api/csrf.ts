/**
 * CSRF Token utilities for Playwright e2e tests
 */

import {APIRequestContext} from '@playwright/test';
import {API_URL} from '../config';

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
