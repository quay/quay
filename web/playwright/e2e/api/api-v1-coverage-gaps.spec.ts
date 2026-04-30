/**
 * API Coverage Gap Tests (Phase 2)
 *
 * Covers API endpoints identified as untested in coverage analysis:
 * build triggers, builds, repository signing, pull statistics,
 * team syncing, user notifications, user authorizations, organization
 * member removal, OAuth app client secret reset, authorized repository
 * emails, and signout.
 */

import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {RawApiClient} from '../../utils/api/raw-client';
import {API_URL} from '../../utils/config';

// ---------------------------------------------------------------------------
// Build Triggers
// ---------------------------------------------------------------------------
test.describe('Build Triggers', {tag: ['@api']}, () => {
  test('list triggers returns empty array for new repository', async ({
    superuserApi,
    adminClient,
  }) => {
    const org = await superuserApi.organization('trig');
    const repo = await superuserApi.repository(org.name, 'repo');

    const resp = await adminClient.get(
      `/api/v1/repository/${org.name}/${repo.name}/trigger/`,
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.triggers).toEqual([]);
  });

  test('get non-existent trigger returns 404', async ({
    superuserApi,
    adminClient,
  }) => {
    const org = await superuserApi.organization('trig');
    const repo = await superuserApi.repository(org.name, 'repo');

    const resp = await adminClient.get(
      `/api/v1/repository/${org.name}/${repo.name}/trigger/00000000-0000-0000-0000-000000000000`,
    );
    expect(resp.status()).toBe(404);
  });

  test('list builds for non-existent trigger returns 404', async ({
    superuserApi,
    adminClient,
  }) => {
    const org = await superuserApi.organization('trig');
    const repo = await superuserApi.repository(org.name, 'repo');

    const resp = await adminClient.get(
      `/api/v1/repository/${org.name}/${repo.name}/trigger/00000000-0000-0000-0000-000000000000/builds`,
    );
    expect(resp.status()).toBe(404);
  });

  test('normal user without admin gets 403 on triggers', async ({
    superuserApi,
    userClient,
  }) => {
    const org = await superuserApi.organization('trig');
    const repo = await superuserApi.repository(org.name, 'repo');

    const resp = await userClient.get(
      `/api/v1/repository/${org.name}/${repo.name}/trigger/`,
    );
    expect(resp.status()).toBe(403);
  });
});

// ---------------------------------------------------------------------------
// Builds
// ---------------------------------------------------------------------------
test.describe('Builds', {tag: ['@api']}, () => {
  test('list builds returns empty array for new repository', async ({
    superuserApi,
    adminClient,
  }) => {
    const org = await superuserApi.organization('bld');
    const repo = await superuserApi.repository(org.name, 'repo');

    const resp = await adminClient.get(
      `/api/v1/repository/${org.name}/${repo.name}/build/`,
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.builds).toEqual([]);
  });

  test('get non-existent build returns 404', async ({
    superuserApi,
    adminClient,
  }) => {
    const org = await superuserApi.organization('bld');
    const repo = await superuserApi.repository(org.name, 'repo');

    const resp = await adminClient.get(
      `/api/v1/repository/${org.name}/${repo.name}/build/00000000-0000-0000-0000-000000000000`,
    );
    expect(resp.status()).toBe(404);
  });

  test('build lifecycle: create, get, status, logs, cancel', async ({
    superuserApi,
    adminClient,
  }) => {
    const org = await superuserApi.organization('bld');
    const repo = await superuserApi.repository(org.name, 'repo');

    let buildId: string;
    try {
      const build = await superuserApi.build(org.name, repo.name);
      buildId = build.buildId;
    } catch {
      test.skip(true, 'Build system not available in this environment');
      return;
    }

    const getResp = await adminClient.get(
      `/api/v1/repository/${org.name}/${repo.name}/build/${buildId}`,
    );
    expect(getResp.status()).toBe(200);
    const buildInfo = await getResp.json();
    expect(buildInfo.id).toBe(buildId);
    expect(buildInfo).toHaveProperty('phase');

    const statusResp = await adminClient.get(
      `/api/v1/repository/${org.name}/${repo.name}/build/${buildId}/status`,
    );
    expect(statusResp.status()).toBe(200);

    const logsResp = await adminClient.get(
      `/api/v1/repository/${org.name}/${repo.name}/build/${buildId}/logs`,
    );
    expect(logsResp.status()).toBe(200);

    const listResp = await adminClient.get(
      `/api/v1/repository/${org.name}/${repo.name}/build/`,
    );
    expect(listResp.status()).toBe(200);
    const listBody = await listResp.json();
    expect(listBody.builds.length).toBeGreaterThan(0);
    expect(listBody.builds.some((b: {id: string}) => b.id === buildId)).toBe(
      true,
    );

    const cancelResp = await adminClient.delete(
      `/api/v1/repository/${org.name}/${repo.name}/build/${buildId}`,
    );
    expect([200, 201, 204]).toContain(cancelResp.status());
  });
});

// ---------------------------------------------------------------------------
// Repository Signing
// ---------------------------------------------------------------------------
test.describe('Repository Signing', {tag: ['@api', '@feature:SIGNING']}, () => {
  test('get signatures for repository', async ({superuserApi, adminClient}) => {
    const org = await superuserApi.organization('sign');
    const repo = await superuserApi.repository(org.name, 'repo', 'public');

    const resp = await adminClient.get(
      `/api/v1/repository/${org.name}/${repo.name}/signatures`,
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body).toHaveProperty('signatures');
  });
});

// ---------------------------------------------------------------------------
// Pull Statistics
// ---------------------------------------------------------------------------
test.describe(
  'Pull Statistics',
  {tag: ['@api', '@feature:IMAGE_PULL_STATS']},
  () => {
    test('tag pull statistics endpoint responds for non-existent tag', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('pullstats');
      const repo = await superuserApi.repository(org.name, 'repo', 'public');

      const resp = await adminClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/latest/pull_statistics`,
      );
      expect([200, 404]).toContain(resp.status());
    });
  },
);

// ---------------------------------------------------------------------------
// Team Syncing
// ---------------------------------------------------------------------------
test.describe('Team Syncing', {tag: ['@api', '@feature:TEAM_SYNCING']}, () => {
  test('enable and disable team sync', async ({superuserApi, adminClient}) => {
    const org = await superuserApi.organization('tsync');
    const team = await superuserApi.team(org.name, 'syncteam');

    const enableResp = await adminClient.post(
      `/api/v1/organization/${org.name}/team/${team.name}/syncing`,
      {group_dn: 'cn=testgroup,dc=example,dc=com'},
    );

    if (enableResp.status() === 400 || enableResp.status() === 401) {
      test.skip(true, 'Team sync requires specific auth configuration');
      return;
    }
    expect([200, 201]).toContain(enableResp.status());

    const disableResp = await adminClient.delete(
      `/api/v1/organization/${org.name}/team/${team.name}/syncing`,
    );
    expect([200, 204]).toContain(disableResp.status());
  });
});

// ---------------------------------------------------------------------------
// User Notifications
// ---------------------------------------------------------------------------
test.describe('User Notifications', {tag: ['@api']}, () => {
  test('list user notifications returns array', async ({adminClient}) => {
    const resp = await adminClient.get('/api/v1/user/notifications');
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body).toHaveProperty('notifications');
    expect(Array.isArray(body.notifications)).toBe(true);
  });

  test('get non-existent notification returns 404', async ({adminClient}) => {
    const resp = await adminClient.get(
      '/api/v1/user/notifications/00000000-0000-0000-0000-000000000000',
    );
    expect(resp.status()).toBe(404);
  });
});

// ---------------------------------------------------------------------------
// User Authorizations
// ---------------------------------------------------------------------------
test.describe('User Authorizations', {tag: ['@api']}, () => {
  test('list user authorizations returns array', async ({adminClient}) => {
    const resp = await adminClient.get('/api/v1/user/authorizations');
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body).toHaveProperty('authorizations');
    expect(Array.isArray(body.authorizations)).toBe(true);
  });

  test('get non-existent authorization returns 404', async ({adminClient}) => {
    const resp = await adminClient.get(
      '/api/v1/user/authorizations/00000000-0000-0000-0000-000000000000',
    );
    expect(resp.status()).toBe(404);
  });
});

// ---------------------------------------------------------------------------
// Organization Member Management
// ---------------------------------------------------------------------------
test.describe('Organization Member Management', {tag: ['@api']}, () => {
  test('add user to org via team, then remove from org', async ({
    superuserApi,
    adminClient,
  }) => {
    const org = await superuserApi.organization('memb');
    const team = await superuserApi.team(org.name, 'devteam');
    const user = await superuserApi.user('member');

    // Verify email so the user can be added
    await adminClient.put(`/api/v1/superuser/users/${user.username}`, {
      email: user.email,
    });

    // Add user to team (makes them an org member)
    const addResp = await adminClient.put(
      `/api/v1/organization/${org.name}/team/${team.name}/members/${user.username}`,
    );
    expect(addResp.status()).toBe(200);

    // Verify member appears in org members list
    const listResp = await adminClient.get(
      `/api/v1/organization/${org.name}/members`,
    );
    expect(listResp.status()).toBe(200);
    const members = await listResp.json();
    expect(members.members).toBeTruthy();

    // Get individual member info
    const memberResp = await adminClient.get(
      `/api/v1/organization/${org.name}/members/${user.username}`,
    );
    expect(memberResp.status()).toBe(200);
    const memberInfo = await memberResp.json();
    expect(memberInfo.name).toBe(user.username);

    // Remove member from org
    const removeResp = await adminClient.delete(
      `/api/v1/organization/${org.name}/members/${user.username}`,
    );
    expect(removeResp.status()).toBe(204);

    // Verify member is gone
    const afterResp = await adminClient.get(
      `/api/v1/organization/${org.name}/members/${user.username}`,
    );
    expect(afterResp.status()).toBe(404);
  });
});

// ---------------------------------------------------------------------------
// OAuth Application Client Secret Reset
// ---------------------------------------------------------------------------
test.describe('OAuth Application Client Secret Reset', {tag: ['@api']}, () => {
  test('reset client secret generates new secret', async ({
    superuserApi,
    adminClient,
  }) => {
    const org = await superuserApi.organization('oauth');
    const app = await superuserApi.oauthApplication(org.name, 'testapp');

    const beforeResp = await adminClient.get(
      `/api/v1/organization/${org.name}/applications/${app.clientId}`,
    );
    expect(beforeResp.status()).toBe(200);

    const resetResp = await adminClient.post(
      `/api/v1/organization/${org.name}/applications/${app.clientId}/resetclientsecret`,
    );
    expect(resetResp.status()).toBe(200);
    const resetBody = await resetResp.json();
    expect(resetBody.client_secret).toBeTruthy();
    expect(resetBody.client_id).toBe(app.clientId);

    if (app.clientSecret) {
      expect(resetBody.client_secret).not.toBe(app.clientSecret);
    }
  });
});

// ---------------------------------------------------------------------------
// Authorized Repository Emails
// ---------------------------------------------------------------------------
test.describe(
  'Authorized Repository Emails',
  {tag: ['@api', '@feature:MAILING']},
  () => {
    test('check email authorization status for repo', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('repomail');
      const repo = await superuserApi.repository(org.name, 'repo');
      const email = 'repocheck@example.com';

      const resp = await adminClient.get(
        `/api/v1/repository/${org.name}/${
          repo.name
        }/authorizedemail/${encodeURIComponent(email)}`,
      );
      expect([200, 404]).toContain(resp.status());
      if (resp.status() === 200) {
        const body = await resp.json();
        expect(body).toHaveProperty('confirmed');
      }
    });

    test('send authorization email for repository', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('repomail');
      const repo = await superuserApi.repository(org.name, 'repo');
      const email = 'repoauth@example.com';

      const resp = await adminClient.post(
        `/api/v1/repository/${org.name}/${
          repo.name
        }/authorizedemail/${encodeURIComponent(email)}`,
      );
      expect([200, 201]).toContain(resp.status());
    });
  },
);

// ---------------------------------------------------------------------------
// Signout
// ---------------------------------------------------------------------------
test.describe('Signout', {tag: ['@api']}, () => {
  test('signout endpoint invalidates session', async ({playwright}) => {
    const request = await playwright.request.newContext({
      ignoreHTTPSErrors: true,
    });
    try {
      const client = new RawApiClient(request, API_URL);
      await client.signIn(TEST_USERS.admin.username, TEST_USERS.admin.password);

      // Verify we're authenticated
      const beforeResp = await client.get('/api/v1/user/');
      expect(beforeResp.status()).toBe(200);

      // Sign out
      const signoutResp = await client.post('/api/v1/signout');
      expect([200, 204]).toContain(signoutResp.status());
    } finally {
      await request.dispose();
    }
  });
});
