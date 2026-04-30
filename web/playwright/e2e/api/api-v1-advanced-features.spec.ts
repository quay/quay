/**
 * Advanced Features API Tests
 *
 * Ported from Cypress quay_api_testing_all.cy.js and unique tests from
 * quay_api_testing_all_new_ui.cy.js. Covers: repository mirroring,
 * proxy cache, quotas, autoprune policies, logs, health endpoints,
 * service keys, organization mirror, registry capabilities, repository
 * signing, pull statistics, and team syncing.
 */

import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {RawApiClient} from '../../utils/api/raw-client';
import {API_URL} from '../../utils/config';

// ---------------------------------------------------------------------------
// Repository Mirror
// ---------------------------------------------------------------------------
test.describe(
  'Repository Mirror',
  {tag: ['@api', '@feature:REPO_MIRROR']},
  () => {
    test('CRUD mirror config, sync-now, sync-cancel', async ({
      superuserApi,
    }) => {
      const org = await superuserApi.organization('mirror');
      const repo = await superuserApi.repository(org.name, 'mirrorrepo');
      const robot = await superuserApi.robot(org.name, 'mirrorbot');

      // Set repo state to MIRROR
      await superuserApi.setMirrorState(org.name, repo.name);

      const client = superuserApi.raw;

      // Create mirror config
      await client.createMirrorConfig(org.name, repo.name, {
        external_reference: 'registry.example.io/library/alpine',
        sync_interval: 3600,
        sync_start_date: '2023-07-10T06:24:00Z',
        root_rule: {
          rule_kind: 'tag_glob_csv',
          rule_value: ['latest'],
        },
        robot_username: robot.fullName,
        is_enabled: false,
        external_registry_username: null,
        external_registry_password: null,
        external_registry_config: {
          verify_tls: true,
          unsigned_images: false,
          proxy: {
            http_proxy: null,
            https_proxy: null,
            no_proxy: null,
          },
        },
      });

      // Modify mirror config
      await client.updateMirrorConfig(org.name, repo.name, {
        sync_interval: 7200,
      });

      // Get mirror config and verify update
      const mirrorCfg = await client.getMirrorConfig(org.name, repo.name);
      expect(mirrorCfg).not.toBeNull();
      expect(mirrorCfg!.sync_interval).toBe(7200);

      // Sync-now (204 expected)
      await client.triggerMirrorSync(org.name, repo.name);

      // Sync-cancel (204 expected)
      await client.cancelMirrorSync(org.name, repo.name);
    });
  },
);

// ---------------------------------------------------------------------------
// Proxy Cache
// ---------------------------------------------------------------------------
test.describe('Proxy Cache', {tag: ['@api', '@feature:PROXY_CACHE']}, () => {
  test('validate, create, get, and delete proxy cache config', async ({
    superuserApi,
    adminClient,
  }) => {
    const org = await superuserApi.organization('proxycache');

    // Validate proxy cache config
    const validateResp = await adminClient.post(
      `/api/v1/organization/${org.name}/validateproxycache`,
      {
        upstream_registry: 'quay.io',
      },
    );
    // 202 means validation was accepted; 400 means the upstream registry
    // was unreachable (expected in isolated CI environments).
    expect([202, 400]).toContain(validateResp.status());

    // Create proxy cache config
    const client = superuserApi.raw;
    await client.createProxyCacheConfig(org.name, {
      upstream_registry: 'quay.io',
      expiration_s: 86400,
      insecure: false,
      upstream_registry_username: 'dummyuser',
      upstream_registry_password: 'dummypassword',
    });

    // Get proxy cache config
    const proxyCfg = await client.getProxyCacheConfig(org.name);
    expect(proxyCfg).not.toBeNull();
    expect(proxyCfg!.upstream_registry).toContain('quay.io');

    // Delete proxy cache config -- deleteProxyCacheConfig already
    // verifies the DELETE request succeeded (throws on failure)
    await client.deleteProxyCacheConfig(org.name);
  });
});

// ---------------------------------------------------------------------------
// Organization Quotas
// ---------------------------------------------------------------------------
test.describe(
  'Organization Quotas',
  {tag: ['@api', '@feature:QUOTA_MANAGEMENT']},
  () => {
    test('CRUD organization quota', async ({superuserApi}) => {
      const org = await superuserApi.organization('quota');
      const quota = await superuserApi.quota(org.name, 1024000000);

      // Get quota
      const quotas = await superuserApi.raw.getOrganizationQuota(org.name);
      expect(quotas.length).toBeGreaterThan(0);
      expect(quotas[0].limit_bytes).toBe(1024000000);

      // Change quota
      await superuserApi.raw.updateOrganizationQuota(
        org.name,
        quota.quotaId,
        8024000000,
      );

      // Verify change
      const updated = await superuserApi.raw.getOrganizationQuota(org.name);
      expect(updated[0].limit_bytes).toBe(8024000000);
    });

    test('CRUD organization quota limits', async ({superuserApi}) => {
      const org = await superuserApi.organization('quotalim');
      const quota = await superuserApi.quota(org.name, 1024000000);

      const client = superuserApi.raw;

      // Create quota limit
      await client.createQuotaLimit(org.name, quota.quotaId, 'Reject', 98);

      // Get quota to verify limit
      const quotas = await client.getOrganizationQuota(org.name);
      expect(quotas[0].limits.length).toBeGreaterThan(0);
      expect(quotas[0].limits[0].type).toBe('Reject');
      expect(quotas[0].limits[0].limit_percent).toBe(98);

      // Delete the quota limit
      const limitId = quotas[0].limits[0].id;
      await client.deleteQuotaLimit(org.name, quota.quotaId, limitId);

      // Verify deletion
      const afterDelete = await client.getOrganizationQuota(org.name);
      expect(afterDelete[0].limits.length).toBe(0);
    });

    test('superuser CRUD organization quota', async ({
      superuserApi,
      adminClient,
    }) => {
      // Skip when SUPER_USERS feature is disabled (403 from superuser endpoints)
      const probe = await adminClient.get('/api/v1/superuser/registrystatus');
      if (probe.status() === 403 || probe.status() === 404) {
        test.skip();
        return;
      }

      const org = await superuserApi.organization('suquota');

      // Create quota via superuser API
      const createResp = await adminClient.post(
        `/api/v1/superuser/organization/${org.name}/quota`,
        {limit_bytes: 9024000000},
      );
      expect(createResp.status()).toBe(201);

      // Get the quota to find its ID
      const listResp = await adminClient.get(
        `/api/v1/organization/${org.name}/quota`,
      );
      const quotas = await listResp.json();
      const quotaId = quotas[0].id;

      // Change quota via superuser API
      const changeResp = await adminClient.put(
        `/api/v1/superuser/organization/${org.name}/quota/${quotaId}`,
        {limit_bytes: 10024000000},
      );
      expect(changeResp.status()).toBe(200);
      const changed = await changeResp.json();
      expect(changed.limit_bytes).toBe(10024000000);

      // Delete quota via superuser API
      const deleteResp = await adminClient.delete(
        `/api/v1/superuser/organization/${org.name}/quota/${quotaId}`,
      );
      expect(deleteResp.status()).toBe(204);
    });

    test('admin can get quota limits via sub-resource endpoints', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('qlimit');
      const quota = await superuserApi.quota(org.name, 1024000000);

      await superuserApi.raw.createQuotaLimit(
        org.name,
        quota.quotaId,
        'Warning',
        80,
      );

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

// ---------------------------------------------------------------------------
// User Quotas
// ---------------------------------------------------------------------------
test.describe(
  'User Quotas',
  {tag: ['@api', '@feature:QUOTA_MANAGEMENT']},
  () => {
    test('admin can get user quota by ID and list its limits', async ({
      superuserApi,
      adminClient,
      playwright,
    }) => {
      const user = await superuserApi.user('quotauser');

      await superuserApi.raw.createUserQuotaSuperuser(
        user.username,
        2048000000,
      );

      const quotasResp = await adminClient.get(
        `/api/v1/superuser/users/${user.username}/quota`,
      );
      expect(quotasResp.status()).toBe(200);
      const quotas = await quotasResp.json();
      const quota = quotas.find(
        (q: {limit_bytes: number}) => q.limit_bytes === 2048000000,
      );
      expect(quota).toBeTruthy();
      const quotaId = quota.id;

      // Verify the user's email via superuser API (auto_verify=True on the backend)
      const verifyEmailResp = await adminClient.put(
        `/api/v1/superuser/users/${user.username}`,
        {email: user.email},
      );
      expect(verifyEmailResp.status()).toBe(200);

      // Sign in as the created user for user-scoped quota endpoints
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const userClient = new RawApiClient(request, API_URL);
        await userClient.signIn(user.username, user.password);

        const quotaResp = await userClient.get(`/api/v1/user/quota/${quotaId}`);
        expect(quotaResp.status()).toBe(200);

        const limitsResp = await userClient.get(
          `/api/v1/user/quota/${quotaId}/limit`,
        );
        expect(limitsResp.status()).toBe(200);
      } finally {
        await request.dispose();
      }

      // Superuser update and verify
      try {
        const updateResp = await adminClient.put(
          `/api/v1/superuser/users/${user.username}/quota/${quotaId}`,
          {limit_bytes: 4096000000},
        );
        expect(updateResp.status()).toBe(200);

        const verifyResp = await adminClient.get(
          `/api/v1/superuser/users/${user.username}/quota`,
        );
        const verifiedQuotas = await verifyResp.json();
        const updated = verifiedQuotas.find(
          (q: {id: number}) => q.id === quotaId,
        );
        expect(updated.limit_bytes).toBe(4096000000);
      } finally {
        await adminClient.delete(
          `/api/v1/superuser/users/${user.username}/quota/${quotaId}`,
        );
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Autoprune - Organization
// ---------------------------------------------------------------------------
test.describe(
  'Autoprune - Organization',
  {tag: ['@api', '@feature:AUTO_PRUNE']},
  () => {
    test('invalid payload returns 400', async ({superuserApi, adminClient}) => {
      const org = await superuserApi.organization('aporg');

      const resp = await adminClient.post(
        `/api/v1/organization/${org.name}/autoprunepolicy/`,
        {method: 'number_of_times', value: 6},
      );
      expect(resp.status()).toBe(400);
      const body = await resp.json();
      expect(body.detail).toBe('Invalid method provided');
    });

    test('CRUD autoprune policy for organization', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('aporg');

      // Create
      const createResp = await adminClient.post(
        `/api/v1/organization/${org.name}/autoprunepolicy/`,
        {method: 'number_of_tags', value: 6},
      );
      expect(createResp.status()).toBe(201);
      const created = await createResp.json();
      const uuid = created.uuid;
      expect(uuid).toBeTruthy();

      // Get all
      const listResp = await adminClient.get(
        `/api/v1/organization/${org.name}/autoprunepolicy/`,
      );
      expect(listResp.status()).toBe(200);
      const policies = await listResp.json();
      expect(policies.policies[0].uuid).toContain(uuid);

      // Get by UUID
      const getResp = await adminClient.get(
        `/api/v1/organization/${org.name}/autoprunepolicy/${uuid}`,
      );
      expect(getResp.status()).toBe(200);
      const policy = await getResp.json();
      expect(policy.uuid).toContain(uuid);

      // Update
      const updateResp = await adminClient.put(
        `/api/v1/organization/${org.name}/autoprunepolicy/${uuid}`,
        {method: 'creation_date', value: '7d'},
      );
      expect(updateResp.status()).toBe(204);

      // Delete
      const deleteResp = await adminClient.delete(
        `/api/v1/organization/${org.name}/autoprunepolicy/${uuid}`,
      );
      expect(deleteResp.status()).toBe(200);
    });
  },
);

// ---------------------------------------------------------------------------
// Autoprune - Repository
// ---------------------------------------------------------------------------
test.describe(
  'Autoprune - Repository',
  {tag: ['@api', '@feature:AUTO_PRUNE']},
  () => {
    test('invalid payload returns 400', async ({superuserApi, adminClient}) => {
      const org = await superuserApi.organization('aprepo');
      const repo = await superuserApi.repository(org.name, 'aprepo');

      const resp = await adminClient.post(
        `/api/v1/repository/${org.name}/${repo.name}/autoprunepolicy/`,
        {method: 'number_of_times', value: 10},
      );
      expect(resp.status()).toBe(400);
      const body = await resp.json();
      expect(body.detail).toBe('Invalid method provided');
    });

    test('CRUD autoprune policy for repository', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('aprepo');
      const repo = await superuserApi.repository(org.name, 'aprepo');
      const repo2 = await superuserApi.repository(org.name, 'aprepo2');

      // Create on first repo
      const createResp = await adminClient.post(
        `/api/v1/repository/${org.name}/${repo.name}/autoprunepolicy/`,
        {method: 'number_of_tags', value: 10},
      );
      expect(createResp.status()).toBe(201);
      const created = await createResp.json();
      const uuid = created.uuid;
      expect(uuid).toBeTruthy();

      // Create on second repo (validates PROJQUAY-6782)
      const create2Resp = await adminClient.post(
        `/api/v1/repository/${org.name}/${repo2.name}/autoprunepolicy/`,
        {method: 'number_of_tags', value: 8},
      );
      expect(create2Resp.status()).toBe(201);

      // Update
      const updateResp = await adminClient.put(
        `/api/v1/repository/${org.name}/${repo.name}/autoprunepolicy/${uuid}`,
        {method: 'number_of_tags', uuid, value: 30},
      );
      expect(updateResp.status()).toBe(204);

      // Get
      const getResp = await adminClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/autoprunepolicy/${uuid}`,
      );
      expect(getResp.status()).toBe(200);
      const fetched = await getResp.json();
      expect(fetched.uuid).toContain(uuid);

      // Delete
      const deleteResp = await adminClient.delete(
        `/api/v1/repository/${org.name}/${repo.name}/autoprunepolicy/${uuid}`,
      );
      expect(deleteResp.status()).toBe(200);
    });
  },
);

// ---------------------------------------------------------------------------
// Autoprune - User Namespace
// ---------------------------------------------------------------------------
test.describe(
  'Autoprune - User Namespace',
  {tag: ['@api', '@feature:AUTO_PRUNE']},
  () => {
    test('invalid payload returns 400', async ({adminClient}) => {
      const resp = await adminClient.post('/api/v1/user/autoprunepolicy/', {
        method: 'number_of_times',
        value: 6,
      });
      expect(resp.status()).toBe(400);
      const body = await resp.json();
      expect(body.detail).toBe('Invalid method provided');
    });

    test('CRUD autoprune policy for user namespace', async ({adminClient}) => {
      // Create
      const createResp = await adminClient.post(
        '/api/v1/user/autoprunepolicy/',
        {method: 'number_of_tags', value: 6},
      );
      expect(createResp.status()).toBe(201);
      const created = await createResp.json();
      const uuid = created.uuid;
      expect(uuid).toBeTruthy();

      try {
        // Get all
        const listResp = await adminClient.get('/api/v1/user/autoprunepolicy/');
        expect(listResp.status()).toBe(200);
        const policies = await listResp.json();
        expect(
          policies.policies.some((p: {uuid: string}) => p.uuid === uuid),
        ).toBe(true);

        // Get by UUID
        const getResp = await adminClient.get(
          `/api/v1/user/autoprunepolicy/${uuid}`,
        );
        expect(getResp.status()).toBe(200);
        const policy = await getResp.json();
        expect(policy.uuid).toContain(uuid);

        // Update
        const updateResp = await adminClient.put(
          `/api/v1/user/autoprunepolicy/${uuid}`,
          {method: 'creation_date', value: '7d'},
        );
        expect(updateResp.status()).toBe(204);
      } finally {
        // Delete
        await adminClient.delete(`/api/v1/user/autoprunepolicy/${uuid}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Autoprune - User Namespace Repository
// ---------------------------------------------------------------------------
test.describe(
  'Autoprune - User Namespace Repository',
  {tag: ['@api', '@feature:AUTO_PRUNE']},
  () => {
    test('invalid payload returns 400', async ({superuserApi, adminClient}) => {
      const repo = await superuserApi.repository(
        TEST_USERS.admin.username,
        'apuserrepo',
      );

      const resp = await adminClient.post(
        `/api/v1/repository/${TEST_USERS.admin.username}/${repo.name}/autoprunepolicy/`,
        {method: 'number_of_times', value: 10},
      );
      expect(resp.status()).toBe(400);
      const body = await resp.json();
      expect(body.detail).toBe('Invalid method provided');
    });

    test('CRUD autoprune policy for user namespace repo', async ({
      superuserApi,
      adminClient,
    }) => {
      const repo = await superuserApi.repository(
        TEST_USERS.admin.username,
        'apuserrepo',
      );

      // Create
      const createResp = await adminClient.post(
        `/api/v1/repository/${TEST_USERS.admin.username}/${repo.name}/autoprunepolicy/`,
        {method: 'number_of_tags', value: 6},
      );
      expect(createResp.status()).toBe(201);
      const created = await createResp.json();
      const uuid = created.uuid;
      expect(uuid).toBeTruthy();

      // Update
      const updateResp = await adminClient.put(
        `/api/v1/repository/${TEST_USERS.admin.username}/${repo.name}/autoprunepolicy/${uuid}`,
        {method: 'number_of_tags', uuid, value: 30},
      );
      expect(updateResp.status()).toBe(204);

      // Get
      const getResp = await adminClient.get(
        `/api/v1/repository/${TEST_USERS.admin.username}/${repo.name}/autoprunepolicy/${uuid}`,
      );
      expect(getResp.status()).toBe(200);
      const fetched = await getResp.json();
      expect(fetched.uuid).toContain(uuid);

      // Delete
      const deleteResp = await adminClient.delete(
        `/api/v1/repository/${TEST_USERS.admin.username}/${repo.name}/autoprunepolicy/${uuid}`,
      );
      expect(deleteResp.status()).toBe(200);
    });
  },
);

// ---------------------------------------------------------------------------
// Logs
// ---------------------------------------------------------------------------
test.describe('Logs', {tag: ['@api']}, () => {
  test('get repository logs', async ({superuserApi, adminClient}) => {
    const org = await superuserApi.organization('logs');
    const repo = await superuserApi.repository(org.name, 'logrepo');

    const resp = await adminClient.get(
      `/api/v1/repository/${org.name}/${repo.name}/logs`,
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.logs).toBeDefined();
  });

  test('get organization logs', async ({superuserApi, adminClient}) => {
    const org = await superuserApi.organization('logs');

    const resp = await adminClient.get(`/api/v1/organization/${org.name}/logs`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.logs).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Security Scanner
// ---------------------------------------------------------------------------
test.describe(
  'Security Scanner',
  {tag: ['@api', '@feature:SECURITY_SCANNER']},
  () => {
    test('check backfill status', async ({adminClient}) => {
      const resp = await adminClient.get('/secscan/_backfill_status');
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body.backfill_percent).toBeDefined();
    });
  },
);

// ---------------------------------------------------------------------------
// Registry Status & Size
// ---------------------------------------------------------------------------
test.describe('Registry Status & Size', {tag: ['@api']}, () => {
  test('check superuser registry status', async ({adminClient}) => {
    const resp = await adminClient.get('/api/v1/superuser/registrystatus');
    // Skip when SUPER_USERS feature is disabled
    if (resp.status() === 403 || resp.status() === 404) {
      test.skip();
      return;
    }
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe('ready');
  });

  test('calculate and get registry size', async ({adminClient}) => {
    // Skip when SUPER_USERS feature is disabled
    const probe = await adminClient.get('/api/v1/superuser/registrystatus');
    if (probe.status() === 403 || probe.status() === 404) {
      test.skip();
      return;
    }

    // Trigger calculation (201 = created, 202 = already queued)
    const calcResp = await adminClient.post('/api/v1/superuser/registrysize/');
    expect([201, 202]).toContain(calcResp.status());

    // Poll until the calculation completes and size_bytes is a valid number.
    // Do NOT require size_bytes > 0: CI only creates repos/orgs via API and
    // never pushes image blobs, so the registry legitimately has 0 bytes.
    // Asserting > 0 caused guaranteed 180 s timeouts on every clean CI run.
    await expect
      .poll(
        async () => {
          const sizeResp = await adminClient.get(
            '/api/v1/superuser/registrysize/',
          );
          if (sizeResp.status() !== 200) return null;
          const body = await sizeResp.json();
          const bytes = body.size_bytes;
          // Return the value only once the backend has finished calculating
          // (size_bytes will be null/undefined until the async job completes).
          return typeof bytes === 'number' ? bytes : null;
        },
        {
          message: 'Waiting for registry size calculation to complete',
          timeout: 180_000,
          intervals: [5_000, 10_000, 15_000],
        },
      )
      .toBeGreaterThanOrEqual(0);
  });
});

// ---------------------------------------------------------------------------
// Health Endpoints
// ---------------------------------------------------------------------------
test.describe('Health Endpoints', {tag: ['@api']}, () => {
  test('health/instance returns healthy services', async ({adminClient}) => {
    const resp = await adminClient.get('/health/instance');
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status_code).toBe(200);
    expect(body.data.services.auth).toBe(true);
    expect(body.data.services.database).toBe(true);
    expect(body.data.services.disk_space).toBe(true);
    expect(body.data.services.registry_gunicorn).toBe(true);
    expect(body.data.services.service_key).toBe(true);
    expect(body.data.services.web_gunicorn).toBe(true);
  });

  test('health/endtoend returns healthy services', async ({adminClient}) => {
    const resp = await adminClient.get('/health/endtoend');
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status_code).toBe(200);
    expect(body.data.services.auth).toBe(true);
    expect(body.data.services.database).toBe(true);
    expect(body.data.services.redis).toBe(true);
    expect(body.data.services.storage).toBe(true);
  });

  test('health/warning returns healthy disk_space_warning', async ({
    adminClient,
  }) => {
    const resp = await adminClient.get('/health/warning');
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status_code).toBe(200);
    expect(body.data.services.disk_space_warning).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Config Dump
// ---------------------------------------------------------------------------
test.describe('Config Dump', {tag: ['@api']}, () => {
  test('superuser can get config dump', async ({adminClient}) => {
    const resp = await adminClient.get('/api/v1/superuser/config');
    // Skip if endpoint not supported (pre-3.15) or feature not enabled
    // (FEATURE_SUPERUSER_CONFIGDUMP disabled returns 403)
    if (resp.status() === 404 || resp.status() === 403) {
      test.skip();
      return;
    }
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.config).toBeDefined();
    expect(body.warning).toBeDefined();
    expect(body.env).toBeDefined();
    expect(body.schema).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// App Tokens Superuser
// ---------------------------------------------------------------------------
test.describe('App Tokens Superuser', {tag: ['@api']}, () => {
  test('superuser can list app tokens', async ({adminClient}) => {
    const resp = await adminClient.get('/api/v1/superuser/apptokens');
    // Skip if endpoint not supported (pre-3.16) or SUPER_USERS disabled
    if (resp.status() === 404 || resp.status() === 403) {
      test.skip();
      return;
    }
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.tokens).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Service Keys
// ---------------------------------------------------------------------------
test.describe('Service Keys', {tag: ['@api']}, () => {
  test('CRUD service key', async ({superuserApi, adminClient}) => {
    // Skip when SUPER_USERS feature is disabled
    const probe = await adminClient.get('/api/v1/superuser/keys');
    if (probe.status() === 403 || probe.status() === 404) {
      test.skip();
      return;
    }

    const key = await superuserApi.serviceKey('quay', 'api_test_key');

    // List all service keys
    const listResp = await adminClient.get('/api/v1/superuser/keys');
    expect(listResp.status()).toBe(200);
    const listBody = await listResp.json();
    expect(listBody.keys).toBeDefined();
    expect(listBody.keys.length).toBeGreaterThan(0);

    // Update the service key
    const updateResp = await adminClient.put(
      `/api/v1/superuser/keys/${key.kid}`,
      {
        name: 'api_test_updated',
        metadata: {created_by: 'Playwright Automation'},
      },
    );
    expect(updateResp.status()).toBe(200);
    const updated = await updateResp.json();
    expect(updated.name).toBe('api_test_updated');

    // Get the service key
    const getResp = await adminClient.get(`/api/v1/superuser/keys/${key.kid}`);
    expect(getResp.status()).toBe(200);
    const fetched = await getResp.json();
    expect(fetched.name).toBe('api_test_updated');
    expect(fetched.metadata.created_by).toBe('Playwright Automation');

    // Deletion handled by superuserApi cleanup
  });
});

// ---------------------------------------------------------------------------
// Organization Mirror (from new_ui - /api/v1/organization/{org}/mirror)
// ---------------------------------------------------------------------------
test.describe(
  'Organization Mirror',
  {tag: ['@api', '@feature:ORG_MIRROR']},
  () => {
    test('CRUD org mirror config with sync and verify', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('orgmir');
      const robot = await superuserApi.robot(org.name, 'mirbot');

      const client = superuserApi.raw;

      // Create org mirror config
      await client.createOrgMirrorConfig(org.name, {
        external_registry_type: 'quay',
        external_registry_url: 'https://quay.io',
        external_namespace: 'projectquay',
        robot_username: robot.fullName,
        visibility: 'private',
        sync_interval: 86400,
        sync_start_date: '2026-03-03T08:00:00Z',
        is_enabled: false,
        external_registry_config: {
          verify_tls: true,
          proxy: {
            http_proxy: null,
            https_proxy: null,
            no_proxy: null,
          },
        },
        repository_filters: ['*'],
        skopeo_timeout: 302,
        external_registry_username: null,
        external_registry_password: null,
      });

      // Update org mirror config
      await client.updateOrgMirrorConfig(org.name, {
        sync_interval: 3600,
        skopeo_timeout: 301,
      });

      // Get and verify
      const mirrorCfg = await client.getOrgMirrorConfig(org.name);
      expect(mirrorCfg).not.toBeNull();
      expect(mirrorCfg!.external_registry_url).toContain('https://quay.io');
      expect(mirrorCfg!.sync_interval).toBe(3600);

      // Sync-now
      await client.triggerOrgMirrorSync(org.name);

      // Sync-cancel
      await client.cancelOrgMirrorSync(org.name);

      // Verify connection to source registry
      const verifyResp = await adminClient.post(
        `/api/v1/organization/${org.name}/mirror/verify`,
      );
      // 200 with success = true, or accept other valid responses
      expect([200, 400, 502]).toContain(verifyResp.status());

      // List discovered repositories
      const reposResp = await adminClient.get(
        `/api/v1/organization/${org.name}/mirror/repositories`,
      );
      // May fail if connection can't be established; assert known statuses
      if (reposResp.status() === 200) {
        const reposBody = await reposResp.json();
        expect(reposBody).toHaveProperty('repositories');
        expect(Array.isArray(reposBody.repositories)).toBe(true);
      } else {
        expect([400, 403, 404, 502]).toContain(reposResp.status());
      }

      // Delete org mirror config
      await client.deleteOrgMirrorConfig(org.name);

      // Verify deletion
      const afterDelete = await client.getOrgMirrorConfig(org.name);
      expect(afterDelete).toBeNull();
    });
  },
);

// ---------------------------------------------------------------------------
// Sparse Manifest Support (from new_ui)
// ---------------------------------------------------------------------------
test.describe(
  'Registry Capabilities',
  {tag: ['@api', '@feature:SPARSE_INDEX']},
  () => {
    test('check sparse manifest support', async ({adminClient}) => {
      const resp = await adminClient.get('/api/v1/registry/capabilities');
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body).toHaveProperty('sparse_manifests');
      expect(body.sparse_manifests).toHaveProperty('supported');
      expect(typeof body.sparse_manifests.supported).toBe('boolean');
    });
  },
);

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
      const body = await enableResp.json().catch(() => ({}));
      const msg = (body.error_message || body.message || '').toLowerCase();
      const backendMissing =
        msg.includes('team syncing') ||
        msg.includes('not supported') ||
        msg.includes('ldap') ||
        msg.includes('keystone');
      test.skip(
        backendMissing || enableResp.status() === 401,
        `Team sync unavailable: ${msg || `HTTP ${enableResp.status()}`}`,
      );
      return;
    }
    expect([200, 201]).toContain(enableResp.status());

    const disableResp = await adminClient.delete(
      `/api/v1/organization/${org.name}/team/${team.name}/syncing`,
    );
    expect([200, 204]).toContain(disableResp.status());
  });
});
