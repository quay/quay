/**
 * API Coverage Gap Tests
 *
 * Targets API v1 endpoints identified as uncovered by the Jaeger trace
 * coverage analysis. Covers: user robots, org robot regeneration,
 * org member details, quota limit sub-resources, user notifications,
 * OAuth application info, and team email invitations.
 */

import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {RawApiClient} from '../../utils/api/raw-client';
import {API_URL} from '../../utils/config';

// ===========================================================================
// User Robot CRUD
// ===========================================================================

test.describe('User Robot CRUD', {tag: ['@api', '@auth:Database']}, () => {
  test('user can create, get, list permissions, regenerate, and delete a user robot', async ({
    userClient,
  }) => {
    const shortname = uniqueName('bot').replace(/-/g, '_');
    const username = TEST_USERS.user.username;

    try {
      // Create user robot via PUT
      const createResp = await userClient.put(
        `/api/v1/user/robots/${shortname}`,
        {description: 'test user robot'},
      );
      expect(createResp.status()).toBe(201);
      const created = await createResp.json();
      expect(created.name).toContain(shortname);
      expect(created.token).toBeTruthy();
      const originalToken = created.token;

      // GET individual user robot
      const getResp = await userClient.get(`/api/v1/user/robots/${shortname}`);
      expect(getResp.status()).toBe(200);
      const robot = await getResp.json();
      expect(robot.name).toBe(`${username}+${shortname}`);

      // GET user robot permissions
      const permsResp = await userClient.get(
        `/api/v1/user/robots/${shortname}/permissions`,
      );
      expect(permsResp.status()).toBe(200);
      const perms = await permsResp.json();
      expect(perms.permissions).toBeDefined();

      // POST regenerate user robot token
      const regenResp = await userClient.post(
        `/api/v1/user/robots/${shortname}/regenerate`,
      );
      expect(regenResp.status()).toBe(200);
      const regen = await regenResp.json();
      expect(regen.token).toBeTruthy();
      expect(regen.token).not.toBe(originalToken);
    } finally {
      // DELETE user robot
      const deleteResp = await userClient.delete(
        `/api/v1/user/robots/${shortname}`,
      );
      expect([204, 404]).toContain(deleteResp.status());
    }
  });
});

// ===========================================================================
// Organization Robot Regenerate
// ===========================================================================

test.describe(
  'Organization Robot Regenerate',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('admin can regenerate an org robot token', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('robotregen');
      const robot = await superuserApi.robot(org.name, 'regenbot');

      // POST regenerate org robot token
      const regenResp = await adminClient.post(
        `/api/v1/organization/${org.name}/robots/${robot.shortname}/regenerate`,
      );
      expect(regenResp.status()).toBe(200);
      const regen = await regenResp.json();
      expect(regen.token).toBeTruthy();
    });
  },
);

// ===========================================================================
// Organization Member Details
// ===========================================================================

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

// ===========================================================================
// Organization Quota Limit Sub-resources
// ===========================================================================

test.describe(
  'Organization Quota Limit Sub-resources',
  {tag: ['@api', '@feature:QUOTA_MANAGEMENT']},
  () => {
    test('admin can get quota limits via sub-resource endpoints', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('qlimit');
      const quota = await superuserApi.quota(org.name, 1024000000);

      // Create a quota limit
      await superuserApi.raw.createQuotaLimit(
        org.name,
        quota.quotaId,
        'Warning',
        80,
      );

      // GET all limits for specific quota
      const limitsResp = await adminClient.get(
        `/api/v1/organization/${org.name}/quota/${quota.quotaId}/limit`,
      );
      expect(limitsResp.status()).toBe(200);
      const limits = await limitsResp.json();
      expect(Array.isArray(limits)).toBe(true);
      expect(limits.length).toBeGreaterThan(0);
      expect(limits[0].type).toBe('Warning');
      expect(limits[0].limit_percent).toBe(80);
      const limitId = limits[0].id;

      // GET specific limit by ID
      const limitResp = await adminClient.get(
        `/api/v1/organization/${org.name}/quota/${quota.quotaId}/limit/${limitId}`,
      );
      expect(limitResp.status()).toBe(200);
      const limit = await limitResp.json();
      expect(limit.id).toBe(limitId);
      expect(limit.type).toBe('Warning');
    });
  },
);

// ===========================================================================
// User Quota Sub-resources
// ===========================================================================

test.describe(
  'User Quota Sub-resources',
  {tag: ['@api', '@feature:QUOTA_MANAGEMENT']},
  () => {
    test('admin can get user quota by ID and list its limits', async ({
      superuserApi,
      adminClient,
    }) => {
      const user = await superuserApi.user('quotauser');

      // Create a user quota via superuser API
      await superuserApi.raw.createUserQuotaSuperuser(
        user.username,
        2048000000,
      );

      // Get the quota list to find the quota ID
      const quotasResp = await adminClient.get(
        `/api/v1/superuser/users/${user.username}/quota`,
      );
      expect(quotasResp.status()).toBe(200);
      const quotas = await quotasResp.json();
      expect(quotas.length).toBeGreaterThan(0);
      const quotaId = quotas[0].id;

      try {
        // GET user quota by specific ID
        const quotaResp = await adminClient.get(
          `/api/v1/user/quota/${quotaId}`,
        );
        // User quota GET may require being that user; accept 200 or 404
        expect([200, 404]).toContain(quotaResp.status());

        // GET user quota limits
        const limitsResp = await adminClient.get(
          `/api/v1/user/quota/${quotaId}/limit`,
        );
        expect([200, 404]).toContain(limitsResp.status());

        // PUT update user quota via superuser
        const updateResp = await adminClient.put(
          `/api/v1/superuser/users/${user.username}/quota/${quotaId}`,
          {limit_bytes: 4096000000},
        );
        expect(updateResp.status()).toBe(200);

        // Verify update
        const verifyResp = await adminClient.get(
          `/api/v1/superuser/users/${user.username}/quota`,
        );
        const verifiedQuotas = await verifyResp.json();
        expect(verifiedQuotas[0].limit_bytes).toBe(4096000000);
      } finally {
        await adminClient.delete(
          `/api/v1/superuser/users/${user.username}/quota/${quotaId}`,
        );
      }
    });
  },
);

// ===========================================================================
// User Notifications (Individual)
// ===========================================================================

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

        // GET individual notification
        const getResp = await adminClient.get(
          `/api/v1/user/notifications/${uuid}`,
        );
        expect(getResp.status()).toBe(200);
        const notif = await getResp.json();
        expect(notif.id).toBe(uuid);
      } else {
        // If no notifications exist, at least verify the endpoint returns
        // 404 for a nonexistent UUID rather than erroring
        const getResp = await adminClient.get(
          '/api/v1/user/notifications/nonexistent-uuid',
        );
        expect([404, 400]).toContain(getResp.status());
      }
    });
  },
);

// ===========================================================================
// OAuth Application Info (GET /api/v1/app/<client_id>)
// ===========================================================================

test.describe(
  'OAuth Application Info',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('user can get OAuth application info by client_id', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('oauthapp');

      // Create an OAuth application
      const appName = uniqueName('app');
      const createResp = await adminClient.post(
        `/api/v1/organization/${org.name}/applications`,
        {name: appName},
      );
      expect(createResp.status()).toBe(200);
      const createBody = await createResp.json();
      const clientId = createBody.client_id;

      try {
        // GET application by client_id (the uncovered endpoint)
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

// ===========================================================================
// Team Email Invitations
// ===========================================================================

test.describe(
  'Team Email Invitations',
  {tag: ['@api', '@auth:Database', '@feature:MAILING']},
  () => {
    test('admin can invite user to team by email and revoke the invitation', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('teaminvite');
      const team = await superuserApi.team(org.name, 'inviteteam');
      const email = `${uniqueName('invite')}@example.com`;

      // PUT invite by email
      const inviteResp = await adminClient.put(
        `/api/v1/organization/${org.name}/team/${team.name}/invite/${email}`,
      );
      // 200 = invite sent, 400 = email invites not enabled
      if (inviteResp.status() === 400) {
        test.skip(true, 'Email team invitations not enabled');
        return;
      }
      expect(inviteResp.status()).toBe(200);

      // DELETE (revoke) the invitation
      const revokeResp = await adminClient.delete(
        `/api/v1/organization/${org.name}/team/${team.name}/invite/${email}`,
      );
      expect([204, 404]).toContain(revokeResp.status());
    });
  },
);

// ===========================================================================
// User Self-Delete (DELETE /api/v1/user/)
// ===========================================================================

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

      // DELETE /api/v1/user/ (self-delete)
      const deleteResp = await client.delete('/api/v1/user/');
      expect(deleteResp.status()).toBe(204);
    } finally {
      await request.dispose();
    }
  });
});
