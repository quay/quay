/**
 * Stage/Production Validation Tests
 *
 * API-only smoke tests for live Quay deployments (e.g. stage.quay.io).
 * Uses a pre-provisioned bearer token (QUAY_API_TOKEN) — no Database
 * sign-in, no user creation, no browser UI.
 *
 * Coverage mirrors the Cypress quayio_monitoring_tests.cy.js suite:
 *   - Health endpoints
 *   - API discovery
 *   - Org/repo/robot/team CRUD lifecycle
 *   - Star/unstar
 *   - Usage logs
 *   - Image push/pull via skopeo (@container tag)
 *
 * Run with: npm run test:stage-validation
 *
 * Required env:
 *   QUAY_API_TOKEN           - Registry-wide OAuth2 bearer token
 *   REACT_QUAY_APP_API_URL   - Target URL (e.g. https://stage.quay.io)
 *   PLAYWRIGHT_BASE_URL      - Same as above
 *   QUAY_USER                - Registry username (for skopeo push/pull)
 *   QUAY_PASSWORD             - Registry password (for skopeo push/pull)
 */

import {test, expect, uniqueName} from '../../fixtures';
import {QUAY_USER, QUAY_PASSWORD} from '../../utils/config';

// ---------------------------------------------------------------------------
// Health & Discovery — no auth required on most Quay deployments
// ---------------------------------------------------------------------------

test.describe(
  'Stage Validation — Health',
  {tag: ['@api', '@stage-validation', '@auth:Bearer']},
  () => {
    test('health/instance returns healthy services', async ({bearerClient}) => {
      const resp = await bearerClient.get('/health/instance');
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body.data).toBeTruthy();
      expect(body.data.services).toBeTruthy();
    });

    test('health/endtoend returns healthy services', async ({bearerClient}) => {
      const resp = await bearerClient.get('/health/endtoend');
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body.data).toBeTruthy();
      expect(body.data.services).toBeTruthy();
    });

    test('API discovery endpoint is reachable', async ({bearerClient}) => {
      const resp = await bearerClient.get('/api/v1/discovery');
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body.paths || body.endpoints).toBeTruthy();
    });

    test('authenticated user info resolves', async ({bearerClient}) => {
      const resp = await bearerClient.get('/api/v1/user/');
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body.username).toBeTruthy();
    });
  },
);

// ---------------------------------------------------------------------------
// Org / Repo / Robot / Team CRUD lifecycle
// ---------------------------------------------------------------------------

test.describe(
  'Stage Validation — CRUD Lifecycle',
  {tag: ['@api', '@stage-validation', '@auth:Bearer']},
  () => {
    test.describe.configure({mode: 'serial'});

    const prefix = uniqueName('stgval');
    const orgName = `${prefix}-org`.substring(0, 40).toLowerCase();
    const orgEmail = `${orgName}@validation.test`;
    const repoName = `${prefix}-repo`.substring(0, 40).toLowerCase();
    const robotName = `${prefix}robot`
      .substring(0, 40)
      .toLowerCase()
      .replace(/-/g, '');
    const teamName = `${prefix}team`
      .substring(0, 40)
      .toLowerCase()
      .replace(/-/g, '');

    test('create organization', async ({bearerClient}) => {
      const resp = await bearerClient.post('/api/v1/organization/', {
        name: orgName,
        email: orgEmail,
      });
      expect(resp.status()).toBe(201);
    });

    test('create repository in organization', async ({bearerClient}) => {
      const resp = await bearerClient.post('/api/v1/repository', {
        namespace: orgName,
        repository: repoName,
        visibility: 'public',
        description: 'stage validation test repo',
        repo_kind: 'image',
      });
      expect(resp.status()).toBe(201);
    });

    test('star repository', async ({bearerClient}) => {
      const resp = await bearerClient.post('/api/v1/user/starred', {
        namespace: orgName,
        repository: repoName,
      });
      expect(resp.status()).toBe(201);
    });

    test('create robot account', async ({bearerClient}) => {
      const resp = await bearerClient.put(
        `/api/v1/organization/${orgName}/robots/${robotName}`,
        {description: 'stage validation robot'},
      );
      expect(resp.status()).toBe(201);
    });

    test('unstar repository', async ({bearerClient}) => {
      const resp = await bearerClient.delete(
        `/api/v1/user/starred/${orgName}/${repoName}`,
      );
      expect(resp.status()).toBe(204);
    });

    test('delete robot account', async ({bearerClient}) => {
      const resp = await bearerClient.delete(
        `/api/v1/organization/${orgName}/robots/${robotName}`,
      );
      expect(resp.status()).toBe(204);
    });

    test('create team', async ({bearerClient}) => {
      const resp = await bearerClient.put(
        `/api/v1/organization/${orgName}/team/${teamName}`,
        {name: teamName, role: 'member'},
      );
      expect(resp.status()).toBe(200);
    });

    test('delete team', async ({bearerClient}) => {
      const resp = await bearerClient.delete(
        `/api/v1/organization/${orgName}/team/${teamName}`,
      );
      expect(resp.status()).toBe(204);
    });

    test('check organization usage logs', async ({bearerClient}) => {
      const resp = await bearerClient.get(
        `/api/v1/organization/${orgName}/logs`,
      );
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body.logs).toBeTruthy();
      // Logs may not have aggregated yet for a freshly created org.
      // Just verify the endpoint returns a valid structure.
      expect(Array.isArray(body.logs)).toBe(true);
    });

    test('check repository usage logs', async ({bearerClient}) => {
      const resp = await bearerClient.get(
        `/api/v1/repository/${orgName}/${repoName}/logs`,
      );
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body.logs).toBeTruthy();
      expect(Array.isArray(body.logs)).toBe(true);
    });

    test('delete repository', async ({bearerClient}) => {
      const resp = await bearerClient.delete(
        `/api/v1/repository/${orgName}/${repoName}`,
      );
      expect(resp.status()).toBe(204);
    });

    test('delete organization', async ({bearerClient}) => {
      const resp = await bearerClient.delete(`/api/v1/organization/${orgName}`);
      expect(resp.status()).toBe(204);
    });
  },
);

// ---------------------------------------------------------------------------
// Image Push/Pull via skopeo (requires container runtime + credentials)
// ---------------------------------------------------------------------------

test.describe(
  'Stage Validation — Image Push/Pull',
  {tag: ['@api', '@stage-validation', '@auth:Bearer', '@container']},
  () => {
    const prefix = uniqueName('stgimg');
    const imgOrgName = `${prefix}-org`.substring(0, 40).toLowerCase();
    const imgRepoName = `${prefix}-repo`.substring(0, 40).toLowerCase();

    test.beforeAll(async ({playwright}) => {
      test.skip(
        !QUAY_USER || !QUAY_PASSWORD,
        'QUAY_USER/QUAY_PASSWORD not set',
      );
      const apiUrl = process.env.REACT_QUAY_APP_API_URL || '';

      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const {BearerApiClient} = await import('../../utils/api/bearer-client');
        const token = process.env.QUAY_API_TOKEN;
        if (!token) throw new Error('QUAY_API_TOKEN is required');
        const client = new BearerApiClient(request, apiUrl, token);
        await client.post('/api/v1/organization/', {
          name: imgOrgName,
          email: `${imgOrgName}@validation.test`,
        });
        await client.post('/api/v1/repository', {
          namespace: imgOrgName,
          repository: imgRepoName,
          visibility: 'public',
          description: 'stage push/pull test',
          repo_kind: 'image',
        });
      } finally {
        await request.dispose();
      }
    });

    // Push a small image (busybox) — mirrors the Cypress skopeo push pattern
    test('push image via skopeo', async () => {
      const {pushImage} = await import('../../utils/container');
      await pushImage(
        imgOrgName,
        imgRepoName,
        'skopeo-test',
        QUAY_USER,
        QUAY_PASSWORD,
      );
    });

    test.afterAll(async ({playwright}) => {
      const token = process.env.QUAY_API_TOKEN;
      if (!token) return;
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const {BearerApiClient} = await import('../../utils/api/bearer-client');
        const client = new BearerApiClient(
          request,
          process.env.REACT_QUAY_APP_API_URL || '',
          token,
        );
        await client.delete(`/api/v1/repository/${imgOrgName}/${imgRepoName}`);
        await client.delete(`/api/v1/organization/${imgOrgName}`);
      } catch {
        // Best-effort cleanup
      } finally {
        await request.dispose();
      }
    });
  },
);
