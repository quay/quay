/**
 * Organization & User API Tests
 *
 * Ported from Cypress quay-api-tests to Playwright.
 * Covers: user CRUD, user robots, user self-delete, error descriptions,
 * app tokens, API discovery, global messages, organization CRUD,
 * organization members, organization applications, OAuth app info,
 * user notifications, and superuser user info.
 */

import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {RawApiClient} from '../../utils/api/raw-client';
import {API_URL} from '../../utils/config';

// ============================================================================
// User CRUD
// ============================================================================

test.describe('User CRUD', {tag: ['@api', '@auth:Database']}, () => {
  test('admin can create a new user via superuser API', async ({
    adminClient,
  }) => {
    const username = uniqueName('user');
    const email = `${username}@example.com`;
    try {
      const response = await adminClient.post('/api/v1/superuser/users/', {
        username,
        email,
      });
      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.username).toBe(username);
      expect(body.email).toBe(email);
    } finally {
      await adminClient.delete(`/api/v1/superuser/users/${username}`);
    }
  });

  test('new user can sign in', async ({adminClient, playwright}) => {
    const username = uniqueName('user');
    const email = `${username}@example.com`;
    try {
      // Create user -- the superuser endpoint returns the generated password
      const createResp = await adminClient.post('/api/v1/superuser/users/', {
        username,
        email,
      });
      expect(createResp.status()).toBe(200);
      const createBody = await createResp.json();
      const password = createBody.password;
      expect(password).toBeTruthy();

      // Sign in as the new user using a separate request context
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const newUserClient = new RawApiClient(request, API_URL);

        try {
          await newUserClient.signIn(username, password);
        } catch (e: unknown) {
          // If email verification is required, the user was still created
          // successfully — skip the sign-in portion of this test
          const msg = e instanceof Error ? e.message : String(e);
          if (msg.includes('needsEmailVerification')) {
            return;
          }
          throw e;
        }

        // Verify the session belongs to the new user
        const whoami = await newUserClient.get('/api/v1/user/');
        expect(whoami.status()).toBe(200);
        const whoamiBody = await whoami.json();
        expect(whoamiBody.username).toBe(username);
      } finally {
        await request.dispose();
      }
    } finally {
      await adminClient.delete(`/api/v1/superuser/users/${username}`);
    }
  });

  test('admin can generate encrypted password for a user', async ({
    adminClient,
  }) => {
    // Use the admin user's own session to generate a client key
    const response = await adminClient.post('/api/v1/user/clientkey', {
      password: TEST_USERS.admin.password,
    });
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.key).toBeTruthy();
  });

  test('admin can disable a user', async ({adminClient}) => {
    const username = uniqueName('user');
    const email = `${username}@example.com`;
    try {
      await adminClient.post('/api/v1/superuser/users/', {
        username,
        email,
      });

      const response = await adminClient.put(
        `/api/v1/superuser/users/${username}`,
        {enabled: false},
      );
      expect(response.status()).toBe(200);

      // The PUT response returns stale user data (fetched before the
      // update is applied), so verify the change with a follow-up GET.
      const getResp = await adminClient.get(
        `/api/v1/superuser/users/${username}`,
      );
      expect(getResp.status()).toBe(200);
      const body = await getResp.json();
      expect(body.enabled).toBe(false);
    } finally {
      await adminClient.delete(`/api/v1/superuser/users/${username}`);
    }
  });

  test('admin can delete a user', async ({adminClient}) => {
    const username = uniqueName('user');
    const email = `${username}@example.com`;
    await adminClient.post('/api/v1/superuser/users/', {
      username,
      email,
    });

    const response = await adminClient.delete(
      `/api/v1/superuser/users/${username}`,
    );
    expect(response.status()).toBe(204);
  });
});

// ============================================================================
// User Robot CRUD
// ============================================================================

test.describe('User Robot CRUD', {tag: ['@api', '@auth:Database']}, () => {
  test('user can create, get, list permissions, regenerate, and delete a user robot', async ({
    userClient,
  }) => {
    const shortname = uniqueName('bot').replace(/-/g, '_');
    const username = TEST_USERS.user.username;

    try {
      const createResp = await userClient.put(
        `/api/v1/user/robots/${shortname}`,
        {description: 'test user robot'},
      );
      expect(createResp.status()).toBe(201);
      const created = await createResp.json();
      expect(created.name).toContain(shortname);
      expect(created.token).toBeTruthy();
      const originalToken = created.token;

      const getResp = await userClient.get(`/api/v1/user/robots/${shortname}`);
      expect(getResp.status()).toBe(200);
      const robot = await getResp.json();
      expect(robot.name).toBe(`${username}+${shortname}`);

      const permsResp = await userClient.get(
        `/api/v1/user/robots/${shortname}/permissions`,
      );
      expect(permsResp.status()).toBe(200);
      const perms = await permsResp.json();
      expect(perms.permissions).toBeDefined();

      const regenResp = await userClient.post(
        `/api/v1/user/robots/${shortname}/regenerate`,
      );
      expect(regenResp.status()).toBe(200);
      const regen = await regenResp.json();
      expect(regen.token).toBeTruthy();
      expect(regen.token).not.toBe(originalToken);
    } finally {
      const deleteResp = await userClient.delete(
        `/api/v1/user/robots/${shortname}`,
      );
      expect([204, 404]).toContain(deleteResp.status());
    }
  });
});

// ============================================================================
// User Self-Delete
// ============================================================================

test.describe('User Self-Delete', {tag: ['@api', '@auth:Database']}, () => {
  test('user can delete their own account', async ({
    superuserApi,
    playwright,
  }) => {
    const tempUser = await superuserApi.user('delme');

    const request = await playwright.request.newContext({
      ignoreHTTPSErrors: true,
    });
    try {
      const client = new RawApiClient(request, API_URL);
      await client.signIn(tempUser.username, tempUser.password);

      const deleteResp = await client.delete('/api/v1/user/');
      expect(deleteResp.status()).toBe(204);
    } finally {
      await request.dispose();
    }
  });
});

// ============================================================================
// Error Descriptions
// ============================================================================

test.describe('Error Descriptions', {tag: ['@api', '@auth:Database']}, () => {
  const errorTypes = [
    'invalid_token',
    'expired_token',
    'external_service_timeout',
    'not_found',
    'invalid_response',
    'fresh_login_required',
    'insufficient_scope',
    'invalid_request',
    'exceeds_license',
  ];

  for (const errorType of errorTypes) {
    test(`returns description for error type: ${errorType}`, async ({
      adminClient,
    }) => {
      const response = await adminClient.get(`/api/v1/error/${errorType}`);
      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.title).toBe(errorType);
    });
  }
});

// ============================================================================
// App Tokens CRUD
// ============================================================================

test.describe('App Tokens CRUD', {tag: ['@api', '@auth:Database']}, () => {
  test('user can create, list, get, and revoke an app token', async ({
    adminClient,
  }) => {
    const tokenTitle = uniqueName('apptoken');

    // Create
    const createResp = await adminClient.post('/api/v1/user/apptoken', {
      title: tokenTitle,
    });
    expect(createResp.status()).toBe(200);
    const createBody = await createResp.json();
    expect(createBody.token.title).toBe(tokenTitle);
    const tokenUuid = createBody.token.uuid;

    try {
      // List
      const listResp = await adminClient.get('/api/v1/user/apptoken');
      expect(listResp.status()).toBe(200);
      const listBody = await listResp.json();
      const found = listBody.tokens.find(
        (t: {uuid: string}) => t.uuid === tokenUuid,
      );
      expect(found).toBeTruthy();
      expect(found.title).toBe(tokenTitle);

      // Get by UUID
      const getResp = await adminClient.get(
        `/api/v1/user/apptoken/${tokenUuid}`,
      );
      expect(getResp.status()).toBe(200);
      const getBody = await getResp.json();
      expect(getBody.token.title).toBe(tokenTitle);
    } finally {
      // Best-effort cleanup — don't mask original test failures
      if (tokenUuid) {
        await adminClient.delete(`/api/v1/user/apptoken/${tokenUuid}`);
      }
    }
  });
});

// ============================================================================
// API Discovery
// ============================================================================

test.describe('API Discovery', {tag: ['@api', '@auth:Database']}, () => {
  test('returns API discovery information', async ({adminClient}) => {
    const response = await adminClient.get('/api/v1/discovery');
    expect(response.status()).toBe(200);
    const body = await response.json();
    // The discovery endpoint should return API metadata
    expect(body).toBeTruthy();
  });
});

// ============================================================================
// Global Messages CRUD
// ============================================================================

test.describe('Global Messages CRUD', {tag: ['@api', '@auth:Database']}, () => {
  test('admin can create info, warning, and error global messages', async ({
    adminClient,
  }) => {
    const severities = ['info', 'warning', 'error'] as const;
    const contents: string[] = [];

    try {
      for (const severity of severities) {
        const content = `test global ${severity} message ${uniqueName('msg')}`;
        contents.push(content);
        const response = await adminClient.post('/api/v1/messages', {
          message: {
            media_type: 'text/markdown',
            severity,
            content,
          },
        });
        expect(response.status()).toBe(201);
      }

      // Get all global messages
      const getResp = await adminClient.get('/api/v1/messages');
      expect(getResp.status()).toBe(200);
      const getBody = await getResp.json();
      expect(getBody.messages.length).toBeGreaterThanOrEqual(3);

      // Verify our messages are present
      for (const content of contents) {
        const found = getBody.messages.find(
          (m: {content: string}) => m.content === content,
        );
        expect(found).toBeTruthy();
      }
    } finally {
      // Delete only the messages created by this test
      const allResp = await adminClient.get('/api/v1/messages');
      if (allResp.status() === 200) {
        const allBody = await allResp.json();
        for (const msg of allBody.messages) {
          if (contents.includes(msg.content)) {
            const deleteResp = await adminClient.delete(
              `/api/v1/message/${msg.uuid}`,
            );
            expect([204, 404]).toContain(deleteResp.status());
          }
        }
      }
    }
  });

  test('admin can create and delete a single global message', async ({
    adminClient,
  }) => {
    const content = `test message ${uniqueName('msg')}`;
    let createdUuid: string | undefined;
    try {
      const createResp = await adminClient.post('/api/v1/messages', {
        message: {
          media_type: 'text/markdown',
          severity: 'info',
          content,
        },
      });
      expect(createResp.status()).toBe(201);

      // Retrieve messages and find the one we just created by content
      const getResp = await adminClient.get('/api/v1/messages');
      expect(getResp.status()).toBe(200);
      const getBody = await getResp.json();
      const ourMessage = getBody.messages.find(
        (m: {content: string}) => m.content === content,
      );
      expect(ourMessage).toBeTruthy();
      createdUuid = ourMessage.uuid;

      // Delete the specific message we created
      const deleteResp = await adminClient.delete(
        `/api/v1/message/${createdUuid}`,
      );
      expect(deleteResp.status()).toBe(204);
    } finally {
      // Best-effort cleanup — don't mask original test failures
      try {
        if (createdUuid) {
          await adminClient.delete(`/api/v1/message/${createdUuid}`);
        } else {
          // UUID was never captured — try to find and clean up by content
          const list = await adminClient.get('/api/v1/messages');
          if (list.status() === 200) {
            const listBody = await list.json();
            const leaked = listBody.messages?.find(
              (m: {content: string}) => m.content === content,
            );
            if (leaked) {
              await adminClient.delete(`/api/v1/message/${leaked.uuid}`);
            }
          }
        }
      } catch {
        // Ignore cleanup errors
      }
    }
  });
});

// ============================================================================
// Organization CRUD
// ============================================================================

test.describe('Organization CRUD', {tag: ['@api', '@auth:Database']}, () => {
  test('admin can create a new organization', async ({adminClient}) => {
    const orgName = uniqueName('org');
    const email = `${orgName}@example.com`;
    try {
      const response = await adminClient.post('/api/v1/organization/', {
        name: orgName,
        email,
      });
      expect(response.status()).toBe(201);
    } finally {
      await adminClient.delete(`/api/v1/organization/${orgName}`);
    }
  });

  test('get non-existing organization returns 404', async ({adminClient}) => {
    const response = await adminClient.get(
      '/api/v1/organization/quaynotexistingorg_xyzzy_404',
    );
    expect(response.status()).toBe(404);
  });

  test('get existing organization returns 200', async ({adminClient}) => {
    const orgName = uniqueName('org');
    try {
      await adminClient.post('/api/v1/organization/', {
        name: orgName,
        email: `${orgName}@example.com`,
      });

      const response = await adminClient.get(`/api/v1/organization/${orgName}`);
      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.name).toBe(orgName);
    } finally {
      await adminClient.delete(`/api/v1/organization/${orgName}`);
    }
  });

  test('admin can update an existing organization', async ({adminClient}) => {
    const orgName = uniqueName('org');
    const email = `${orgName}@example.com`;
    const newEmail = `updated-${email}`;
    try {
      await adminClient.post('/api/v1/organization/', {
        name: orgName,
        email,
      });

      const response = await adminClient.put(
        `/api/v1/organization/${orgName}`,
        {
          invoice_email: true,
          email: newEmail,
        },
      );
      expect(response.status()).toBe(200);
    } finally {
      await adminClient.delete(`/api/v1/organization/${orgName}`);
    }
  });

  test('admin can delete an organization', async ({adminClient}) => {
    const orgName = uniqueName('org');
    await adminClient.post('/api/v1/organization/', {
      name: orgName,
      email: `${orgName}@example.com`,
    });

    const response = await adminClient.delete(
      `/api/v1/organization/${orgName}`,
    );
    expect(response.status()).toBe(204);
  });
});

// ============================================================================
// Organization Member Details
// ============================================================================

test.describe(
  'Organization Member Details',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('admin can get individual org member info', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('memberinfo');

      // The creating user (admin) is automatically in the 'owners' team
      const resp = await adminClient.get(
        `/api/v1/organization/${org.name}/members/${TEST_USERS.admin.username}`,
      );
      expect(resp.status()).toBe(200);
      const member = await resp.json();
      expect(member.name).toBe(TEST_USERS.admin.username);
      expect(member.kind).toBe('user');
      expect(member.teams).toBeDefined();
    });
  },
);

// ============================================================================
// Organization Applications CRUD
// ============================================================================

test.describe(
  'Organization Applications CRUD',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('admin can create, get, update, and delete an org application', async ({
      adminClient,
    }) => {
      const orgName = uniqueName('org');
      let clientId = '';

      try {
        // Create org first
        await adminClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        // Create application
        const appName = uniqueName('app');
        const createResp = await adminClient.post(
          `/api/v1/organization/${orgName}/applications`,
          {name: appName},
        );
        expect(createResp.status()).toBe(200);
        const createBody = await createResp.json();
        expect(createBody.name).toBe(appName);
        expect(createBody.client_id).toBeTruthy();
        clientId = createBody.client_id;
        const clientSecret = createBody.client_secret;

        // Get application
        const getResp = await adminClient.get(
          `/api/v1/organization/${orgName}/applications/${clientId}`,
        );
        expect(getResp.status()).toBe(200);
        const getBody = await getResp.json();
        expect(getBody.name).toBe(appName);

        // Update application
        const updatedName = `${appName}-updated`;
        const updateResp = await adminClient.put(
          `/api/v1/organization/${orgName}/applications/${clientId}`,
          {
            name: updatedName,
            description: 'updated app description',
            application_uri: 'https://quay.io',
            client_id: clientId,
            client_secret: clientSecret,
            redirect_uri: 'https://quay.io',
            avatar_email: 'apptest@redhat.com',
          },
        );
        expect(updateResp.status()).toBe(200);
        const updateBody = await updateResp.json();
        expect(updateBody.name).toBe(updatedName);

        // Delete application
        const deleteResp = await adminClient.delete(
          `/api/v1/organization/${orgName}/applications/${clientId}`,
        );
        expect(deleteResp.status()).toBe(204);
      } finally {
        await adminClient.delete(`/api/v1/organization/${orgName}`);
      }
    });
  },
);

// ============================================================================
// OAuth Application Info
// ============================================================================

test.describe(
  'OAuth Application Info',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('user can get OAuth application info by client_id', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('oauthapp');

      const appName = uniqueName('app');
      const createResp = await adminClient.post(
        `/api/v1/organization/${org.name}/applications`,
        {name: appName},
      );
      expect(createResp.status()).toBe(200);
      const createBody = await createResp.json();
      const clientId = createBody.client_id;

      try {
        const getResp = await adminClient.get(`/api/v1/app/${clientId}`);
        expect(getResp.status()).toBe(200);
        const appInfo = await getResp.json();
        expect(appInfo.name).toBe(appName);
      } finally {
        await adminClient.delete(
          `/api/v1/organization/${org.name}/applications/${clientId}`,
        );
      }
    });
  },
);

// ============================================================================
// User Notifications
// ============================================================================

test.describe(
  'User Notifications Individual',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('user can get an individual notification by UUID', async ({
      adminClient,
    }) => {
      const listResp = await adminClient.get('/api/v1/user/notifications');
      expect(listResp.status()).toBe(200);
      const notifications = await listResp.json();

      if (
        notifications.notifications &&
        notifications.notifications.length > 0
      ) {
        const uuid = notifications.notifications[0].id;

        const getResp = await adminClient.get(
          `/api/v1/user/notifications/${uuid}`,
        );
        expect(getResp.status()).toBe(200);
        const notif = await getResp.json();
        expect(notif.id).toBe(uuid);
      } else {
        const getResp = await adminClient.get(
          '/api/v1/user/notifications/nonexistent-uuid',
        );
        expect([404, 400]).toContain(getResp.status());
      }
    });
  },
);

// ============================================================================
// Superuser User Info
// ============================================================================

test.describe('Superuser User Info', {tag: ['@api', '@auth:Database']}, () => {
  test('admin can list superuser users', async ({adminClient}) => {
    const response = await adminClient.get('/api/v1/superuser/users/');
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.users).toBeTruthy();
    expect(body.users.length).toBeGreaterThanOrEqual(1);

    // Verify admin user is in the list and is a superuser
    const adminUser = body.users.find(
      (u: {username: string}) => u.username === TEST_USERS.admin.username,
    );
    expect(adminUser).toBeTruthy();
    expect(adminUser.super_user).toBe(true);
  });

  test('normal user gets 403 on superuser users endpoint', async ({
    userClient,
  }) => {
    const response = await userClient.get('/api/v1/superuser/users/');
    expect(response.status()).toBe(403);
  });

  test('admin can get current authenticated user info', async ({
    adminClient,
  }) => {
    const response = await adminClient.get('/api/v1/user/');
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.username).toBe(TEST_USERS.admin.username);
    expect(body.super_user).toBe(true);
  });

  test('admin can get info for a specified user', async ({adminClient}) => {
    const response = await adminClient.get(
      `/api/v1/users/${TEST_USERS.admin.username}`,
    );
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.username).toBe(TEST_USERS.admin.username);
  });
});
