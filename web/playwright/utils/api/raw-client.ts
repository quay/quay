/**
 * Raw API client for API tests.
 *
 * Provides low-level HTTP methods that return full APIResponse objects,
 * allowing tests to assert on status codes, headers, and response bodies.
 * This is essential for negative tests (asserting 403, 404, etc.).
 *
 * For setup/teardown operations that should throw on failure, use the
 * existing ApiClient from web/playwright/utils/api/client.ts instead.
 */

import {APIRequestContext, APIResponse} from '@playwright/test';

import {requestCsrfToken} from './csrf';

export class RawApiClient {
  private request: APIRequestContext;
  private baseUrl: string;
  private csrfToken: string | null = null;

  constructor(request: APIRequestContext, baseUrl: string) {
    this.request = request;
    this.baseUrl = baseUrl;
  }

  /**
   * Fetch and cache the CSRF token needed for mutating requests.
   */
  async fetchCsrfToken(): Promise<string> {
    if (!this.csrfToken) {
      this.csrfToken = await requestCsrfToken(this.request, this.baseUrl);
    }
    return this.csrfToken as string;
  }

  /**
   * Sign in to establish a session. Must be called before making
   * authenticated requests.
   *
   * Note: signing in creates a new session, which invalidates the
   * pre-login CSRF token. We clear the cache so the next request
   * fetches a fresh token tied to the authenticated session.
   */
  async signIn(username: string, password: string): Promise<void> {
    const token = await this.fetchCsrfToken();
    const response = await this.request.post(`${this.baseUrl}/api/v1/signin`, {
      headers: {'X-CSRF-Token': token},
      data: {username, password},
    });
    if (!response.ok()) {
      const body = await response.text();
      throw new Error(
        `Failed to sign in as ${username}: ${response.status()} - ${body}`,
      );
    }
    // Invalidate cached token — the new session has a different CSRF token
    this.csrfToken = null;
  }

  /**
   * GET request returning the full APIResponse.
   */
  async get(path: string): Promise<APIResponse> {
    return this.request.get(`${this.baseUrl}${path}`, {
      timeout: 10_000,
    });
  }

  /**
   * POST request returning the full APIResponse.
   */
  async post(
    path: string,
    data?: Record<string, unknown>,
  ): Promise<APIResponse> {
    const token = await this.fetchCsrfToken();
    return this.request.post(`${this.baseUrl}${path}`, {
      headers: {'X-CSRF-Token': token},
      data,
      timeout: 10_000,
    });
  }

  /**
   * PUT request returning the full APIResponse.
   */
  async put(
    path: string,
    data?: Record<string, unknown>,
  ): Promise<APIResponse> {
    const token = await this.fetchCsrfToken();
    return this.request.put(`${this.baseUrl}${path}`, {
      headers: {'X-CSRF-Token': token},
      data,
      timeout: 10_000,
    });
  }

  /**
   * DELETE request returning the full APIResponse.
   */
  async delete(path: string): Promise<APIResponse> {
    const token = await this.fetchCsrfToken();
    return this.request.delete(`${this.baseUrl}${path}`, {
      headers: {'X-CSRF-Token': token},
      timeout: 10_000,
    });
  }

  /**
   * PATCH request returning the full APIResponse.
   */
  async patch(
    path: string,
    data?: Record<string, unknown>,
  ): Promise<APIResponse> {
    const token = await this.fetchCsrfToken();
    return this.request.patch(`${this.baseUrl}${path}`, {
      headers: {'X-CSRF-Token': token},
      data,
      timeout: 10_000,
    });
  }
}
