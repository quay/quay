/**
 * Bearer token API client for stage/production validation tests.
 *
 * Uses a pre-provisioned OAuth2 bearer token (e.g. from a QE secret)
 * instead of CSRF-based session auth. This is the auth mode used when
 * running Playwright tests against live environments like stage.quay.io
 * where Database sign-in is not available.
 *
 * The token is expected in process.env.QUAY_API_TOKEN and is typically
 * a registry-wide OAuth2 token created by QE.
 */

import {APIRequestContext, APIResponse} from '@playwright/test';

export class BearerApiClient {
  private request: APIRequestContext;
  private baseUrl: string;
  private token: string;

  constructor(request: APIRequestContext, baseUrl: string, token: string) {
    this.request = request;
    this.baseUrl = baseUrl;
    this.token = token;
  }

  private authHeaders(): Record<string, string> {
    return {
      Authorization: `Bearer ${this.token}`,
      'Content-Type': 'application/json',
    };
  }

  /**
   * GET request returning the full APIResponse.
   */
  async get(path: string): Promise<APIResponse> {
    return this.request.get(`${this.baseUrl}${path}`, {
      headers: this.authHeaders(),
      timeout: 30_000,
    });
  }

  /**
   * POST request returning the full APIResponse.
   */
  async post(
    path: string,
    data?: Record<string, unknown> | unknown[],
  ): Promise<APIResponse> {
    return this.request.post(`${this.baseUrl}${path}`, {
      headers: this.authHeaders(),
      data,
      timeout: 30_000,
    });
  }

  /**
   * PUT request returning the full APIResponse.
   */
  async put(
    path: string,
    data?: Record<string, unknown>,
  ): Promise<APIResponse> {
    return this.request.put(`${this.baseUrl}${path}`, {
      headers: this.authHeaders(),
      data,
      timeout: 30_000,
    });
  }

  /**
   * DELETE request returning the full APIResponse.
   */
  async delete(path: string): Promise<APIResponse> {
    return this.request.delete(`${this.baseUrl}${path}`, {
      headers: this.authHeaders(),
      timeout: 30_000,
    });
  }

  /**
   * PATCH request returning the full APIResponse.
   */
  async patch(
    path: string,
    data?: Record<string, unknown>,
  ): Promise<APIResponse> {
    return this.request.patch(`${this.baseUrl}${path}`, {
      headers: this.authHeaders(),
      data,
      timeout: 30_000,
    });
  }
}

/**
 * Whether bearer token auth mode is active.
 * When true, tests should use bearerClient instead of session-based clients.
 */
export function isBearerAuthMode(): boolean {
  return !!process.env.QUAY_API_TOKEN;
}
