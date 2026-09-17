// @vitest-environment node

import {describe, expect, it} from 'vitest';
import type {APIResponse} from '@playwright/test';

import {TestApi} from './fixtures';
import type {ApiClient} from './utils/api';

function fakeResponse(status: number): APIResponse {
  return {
    ok: () => status >= 200 && status < 300,
    status: () => status,
  } as unknown as APIResponse;
}

function stubClient(ran: string[]): ApiClient {
  return {
    createOrganization: async (name: string) => {
      ran.push(`create:${name}`);
    },
    deleteOrganization: async (name: string) => {
      ran.push(`deleteOrg:${name}`);
    },
  } as unknown as ApiClient;
}

describe('TestApi.cleanup', () => {
  it('drains the whole stack and rethrows a failed app-token revoke', async () => {
    const ran: string[] = [];
    const api = new TestApi(stubClient(ran));
    const org = await api.organization();
    api.trackAppToken('tok-uuid', async () => fakeResponse(500));

    await expect(api.cleanup()).rejects.toThrow(
      'Failed to revoke app token tok-uuid: 500',
    );
    expect(ran).toEqual([`create:${org.name}`, `deleteOrg:${org.name}`]);
  });

  it('treats a 404 revoke as already-gone and does not throw', async () => {
    const ran: string[] = [];
    const api = new TestApi(stubClient(ran));
    const org = await api.organization();
    api.trackAppToken('tok-uuid', async () => fakeResponse(404));

    await expect(api.cleanup()).resolves.toBeUndefined();
    expect(ran).toEqual([`create:${org.name}`, `deleteOrg:${org.name}`]);
  });

  it('rethrows only the last-registered of multiple failed cleanups', async () => {
    const api = new TestApi({} as unknown as ApiClient);
    api.trackAppToken('tok-a', async () => fakeResponse(500));
    api.trackAppToken('tok-b', async () => fakeResponse(503));

    await expect(api.cleanup()).rejects.toThrow(
      'Failed to revoke app token tok-b: 503',
    );
  });
});
