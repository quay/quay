/**
 * Smoke tests for the API test infrastructure.
 *
 * Validates that the test harness works: authentication, CSRF tokens,
 * basic CRUD, and permission boundaries. Each test is self-contained
 * and can run in parallel.
 */

import {test, expect, uniqueName} from '../../fixtures';

test.describe('API Smoke', {tag: ['@api', '@smoke', '@auth:Database']}, () => {
  test('admin can create, read, and delete an organization', async ({
    adminClient,
  }) => {
    const orgName = uniqueName('smoke_org');
    try {
      const create = await adminClient.post('/api/v1/organization/', {
        name: orgName,
        email: `${orgName}@example.com`,
      });
      expect(create.status()).toBe(201);

      const get = await adminClient.get(`/api/v1/organization/${orgName}`);
      expect(get.status()).toBe(200);
      const body = await get.json();
      expect(body.name).toBe(orgName);
    } finally {
      await adminClient.delete(`/api/v1/organization/${orgName}`);
    }
  });

  test('admin can create a repository in an organization', async ({
    adminClient,
  }) => {
    const orgName = uniqueName('smoke_org');
    try {
      await adminClient.post('/api/v1/organization/', {
        name: orgName,
        email: `${orgName}@example.com`,
      });

      const response = await adminClient.post('/api/v1/repository', {
        namespace: orgName,
        repository: uniqueName('smoke_repo'),
        visibility: 'private',
        description: 'smoke test repo',
        repo_kind: 'image',
      });
      expect(response.status()).toBe(201);
    } finally {
      await adminClient.delete(`/api/v1/organization/${orgName}`);
    }
  });

  test('normal user gets 403 on superuser endpoints', async ({userClient}) => {
    const response = await userClient.get('/api/v1/superuser/users/');
    expect(response.status()).toBe(403);
  });

  test('unauthenticated request is rejected', async ({anonClient}) => {
    const response = await anonClient.get('/api/v1/user/');
    // Quay returns 401 or 403 depending on auth configuration
    expect([401, 403]).toContain(response.status());
  });

  test('public config exposes bootstrap feature flag without internal token settings', async ({
    request,
  }) => {
    const response = await request.get('/config');
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body.features).toHaveProperty('PROGRAMMATIC_BOOTSTRAP');
    expect(typeof body.features.PROGRAMMATIC_BOOTSTRAP).toBe('boolean');
    expect(body.config).not.toHaveProperty('BOOTSTRAP_APP_NAME');
    expect(body.config).not.toHaveProperty('BOOTSTRAP_TOKEN_OWNER');
    expect(body.config).not.toHaveProperty('BOOTSTRAP_TOKEN_PATH');
    expect(body.config).not.toHaveProperty('BOOTSTRAP_TOKEN_SCOPE');
    expect(body.config).not.toHaveProperty('BOOTSTRAP_TOKEN_EXPIRATION');
  });
});
