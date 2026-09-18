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

  it('re-signs in and retries exactly once on fresh_login_required for build logs', async () => {
    const logsGet = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(401, {error_type: 'fresh_login_required'}),
      )
      .mockResolvedValueOnce(jsonResponse(200, {logs_url: 'http://example'}));
    const csrfGet = vi
      .fn()
      .mockResolvedValue(jsonResponse(200, {csrf_token: 'test-csrf'}));
    const signInPost = vi.fn().mockResolvedValue(jsonResponse(200, {}));

    const request = {
      get: vi.fn((url: string, ...args: unknown[]) => {
        if (url === `${API_URL}/csrf_token`) return csrfGet(url, ...args);
        return logsGet(url, ...args);
      }),
      post: vi.fn((url: string, ...args: unknown[]) => {
        if (url === `${API_URL}/api/v1/signin`) return signInPost(url, ...args);
        throw new Error(`unexpected post: ${url}`);
      }),
    } as unknown as APIRequestContext;

    const client = new ApiClient(request);
    client.setCredentials('admin', 'password');

    const response = await client.getBuildLogsAsSuperuser('some-build-uuid');

    expect(response.status()).toBe(200);
    expect(logsGet).toHaveBeenCalledTimes(2);
    expect(logsGet).toHaveBeenCalledWith(
      `${API_URL}/api/v1/superuser/some-build-uuid/logs`,
      expect.anything(),
    );
    expect(signInPost).toHaveBeenCalledTimes(1);
  });
});

describe('ApiClient CSRF token cache', () => {
  it('invalidates a sibling client cached token on sign-in', async () => {
    const csrfGet = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, {csrf_token: 'token-1'}))
      .mockResolvedValueOnce(jsonResponse(200, {csrf_token: 'token-2'}))
      .mockResolvedValueOnce(jsonResponse(200, {csrf_token: 'token-3'}));
    const orgPost = vi.fn().mockResolvedValue(jsonResponse(200, {name: 'org'}));
    const signInPost = vi.fn().mockResolvedValue(jsonResponse(200, {}));

    const request = {
      get: vi.fn((url: string, ...args: unknown[]) => {
        if (url === `${API_URL}/csrf_token`) return csrfGet(url, ...args);
        throw new Error(`unexpected get: ${url}`);
      }),
      post: vi.fn((url: string, ...args: unknown[]) => {
        if (url === `${API_URL}/api/v1/signin`) return signInPost(url, ...args);
        if (url === `${API_URL}/api/v1/organization/`)
          return orgPost(url, ...args);
        throw new Error(`unexpected post: ${url}`);
      }),
    } as unknown as APIRequestContext;

    const clientA = new ApiClient(request);
    const clientB = new ApiClient(request);

    await clientB.createOrganization('org');
    expect(csrfGet).toHaveBeenCalledTimes(1);
    expect(orgPost).toHaveBeenNthCalledWith(
      1,
      `${API_URL}/api/v1/organization/`,
      expect.objectContaining({
        headers: {'X-CSRF-Token': 'token-1'},
      }),
    );

    // clientA's own first fetch always hits the server (self-healing),
    // independent of clientB's already-cached token; it invalidates the
    // shared entry on success regardless.
    await clientA.signIn('admin', 'password');
    expect(csrfGet).toHaveBeenCalledTimes(2);

    await clientB.createOrganization('org');
    expect(csrfGet).toHaveBeenCalledTimes(3);
    expect(orgPost).toHaveBeenNthCalledWith(
      2,
      `${API_URL}/api/v1/organization/`,
      expect.objectContaining({
        headers: {'X-CSRF-Token': 'token-3'},
      }),
    );
  });

  it('does not share a cached token across different request contexts', async () => {
    const csrfGetA = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, {csrf_token: 'token-a'}));
    const csrfGetB = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, {csrf_token: 'token-b'}));
    const orgPost = vi.fn().mockResolvedValue(jsonResponse(200, {name: 'org'}));

    const makeRequest = (csrfGet: typeof csrfGetA) =>
      ({
        get: vi.fn((url: string, ...args: unknown[]) => {
          if (url === `${API_URL}/csrf_token`) return csrfGet(url, ...args);
          throw new Error(`unexpected get: ${url}`);
        }),
        post: vi.fn((url: string, ...args: unknown[]) => {
          if (url === `${API_URL}/api/v1/organization/`)
            return orgPost(url, ...args);
          throw new Error(`unexpected post: ${url}`);
        }),
      }) as unknown as APIRequestContext;

    const clientA = new ApiClient(makeRequest(csrfGetA));
    const clientB = new ApiClient(makeRequest(csrfGetB));

    await clientA.createOrganization('org');
    await clientB.createOrganization('org');

    expect(csrfGetA).toHaveBeenCalledTimes(1);
    expect(csrfGetB).toHaveBeenCalledTimes(1);
    expect(orgPost).toHaveBeenNthCalledWith(
      1,
      `${API_URL}/api/v1/organization/`,
      expect.objectContaining({headers: {'X-CSRF-Token': 'token-a'}}),
    );
    expect(orgPost).toHaveBeenNthCalledWith(
      2,
      `${API_URL}/api/v1/organization/`,
      expect.objectContaining({headers: {'X-CSRF-Token': 'token-b'}}),
    );
  });

  it('does not resurrect a pre-invalidation token from a late-resolving fetch', async () => {
    let resolveFirstCsrf: (value: APIResponse) => void;
    const firstCsrf = new Promise<APIResponse>((resolve) => {
      resolveFirstCsrf = resolve;
    });
    const csrfGet = vi
      .fn()
      .mockImplementationOnce(() => firstCsrf)
      .mockResolvedValueOnce(jsonResponse(200, {csrf_token: 'token-2'}))
      .mockResolvedValueOnce(jsonResponse(200, {csrf_token: 'token-3'}));
    const signInPost = vi.fn().mockResolvedValue(jsonResponse(200, {}));

    const request = {
      get: vi.fn((url: string, ...args: unknown[]) => {
        if (url === `${API_URL}/csrf_token`) return csrfGet(url, ...args);
        throw new Error(`unexpected get: ${url}`);
      }),
      post: vi.fn((url: string, ...args: unknown[]) => {
        if (url === `${API_URL}/api/v1/signin`) return signInPost(url, ...args);
        throw new Error(`unexpected post: ${url}`);
      }),
    } as unknown as APIRequestContext;

    const clientA = new ApiClient(request);
    const clientB = new ApiClient(request);

    // clientA's fetch starts (csrfGet #1) and is left in flight.
    const aFetch = clientA.getToken();

    // clientB completes a full sign-in cycle (csrfGet #2), invalidating the
    // shared cache and bumping the generation before clientA's fetch resolves.
    await clientB.signIn('admin', 'password');

    // clientA's in-flight fetch now resolves with a pre-invalidation token.
    resolveFirstCsrf!(jsonResponse(200, {csrf_token: 'token-1'}));
    const aToken = await aFetch;
    expect(aToken).toBe('token-1');

    // A third read must not see clientA's stale write -- it refetches.
    const thirdToken = await clientA.getToken();
    expect(thirdToken).toBe('token-3');
    expect(csrfGet).toHaveBeenCalledTimes(3);
  });
});
