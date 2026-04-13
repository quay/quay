/**
 * Smoke tests for the API test infrastructure.
 *
 * Validates that the test harness works: authentication, CSRF tokens,
 * basic CRUD, and permission boundaries. These should pass before
 * porting any Cypress tests.
 */

import {test, expect, uniqueName} from '../helpers';

test.describe.serial('API Test Infrastructure Smoke', () => {
  const orgName = uniqueName('smoke_org');

  test('admin can create and list an organization', async ({adminClient}) => {
    const createResponse = await adminClient.post('/api/v1/organization/', {
      name: orgName,
      email: `${orgName}@example.com`,
    });
    expect(createResponse.status()).toBe(201);

    const getResponse = await adminClient.get(
      `/api/v1/organization/${orgName}`,
    );
    expect(getResponse.status()).toBe(200);
    const body = await getResponse.json();
    expect(body.name).toBe(orgName);
  });

  test('admin can create a repository in the organization', async ({
    adminClient,
  }) => {
    const repoName = uniqueName('smoke_repo');
    const response = await adminClient.post('/api/v1/repository', {
      namespace: orgName,
      repository: repoName,
      visibility: 'private',
      description: 'smoke test repo',
      repo_kind: 'image',
    });
    expect(response.status()).toBe(201);
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

  test('admin can delete the organization', async ({adminClient}) => {
    const response = await adminClient.delete(
      `/api/v1/organization/${orgName}`,
    );
    expect(response.status()).toBe(204);

    // Verify it's gone
    const getResponse = await adminClient.get(
      `/api/v1/organization/${orgName}`,
    );
    expect(getResponse.status()).toBe(404);
  });

  // Cleanup even if earlier tests fail — prevent orphaned resources
  test.afterAll(async () => {
    const baseUrl = process.env.QUAY_API_URL || 'http://localhost:8080';
    const {RawApiClient} = await import('../helpers/api-client');
    // Use global fetch for cleanup — Playwright fixtures aren't available in afterAll
    const {request: playwrightRequest} = await import('@playwright/test');
    const reqContext = await playwrightRequest.newContext({
      ignoreHTTPSErrors: true,
    });
    const client = new RawApiClient(reqContext, baseUrl);
    const adminUser = process.env.QUAY_ADMIN_USERNAME || 'admin';
    const adminPass = process.env.QUAY_ADMIN_PASSWORD || 'password';
    try {
      await client.signIn(adminUser, adminPass);
      await client.delete(`/api/v1/organization/${orgName}`);
    } catch {
      // Best-effort cleanup — org may already be deleted by the test above
    } finally {
      await reqContext.dispose();
    }
  });
});
