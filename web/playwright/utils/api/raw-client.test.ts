// @vitest-environment node

import {describe, expect, it, vi} from 'vitest';
import type {APIRequestContext, APIResponse} from '@playwright/test';

import {ApiRequestError, RawApiClient} from './raw-client';

function fakeResponse(status: number, body: unknown): APIResponse {
  return {
    ok: () => status >= 200 && status < 300,
    status: () => status,
    headers: () => ({}),
    text: async () => JSON.stringify(body),
    json: async () => body,
  } as unknown as APIResponse;
}

function fakeRequest(signInStatus: number): APIRequestContext {
  return {
    get: vi.fn().mockResolvedValue(fakeResponse(200, {csrf_token: 'token'})),
    post: vi
      .fn()
      .mockResolvedValue(
        fakeResponse(signInStatus, {message: 'Invalid credentials'}),
      ),
  } as unknown as APIRequestContext;
}

describe('RawApiClient.signIn', () => {
  it('resolves on a 200 response', async () => {
    const client = new RawApiClient(fakeRequest(200), 'https://example.test');
    await expect(client.signIn('user', 'pass')).resolves.toBeUndefined();
  });

  it('throws an ApiRequestError carrying the response status on failure', async () => {
    const client = new RawApiClient(fakeRequest(401), 'https://example.test');
    try {
      await client.signIn('user', 'pass');
      throw new Error('expected signIn to throw');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiRequestError);
      expect((err as ApiRequestError).status).toBe(401);
    }
  });

  it('throws an ApiRequestError carrying the response status on a 5xx failure', async () => {
    const client = new RawApiClient(fakeRequest(503), 'https://example.test');
    try {
      await client.signIn('user', 'pass');
      throw new Error('expected signIn to throw');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiRequestError);
      expect((err as ApiRequestError).status).toBe(503);
    }
  });
});
