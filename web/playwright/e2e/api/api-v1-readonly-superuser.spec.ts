/**
 * Readonly Superuser Role API Tests
 *
 * Validates that a user listed in GLOBAL_READONLY_SUPER_USERS can read (GET)
 * all API resources but cannot mutate (POST/PUT/DELETE) them.
 *
 * Three client roles are used:
 *   - adminClient  : full superuser for setup and teardown
 *   - userClient   : normal user for creating test data
 *   - readonlyClient : readonly superuser under test
 *
 * Ported from Cypress: quay_api_testing_gobal_readonly_supuer_user.cy.js
 */

import {test, expect, uniqueName} from '../../fixtures';
import {RawApiClient} from '../../utils/api';
import {API_URL} from '../../utils/config';
import {TEST_USERS, TEST_USERS_OIDC} from '../../global-setup';

test.describe(
  'Readonly Superuser API',
  {tag: ['@api', '@auth:Database']},
  () => {
    let readonlyClient: RawApiClient;

    // Shared test data names (set once in beforeAll)
    let orgName: string;
    let repoName: string;
    let teamName: string;
    let robotShortname: string;
    let normalUsername: string;

    test.beforeAll(async ({playwright, cachedQuayConfig}) => {
      // Build a readonly client
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      readonlyClient = new RawApiClient(request, API_URL);
      const users =
        cachedQuayConfig?.config?.AUTHENTICATION_TYPE === 'OIDC'
          ? TEST_USERS_OIDC
          : TEST_USERS;

      try {
        await readonlyClient.signIn(
          users.readonly.username,
          users.readonly.password,
        );
      } catch (err: unknown) {
        // Skip when the readonly user is genuinely not configured (auth
        // rejection), but let infrastructure errors (5xx, network) fail loudly.
        const status =
          err != null &&
          typeof err === 'object' &&
          'status' in err &&
          typeof (err as {status: unknown}).status === 'number'
            ? (err as {status: number}).status
            : undefined;
        if (status === 401 || status === 403) {
          test.skip(true, 'Readonly superuser is not configured');
          return;
        }
        throw err;
      }

      // Verify readonly user actually has superuser privileges
      // (GET /api/v1/superuser/users/ requires superuser access)
      const suCheck = await readonlyClient.get('/api/v1/superuser/users/');
      if (suCheck.status() === 401 || suCheck.status() === 403) {
        test.skip(true, 'Readonly user does not have superuser privileges');
        return;
      }
      expect(suCheck.status()).toBe(200);

      // Prepare unique names
      orgName = uniqueName('roorg');
      repoName = uniqueName('rorepo');
      teamName = uniqueName('roteam');
      robotShortname = uniqueName('robot').replace(/-/g, '_');
      normalUsername = users.user.username;
    });

    // ========================================================================
    // Section 1 -- Public / unauthenticated-style GETs
    // ========================================================================

    test.describe('Public endpoints', () => {
      test('can GET /api/v1/discovery', async () => {
        const r = await readonlyClient.get('/api/v1/discovery');
        expect(r.status()).toBe(200);
      });

      test('can GET error descriptions', async () => {
        const errors = [
          'expired_token',
          'fresh_login_required',
          'invalid_token',
          'insufficient_scope',
          'invalid_request',
          'exceeds_license',
          'external_service_timeout',
          'not_found',
          'invalid_response',
        ];
        for (const errorType of errors) {
          const r = await readonlyClient.get(`/api/v1/error/${errorType}`);
          expect(r.status()).toBe(200);
          const body = await r.json();
          expect(body.title).toBe(errorType);
        }
      });

      test('can GET /health/instance', async () => {
        const r = await readonlyClient.get('/health/instance');
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.data.services.database).toBe(true);
      });

      test('can GET /health/endtoend', async () => {
        const r = await readonlyClient.get('/health/endtoend');
        expect(r.status()).toBe(200);
      });

      test('can GET /health/warning', async () => {
        const r = await readonlyClient.get('/health/warning');
        expect(r.status()).toBe(200);
      });
    });

    // ========================================================================
    // Section 2 -- User info
    // ========================================================================

    test.describe('User info', () => {
      test('can GET own user info', async () => {
        const r = await readonlyClient.get('/api/v1/user/');
        expect(r.status()).toBe(200);
        const body = await r.json();
        // The readonly user should be recognized
        expect(body.username).toBeTruthy();
      });

      test('can GET another user info', async () => {
        const r = await readonlyClient.get(`/api/v1/users/${normalUsername}`);
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.username).toBe(normalUsername);
      });

      test('can GET user aggregate logs', async () => {
        const r = await readonlyClient.get('/api/v1/user/aggregatelogs');
        expect(r.status()).toBe(200);
      });
    });

    // ========================================================================
    // Section 3 -- Organization CRUD
    // ========================================================================

    test.describe('Organization', () => {
      test.beforeAll(async ({adminClient}) => {
        // Create org with admin
        const create = await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        expect(create.status()).toBe(201);
      });

      test.afterAll(async ({adminClient}) => {
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET organization', async () => {
        const r = await readonlyClient.get(`/api/v1/organization/${orgName}`);
        expect(r.status()).toBe(200);
      });

      test('cannot DELETE organization', async () => {
        const r = await readonlyClient.delete(
          `/api/v1/organization/${orgName}`,
        );
        expect(r.status()).toBe(403);
      });

      test('cannot PUT (update) organization', async () => {
        const r = await readonlyClient.put(`/api/v1/organization/${orgName}`, {
          email: 'hacked@example.com',
        });
        expect(r.status()).toBe(403);
      });

      test('can GET organization collaborators', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/collaborators`,
        );
        expect(r.status()).toBe(200);
      });

      test('can GET organization logs', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/logs`,
        );
        expect(r.status()).toBe(200);
      });

      test('can GET organization aggregate logs', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/aggregatelogs`,
        );
        expect(r.status()).toBe(200);
      });
    });

    // ========================================================================
    // Section 4 -- Organization Application
    // ========================================================================

    test.describe('Organization Application', () => {
      let appClientId: string;

      test.beforeAll(async ({adminClient}) => {
        // Ensure org exists
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        // Create app as admin
        const appResp = await adminClient.post(
          `/api/v1/organization/${orgName}/applications`,
          {name: 'testapp_ro'},
        );
        expect(appResp.status()).toBe(200);
        const appBody = await appResp.json();
        appClientId = appBody.client_id;
      });

      test.afterAll(async ({adminClient}) => {
        if (appClientId) {
          await adminClient.delete(
            `/api/v1/organization/${orgName}/applications/${appClientId}`,
          );
        }
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET organization application', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/applications/${appClientId}`,
        );
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.name).toBe('testapp_ro');
      });

      test('cannot POST new organization application', async () => {
        const r = await readonlyClient.post(
          `/api/v1/organization/${orgName}/applications`,
          {name: 'should_fail'},
        );
        expect(r.status()).toBe(403);
      });
    });

    // ========================================================================
    // Section 5 -- Repository
    // ========================================================================

    test.describe('Repository', () => {
      test.beforeAll(async ({adminClient}) => {
        // Ensure org
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        // Create repo
        const repoResp = await adminClient.post('/api/v1/repository', {
          namespace: orgName,
          repository: repoName,
          visibility: 'public',
          description: 'readonly superuser test repo',
          repo_kind: 'image',
        });
        expect(repoResp.status()).toBe(201);
      });

      test.afterAll(async ({adminClient}) => {
        await adminClient.delete(`/api/v1/repository/${orgName}/${repoName}`);
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET repository', async () => {
        const r = await readonlyClient.get(
          `/api/v1/repository/${orgName}/${repoName}`,
        );
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.name).toBe(repoName);
      });

      test('cannot DELETE repository', async () => {
        const r = await readonlyClient.delete(
          `/api/v1/repository/${orgName}/${repoName}`,
        );
        expect(r.status()).toBe(403);
      });

      test('cannot POST new repository', async () => {
        const r = await readonlyClient.post('/api/v1/repository', {
          namespace: orgName,
          repository: 'should_fail',
          visibility: 'private',
          description: 'should fail',
          repo_kind: 'image',
        });
        expect(r.status()).toBe(403);
      });

      test('can GET repository tags', async () => {
        const r = await readonlyClient.get(
          `/api/v1/repository/${orgName}/${repoName}/tag/`,
        );
        expect(r.status()).toBe(200);
      });

      test('can GET repository logs', async () => {
        const r = await readonlyClient.get(
          `/api/v1/repository/${orgName}/${repoName}/logs`,
        );
        expect(r.status()).toBe(200);
      });

      test('can GET repository aggregate logs', async () => {
        const r = await readonlyClient.get(
          `/api/v1/repository/${orgName}/${repoName}/aggregatelogs`,
        );
        expect(r.status()).toBe(200);
      });

      test('can list repository notifications', async () => {
        const r = await readonlyClient.get(
          `/api/v1/repository/${orgName}/${repoName}/notification/`,
        );
        expect(r.status()).toBe(200);
      });

      test('cannot POST repository notification', async () => {
        const r = await readonlyClient.post(
          `/api/v1/repository/${orgName}/${repoName}/notification/`,
          {
            event: 'repo_push',
            method: 'quay_notification',
            config: {target: {name: 'owners', kind: 'team'}},
            title: 'should_fail',
          },
        );
        expect(r.status()).toBe(403);
      });
    });

    // ========================================================================
    // Section 6 -- Permissions
    // ========================================================================

    test.describe('Permissions', () => {
      test.beforeAll(async ({adminClient}) => {
        // Ensure org + repo exist
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await adminClient.post('/api/v1/repository', {
          namespace: orgName,
          repository: repoName,
          visibility: 'public',
          description: 'readonly superuser test repo',
          repo_kind: 'image',
        });

        // Set a user permission so there's something to read
        await adminClient.put(
          `/api/v1/repository/${orgName}/${repoName}/permissions/user/${normalUsername}`,
          {role: 'write'},
        );
      });

      test.afterAll(async ({adminClient}) => {
        await adminClient.delete(`/api/v1/repository/${orgName}/${repoName}`);
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET user permission on repo', async () => {
        const r = await readonlyClient.get(
          `/api/v1/repository/${orgName}/${repoName}/permissions/user/${normalUsername}`,
        );
        expect(r.status()).toBe(200);
      });

      test('can GET transitive permission', async () => {
        const r = await readonlyClient.get(
          `/api/v1/repository/${orgName}/${repoName}/permissions/user/${normalUsername}/transitive`,
        );
        expect(r.status()).toBe(200);
      });

      test('cannot PUT permission on repo', async () => {
        const r = await readonlyClient.put(
          `/api/v1/repository/${orgName}/${repoName}/permissions/user/${normalUsername}`,
          {role: 'admin'},
        );
        expect(r.status()).toBe(403);
      });

      test('cannot DELETE permission on repo', async () => {
        const r = await readonlyClient.delete(
          `/api/v1/repository/${orgName}/${repoName}/permissions/user/${normalUsername}`,
        );
        expect(r.status()).toBe(403);
      });
    });

    // ========================================================================
    // Section 7 -- Teams
    // ========================================================================

    test.describe('Teams', () => {
      test.beforeAll(async ({adminClient}) => {
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await adminClient.post('/api/v1/repository', {
          namespace: orgName,
          repository: repoName,
          visibility: 'public',
          description: 'readonly superuser test repo',
          repo_kind: 'image',
        });

        // Create team
        await adminClient.put(
          `/api/v1/organization/${orgName}/team/${teamName}`,
          {name: teamName, role: 'member'},
        );

        // Add team permission on repo
        await adminClient.put(
          `/api/v1/repository/${orgName}/${repoName}/permissions/team/${teamName}`,
          {role: 'write'},
        );

        // Add member to team
        await adminClient.put(
          `/api/v1/organization/${orgName}/team/${teamName}/members/${normalUsername}`,
        );
      });

      test.afterAll(async ({adminClient}) => {
        await adminClient.delete(
          `/api/v1/organization/${orgName}/team/${teamName}`,
        );
        await adminClient.delete(`/api/v1/repository/${orgName}/${repoName}`);
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET team', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/team/${teamName}/members`,
        );
        expect(r.status()).toBe(200);
      });

      test('can GET team permissions', async () => {
        const r = await readonlyClient.get(
          `/api/v1/repository/${orgName}/${repoName}/permissions/team/${teamName}`,
        );
        expect(r.status()).toBe(200);
      });

      test('can GET organization member', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/members`,
        );
        expect(r.status()).toBe(200);
      });

      test('can GET team member', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/team/${teamName}/members`,
        );
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.members).toBeTruthy();
      });

      test('cannot PUT (create) team', async () => {
        const r = await readonlyClient.put(
          `/api/v1/organization/${orgName}/team/shouldfail`,
          {name: 'shouldfail', role: 'member'},
        );
        expect(r.status()).toBe(403);
      });

      test('cannot DELETE team', async () => {
        const r = await readonlyClient.delete(
          `/api/v1/organization/${orgName}/team/${teamName}`,
        );
        expect(r.status()).toBe(403);
      });

      test('cannot PUT team member', async () => {
        const r = await readonlyClient.put(
          `/api/v1/organization/${orgName}/team/${teamName}/members/shouldfail`,
        );
        expect(r.status()).toBe(403);
      });

      test('cannot DELETE team member', async () => {
        const r = await readonlyClient.delete(
          `/api/v1/organization/${orgName}/team/${teamName}/members/${normalUsername}`,
        );
        expect(r.status()).toBe(403);
      });
    });

    // ========================================================================
    // Section 8 -- Robot accounts
    // ========================================================================

    test.describe('Robot accounts', () => {
      test.beforeAll(async ({adminClient}) => {
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        // Create robot
        await adminClient.put(
          `/api/v1/organization/${orgName}/robots/${robotShortname}`,
          {},
        );
      });

      test.afterAll(async ({adminClient}) => {
        await adminClient.delete(
          `/api/v1/organization/${orgName}/robots/${robotShortname}`,
        );
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET robot account', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/robots/${robotShortname}`,
        );
        expect(r.status()).toBe(200);
      });

      test('can list all robot accounts', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/robots`,
        );
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.robots.length).toBeGreaterThanOrEqual(1);
      });

      test('cannot PUT (create) robot account', async () => {
        const r = await readonlyClient.put(
          `/api/v1/organization/${orgName}/robots/shouldfail`,
          {},
        );
        expect(r.status()).toBe(403);
      });

      test('cannot DELETE robot account', async () => {
        const r = await readonlyClient.delete(
          `/api/v1/organization/${orgName}/robots/${robotShortname}`,
        );
        expect(r.status()).toBe(403);
      });
    });

    // ========================================================================
    // Section 9 -- Default permissions (prototypes)
    // ========================================================================

    test.describe('Default permissions', () => {
      test.beforeAll(async ({adminClient}) => {
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        // Create robot for prototype delegate
        await adminClient.put(
          `/api/v1/organization/${orgName}/robots/${robotShortname}`,
          {},
        );

        // Create default permission
        await adminClient.post(`/api/v1/organization/${orgName}/prototypes`, {
          delegate: {
            name: `${orgName}+${robotShortname}`,
            kind: 'user',
            is_robot: true,
          },
          role: 'read',
        });
      });

      test.afterAll(async ({adminClient}) => {
        await adminClient.delete(
          `/api/v1/organization/${orgName}/robots/${robotShortname}`,
        );
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET default permissions', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/prototypes`,
        );
        expect(r.status()).toBe(200);
      });

      test('cannot POST default permission', async () => {
        const r = await readonlyClient.post(
          `/api/v1/organization/${orgName}/prototypes`,
          {
            delegate: {
              name: `${orgName}+${robotShortname}`,
              kind: 'user',
              is_robot: true,
            },
            role: 'write',
          },
        );
        expect(r.status()).toBe(403);
      });
    });

    // ========================================================================
    // Section 10 -- Global messages
    // ========================================================================

    test.describe('Global messages', () => {
      let globalMessageUuid: string;

      test.beforeAll(async ({adminClient}) => {
        // Create a global message as superuser
        const msgResp = await adminClient.post('/api/v1/messages', {
          message: {
            media_type: 'text/markdown',
            severity: 'info',
            content: 'readonly test message',
          },
        });
        expect(msgResp.status()).toBe(201);
        const text = await msgResp.text();
        if (text) {
          const msgBody = JSON.parse(text);
          globalMessageUuid = msgBody.uuid;
        } else {
          // Server returned 201 with empty body; look up the message via GET
          const list = await adminClient.get('/api/v1/messages');
          const listBody = await list.json();
          const created = listBody.messages?.find(
            (m: {content: string}) => m.content === 'readonly test message',
          );
          if (created) {
            globalMessageUuid = created.uuid;
          }
        }
      });

      test.afterAll(async ({adminClient}) => {
        // Clean up the specific message we created
        if (globalMessageUuid) {
          await adminClient.delete(`/api/v1/message/${globalMessageUuid}`);
        }
      });

      test('can GET global messages', async () => {
        const r = await readonlyClient.get('/api/v1/messages');
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.messages.length).toBeGreaterThanOrEqual(1);
      });

      test('cannot POST global message', async () => {
        const r = await readonlyClient.post('/api/v1/messages', {
          message: {
            media_type: 'text/markdown',
            severity: 'info',
            content: 'should fail',
          },
        });
        expect(r.status()).toBe(403);
      });

      test('cannot DELETE global message', async () => {
        // First get a valid UUID
        const msgs = await readonlyClient.get('/api/v1/messages');
        const body = await msgs.json();
        if (body.messages?.length > 0) {
          const uuid = body.messages[0].uuid;
          const r = await readonlyClient.delete(`/api/v1/message/${uuid}`);
          expect(r.status()).toBe(403);
        }
      });
    });

    // ========================================================================
    // Section 11 -- Superuser endpoints
    // ========================================================================

    test.describe('Superuser endpoints', () => {
      test('can GET superuser users list', async () => {
        const r = await readonlyClient.get('/api/v1/superuser/users/');
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.users).toBeTruthy();
        expect(body.users.length).toBeGreaterThanOrEqual(1);
      });

      test('cannot DELETE superuser user', async () => {
        // Attempt to delete a user that doesn't exist; the point is 403 not 404
        const r = await readonlyClient.delete(
          '/api/v1/superuser/users/nonexistent_user_ro_test',
        );
        expect(r.status()).toBe(403);
      });

      test('can GET registry status', async () => {
        const r = await readonlyClient.get('/api/v1/superuser/registrystatus');
        // 200 = accessible, some deployments may return 404 if not k8s
        expect([200, 404]).toContain(r.status());
      });

      test('can GET registry size', async () => {
        const r = await readonlyClient.get('/api/v1/superuser/registrysize/');
        // 200 if calculated, 404 if never triggered
        expect([200, 404]).toContain(r.status());
      });

      test('cannot POST registry size calculation', async () => {
        const r = await readonlyClient.post(
          '/api/v1/superuser/registrysize/',
          {},
        );
        expect(r.status()).toBe(403);
      });
    });

    // ========================================================================
    // Section 12 -- Service keys
    // ========================================================================

    test.describe('Service keys', () => {
      let serviceKid: string;

      test.beforeAll(async ({adminClient}) => {
        const keyResp = await adminClient.post('/api/v1/superuser/keys', {
          name: 'ro_test_key',
          service: 'quay',
          expiration: null,
        });
        expect(keyResp.status()).toBe(200);
        const keyBody = await keyResp.json();
        serviceKid = keyBody.kid;
      });

      test.afterAll(async ({adminClient}) => {
        if (serviceKid) {
          await adminClient.delete(`/api/v1/superuser/keys/${serviceKid}`);
        }
      });

      test('can GET service keys list', async () => {
        const r = await readonlyClient.get('/api/v1/superuser/keys');
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.keys).toBeTruthy();
      });

      test('can GET specific service key', async () => {
        const r = await readonlyClient.get(
          `/api/v1/superuser/keys/${serviceKid}`,
        );
        expect(r.status()).toBe(200);
      });

      test('cannot POST service key', async () => {
        const r = await readonlyClient.post('/api/v1/superuser/keys', {
          name: 'should_fail',
          service: 'quay',
          expiration: null,
        });
        expect(r.status()).toBe(403);
      });

      test('cannot DELETE service key', async () => {
        const r = await readonlyClient.delete(
          `/api/v1/superuser/keys/${serviceKid}`,
        );
        expect(r.status()).toBe(403);
      });
    });

    // ========================================================================
    // Section 13 -- Stars
    // ========================================================================

    test.describe('Stars', () => {
      test.beforeAll(async ({adminClient}) => {
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await adminClient.post('/api/v1/repository', {
          namespace: orgName,
          repository: repoName,
          visibility: 'public',
          description: 'readonly superuser test repo',
          repo_kind: 'image',
        });
      });

      test.afterAll(async ({adminClient}) => {
        await adminClient.delete(`/api/v1/repository/${orgName}/${repoName}`);
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET starred repos', async () => {
        const r = await readonlyClient.get('/api/v1/user/starred');
        expect(r.status()).toBe(200);
      });

      test('can POST star (own action)', async () => {
        // Starring is a user action on their own account, should be allowed
        const r = await readonlyClient.post('/api/v1/user/starred', {
          namespace: orgName,
          repository: repoName,
        });
        // 200/201 = starred, 409 = already starred (idempotent)
        expect([200, 201, 409]).toContain(r.status());
      });
    });

    // ========================================================================
    // Section 14 -- Search
    // ========================================================================

    test.describe('Search', () => {
      test('can search all entities', async () => {
        const r = await readonlyClient.get('/api/v1/find/all?query=test');
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.results).toBeTruthy();
      });

      test('can search repositories', async () => {
        const r = await readonlyClient.get(
          '/api/v1/find/repositories?query=test',
        );
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.results).toBeTruthy();
      });

      test('can search entities by prefix', async () => {
        const r = await readonlyClient.get('/api/v1/entities/test');
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.results).toBeTruthy();
      });
    });

    // ========================================================================
    // Section 15 -- Proxy cache
    // ========================================================================

    test.describe('Proxy cache', {tag: ['@feature:PROXY_CACHE']}, () => {
      test.beforeAll(async ({adminClient}) => {
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
      });

      test.afterAll(async ({adminClient}) => {
        // Clean up proxy cache if it was created
        await adminClient.delete(`/api/v1/organization/${orgName}/proxycache`);
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET proxy cache config (may be empty)', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/proxycache`,
        );
        // 200 if config exists, 404 if not configured
        expect([200, 404]).toContain(r.status());
      });

      test('cannot POST proxy cache config', async () => {
        const r = await readonlyClient.post(
          `/api/v1/organization/${orgName}/proxycache`,
          {
            upstream_registry: 'docker.io',
            expiration_s: 86400,
            insecure: false,
          },
        );
        expect(r.status()).toBe(403);
      });

      test('cannot DELETE proxy cache config', async () => {
        const r = await readonlyClient.delete(
          `/api/v1/organization/${orgName}/proxycache`,
        );
        expect(r.status()).toBe(403);
      });
    });

    // ========================================================================
    // Section 16 -- Quotas
    // ========================================================================

    test.describe('Quotas', {tag: ['@feature:QUOTA_MANAGEMENT']}, () => {
      let quotaId: string;

      test.beforeAll(async ({adminClient}) => {
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        // Create a quota
        const qResp = await adminClient.post(
          `/api/v1/organization/${orgName}/quota`,
          {limit_bytes: 1024000000},
        );
        expect(qResp.status()).toBe(201);

        // Fetch quota ID
        const listResp = await adminClient.get(
          `/api/v1/organization/${orgName}/quota`,
        );
        const quotas = await listResp.json();
        if (Array.isArray(quotas) && quotas.length > 0) {
          quotaId = quotas[0].id;
        }
      });

      test.afterAll(async ({adminClient}) => {
        if (quotaId) {
          await adminClient.delete(
            `/api/v1/organization/${orgName}/quota/${quotaId}`,
          );
        }
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET organization quota list', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/quota`,
        );
        expect(r.status()).toBe(200);
      });

      test('can GET organization quota by ID', async () => {
        test.skip(!quotaId, 'No quota ID available');
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/quota/${quotaId}`,
        );
        expect(r.status()).toBe(200);
      });

      test('cannot POST organization quota', async () => {
        const r = await readonlyClient.post(
          `/api/v1/organization/${orgName}/quota`,
          {limit_bytes: 999999},
        );
        expect(r.status()).toBe(403);
      });

      test('cannot DELETE organization quota', async () => {
        test.skip(!quotaId, 'No quota ID available');
        const r = await readonlyClient.delete(
          `/api/v1/organization/${orgName}/quota/${quotaId}`,
        );
        expect(r.status()).toBe(403);
      });

      test('can GET superuser organization quota', async () => {
        const r = await readonlyClient.get(
          `/api/v1/superuser/organization/${orgName}/quota`,
        );
        expect(r.status()).toBe(200);
      });

      test('cannot POST superuser organization quota', async () => {
        const r = await readonlyClient.post(
          `/api/v1/superuser/organization/${orgName}/quota`,
          {limit_bytes: 999999},
        );
        expect(r.status()).toBe(403);
      });
    });

    // ========================================================================
    // Section 17 -- Auto-prune policies
    // ========================================================================

    test.describe('Auto-prune policies', {tag: ['@feature:AUTO_PRUNE']}, () => {
      let orgPolicyUuid: string;

      test.beforeAll(async ({adminClient}) => {
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        // Create org autoprune policy
        const policyResp = await adminClient.post(
          `/api/v1/organization/${orgName}/autoprunepolicy/`,
          {method: 'number_of_tags', value: 6},
        );
        if (policyResp.status() === 201) {
          const policyBody = await policyResp.json();
          orgPolicyUuid = policyBody.uuid;
        }
      });

      test.afterAll(async ({adminClient}) => {
        if (orgPolicyUuid) {
          await adminClient.delete(
            `/api/v1/organization/${orgName}/autoprunepolicy/${orgPolicyUuid}`,
          );
        }
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET org autoprune policies', async () => {
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/autoprunepolicy/`,
        );
        expect(r.status()).toBe(200);
      });

      test('can GET specific org autoprune policy', async () => {
        test.skip(!orgPolicyUuid, 'No autoprune policy UUID available');
        const r = await readonlyClient.get(
          `/api/v1/organization/${orgName}/autoprunepolicy/${orgPolicyUuid}`,
        );
        expect(r.status()).toBe(200);
      });

      test('cannot POST org autoprune policy', async () => {
        const r = await readonlyClient.post(
          `/api/v1/organization/${orgName}/autoprunepolicy/`,
          {method: 'number_of_tags', value: 99},
        );
        expect(r.status()).toBe(403);
      });

      test('cannot DELETE org autoprune policy', async () => {
        test.skip(!orgPolicyUuid, 'No autoprune policy UUID available');
        const r = await readonlyClient.delete(
          `/api/v1/organization/${orgName}/autoprunepolicy/${orgPolicyUuid}`,
        );
        expect(r.status()).toBe(403);
      });

      test('can GET user autoprune policies', async () => {
        const r = await readonlyClient.get('/api/v1/user/autoprunepolicy/');
        expect(r.status()).toBe(200);
      });

      test('can POST user autoprune policy (self-action)', async () => {
        // Readonly superusers are admin of their own namespace, so user-level
        // autoprune policies are a self-action that is allowed (like starring).
        const r = await readonlyClient.post('/api/v1/user/autoprunepolicy/', {
          method: 'number_of_tags',
          value: 99,
        });
        // 201 = created, 400 = policy already exists
        expect([201, 400]).toContain(r.status());
      });
    });

    // ========================================================================
    // Section 18 -- Repository auto-prune policies
    // ========================================================================

    test.describe(
      'Repository auto-prune policies',
      {tag: ['@feature:AUTO_PRUNE']},
      () => {
        let repoPolicyUuid: string;

        test.beforeAll(async ({adminClient}) => {
          await adminClient.post('/api/v1/organization/', {
            name: orgName,
            email: `${orgName}@example.com`,
          });
          await adminClient.post('/api/v1/repository', {
            namespace: orgName,
            repository: repoName,
            visibility: 'public',
            description: 'readonly superuser test repo',
            repo_kind: 'image',
          });

          // Create repo autoprune policy
          const policyResp = await adminClient.post(
            `/api/v1/repository/${orgName}/${repoName}/autoprunepolicy/`,
            {method: 'number_of_tags', value: 10},
          );
          if (policyResp.status() === 201) {
            const policyBody = await policyResp.json();
            repoPolicyUuid = policyBody.uuid;
          }
        });

        test.afterAll(async ({adminClient}) => {
          if (repoPolicyUuid) {
            await adminClient.delete(
              `/api/v1/repository/${orgName}/${repoName}/autoprunepolicy/${repoPolicyUuid}`,
            );
          }
          await adminClient.delete(`/api/v1/repository/${orgName}/${repoName}`);
          await adminClient.delete(`/api/v1/organization/${orgName}`);
        });

        test('can GET repo autoprune policies', async () => {
          const r = await readonlyClient.get(
            `/api/v1/repository/${orgName}/${repoName}/autoprunepolicy/`,
          );
          expect(r.status()).toBe(200);
        });

        test('can GET specific repo autoprune policy', async () => {
          test.skip(!repoPolicyUuid, 'No repo autoprune policy UUID');
          const r = await readonlyClient.get(
            `/api/v1/repository/${orgName}/${repoName}/autoprunepolicy/${repoPolicyUuid}`,
          );
          expect(r.status()).toBe(200);
        });

        test('cannot POST repo autoprune policy', async () => {
          const r = await readonlyClient.post(
            `/api/v1/repository/${orgName}/${repoName}/autoprunepolicy/`,
            {method: 'number_of_tags', value: 99},
          );
          expect(r.status()).toBe(403);
        });

        test('cannot DELETE repo autoprune policy', async () => {
          test.skip(!repoPolicyUuid, 'No repo autoprune policy UUID');
          const r = await readonlyClient.delete(
            `/api/v1/repository/${orgName}/${repoName}/autoprunepolicy/${repoPolicyUuid}`,
          );
          expect(r.status()).toBe(403);
        });
      },
    );

    // ========================================================================
    // Section 19 -- Mirror config
    // ========================================================================

    test.describe('Mirror config', {tag: ['@feature:REPO_MIRROR']}, () => {
      test.beforeAll(async ({adminClient}) => {
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await adminClient.post('/api/v1/repository', {
          namespace: orgName,
          repository: repoName,
          visibility: 'public',
          description: 'readonly superuser test repo',
          repo_kind: 'image',
        });
      });

      test.afterAll(async ({adminClient}) => {
        await adminClient.delete(`/api/v1/repository/${orgName}/${repoName}`);
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET mirror config (may be empty)', async () => {
        const r = await readonlyClient.get(
          `/api/v1/repository/${orgName}/${repoName}/mirror`,
        );
        // 200 if config exists, 404 if not configured
        expect([200, 404]).toContain(r.status());
      });

      test('cannot POST mirror config', async ({adminClient}) => {
        const mirrorBot = uniqueName('mirrorbot').replace(/-/g, '_');
        // Create the robot first via admin so the API doesn't reject for missing robot
        await adminClient.put(
          `/api/v1/organization/${orgName}/robots/${mirrorBot}`,
          {description: 'mirror robot for test'},
        );

        const r = await readonlyClient.post(
          `/api/v1/repository/${orgName}/${repoName}/mirror`,
          {
            is_enabled: false,
            external_reference: 'docker.io/library/alpine',
            sync_interval: 3600,
            sync_start_date: '2025-01-01T00:00:00Z',
            root_rule: {rule_kind: 'tag_glob_csv', rule_value: ['latest']},
            robot_username: `${orgName}+${mirrorBot}`,
          },
        );
        expect(r.status()).toBe(403);
      });
    });

    // ========================================================================
    // Section 20 -- Notifications (read specific)
    // ========================================================================

    test.describe('Notifications', () => {
      let notificationUuid: string;

      test.beforeAll(async ({adminClient}) => {
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await adminClient.post('/api/v1/repository', {
          namespace: orgName,
          repository: repoName,
          visibility: 'public',
          description: 'readonly superuser test repo',
          repo_kind: 'image',
        });

        // Create a notification
        const notifResp = await adminClient.post(
          `/api/v1/repository/${orgName}/${repoName}/notification/`,
          {
            event: 'repo_push',
            method: 'quay_notification',
            config: {
              target: {
                name: 'owners',
                kind: 'team',
                is_robot: false,
              },
            },
            eventConfig: {},
            title: 'ro_test_notification',
          },
        );
        expect(notifResp.status()).toBe(201);
        const notifBody = await notifResp.json();
        expect(notifBody.uuid).toBeTruthy();
        notificationUuid = notifBody.uuid;
      });

      test.afterAll(async ({adminClient}) => {
        if (notificationUuid) {
          await adminClient.delete(
            `/api/v1/repository/${orgName}/${repoName}/notification/${notificationUuid}`,
          );
        }
        await adminClient.delete(`/api/v1/repository/${orgName}/${repoName}`);
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      });

      test('can GET specific notification', async () => {
        test.skip(!notificationUuid, 'No notification UUID available');
        const r = await readonlyClient.get(
          `/api/v1/repository/${orgName}/${repoName}/notification/${notificationUuid}`,
        );
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.uuid).toBe(notificationUuid);
      });

      test('cannot DELETE notification', async () => {
        test.skip(!notificationUuid, 'No notification UUID available');
        const r = await readonlyClient.delete(
          `/api/v1/repository/${orgName}/${repoName}/notification/${notificationUuid}`,
        );
        expect(r.status()).toBe(403);
      });
    });

    // ========================================================================
    // Section 21 -- App tokens
    // ========================================================================

    test.describe('App tokens', () => {
      let createdTokenCode: string | undefined;

      test.afterAll(async () => {
        // Revoke the token we created during the test
        if (createdTokenCode) {
          await readonlyClient.delete(
            `/api/v1/user/apptoken/${createdTokenCode}`,
          );
        }
      });

      test('can GET own app tokens', async () => {
        const r = await readonlyClient.get('/api/v1/user/apptoken');
        expect(r.status()).toBe(200);
      });

      test('can POST own app token (self-action)', async () => {
        const r = await readonlyClient.post('/api/v1/user/apptoken', {
          title: 'ro_test_token',
        });
        // Creating a token for one's own account is a self-action, not a write
        expect(r.status()).toBe(200);
        const body = await r.json();
        if (body.token?.uuid) {
          createdTokenCode = body.token.uuid;
        }
      });
    });

    // ========================================================================
    // Section 22 -- Backfill status
    // ========================================================================

    test.describe('Security scanner backfill', () => {
      test('can GET backfill status', async () => {
        const r = await readonlyClient.get('/secscan/_backfill_status');
        // 200 if scanner configured, 404 otherwise
        expect([200, 404]).toContain(r.status());
      });
    });
  },
);
