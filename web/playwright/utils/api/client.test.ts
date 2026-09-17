import {APIRequestContext, APIResponse} from '@playwright/test';
import {ApiClient} from './client';
import {API_URL} from '../config';

function jsonResponse(
  status: number,
  body: Record<string, unknown>,
): APIResponse {
  return {
    status: () => status,
    ok: () => status >= 200 && status < 300,
    text: async () => JSON.stringify(body),
    json: async () => body,
  } as unknown as APIResponse;
}

describe('ApiClient fresh-login retry', () => {
  it('re-signs in and retries exactly once on fresh_login_required', async () => {
    const buildGet = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(401, {error_type: 'fresh_login_required'}),
      )
      .mockResolvedValueOnce(jsonResponse(200, {trigger: null}));
    const csrfGet = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, {csrf_token: 'test-csrf'}));
    const signInPost = vi.fn().mockResolvedValue(jsonResponse(200, {}));

    const request = {
      get: vi.fn((url: string, ...args: unknown[]) => {
        if (url === `${API_URL}/csrf_token`) return csrfGet(url, ...args);
        return buildGet(url, ...args);
      }),
      post: vi.fn((url: string, ...args: unknown[]) => {
        if (url === `${API_URL}/api/v1/signin`) return signInPost(url, ...args);
        throw new Error(`unexpected post: ${url}`);
      }),
    } as unknown as APIRequestContext;

    const client = new ApiClient(request);
    client.setCredentials('admin', 'password');

    const response = await client.getBuildAsSuperuser('some-build-uuid');

    expect(response.status()).toBe(200);
    expect(buildGet).toHaveBeenCalledTimes(2);
    expect(buildGet).toHaveBeenCalledWith(
      `${API_URL}/api/v1/superuser/some-build-uuid/build`,
      expect.anything(),
    );
    expect(signInPost).toHaveBeenCalledTimes(1);
  });
});
