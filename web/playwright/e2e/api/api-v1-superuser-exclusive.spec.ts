/**
 * Superuser-exclusive API tests.
 *
 * Ports tests from the Cypress quay_api_testing_super_user.cy.js that are
 * NOT covered in quay_api_testing_all.cy.js. These test endpoints and
 * workflows that require superuser privileges exclusively.
 *
 * Covered areas:
 *  - Service key approval
 *  - Namespace ownership takeover
 *  - Install user creation (server-generated password)
 *  - Superuser logs, aggregate logs, changelog
 *  - Tag restore and tag creation by manifest digest
 *  - Permission prototype full CRUD
 *  - Export action logs (repo, org, user)
 *  - User logs and per-resource aggregate logs
 */

import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushImage} from '../../utils/container';

// ---------------------------------------------------------------------------
// Service key approval
// ---------------------------------------------------------------------------
test.describe('Service Key Approve', {tag: ['@api', '@auth:Database']}, () => {
  test('superuser can create and approve a service key', async ({
    superuserApi,
    adminClient,
  }) => {
    const key = await superuserApi.serviceKey('quay', 'approve_test_key');

    // Approve via POST /api/v1/superuser/approvedkeys/{kid}
    const approveResp = await adminClient.post(
      `/api/v1/superuser/approvedkeys/${key.kid}`,
      {notes: 'approved by automation'},
    );
    expect(approveResp.status()).toBe(201);
  });
});

// ---------------------------------------------------------------------------
// Take ownership
// ---------------------------------------------------------------------------
test.describe('Take Ownership', {tag: ['@api', '@auth:Database']}, () => {
  test('superuser can take ownership of an organization', async ({
    superuserApi,
    adminClient,
  }) => {
    // Create an org owned by the superuser (simulating "another user's org")
    const org = await superuserApi.organization('takeown');

    // Take ownership via POST /api/v1/superuser/takeownership/{namespace}
    const resp = await adminClient.post(
      `/api/v1/superuser/takeownership/${org.name}`,
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.namespace).toBe(org.name);
  });
});

// ---------------------------------------------------------------------------
// Create install user (server-generated password)
// ---------------------------------------------------------------------------
test.describe('Create Install User', {tag: ['@api', '@auth:Database']}, () => {
  test('superuser can create a user via superuser API and get generated password', async ({
    superuserApi,
  }) => {
    const user = await superuserApi.user('install');
    expect(user.username).toBeTruthy();
    expect(user.email).toBeTruthy();
    // The superuser API returns a server-generated password
    expect(user.password).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// Superuser changelog
// ---------------------------------------------------------------------------
test.describe('Superuser Changelog', {tag: ['@api', '@auth:Database']}, () => {
  test('superuser can read changelog', async ({adminClient}) => {
    const resp = await adminClient.get('/api/v1/superuser/changelog/');
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.log).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Superuser logs (all logs)
// ---------------------------------------------------------------------------
test.describe('Superuser Logs', {tag: ['@api', '@auth:Database']}, () => {
  test('superuser can list all logs', async ({adminClient}) => {
    const resp = await adminClient.get('/api/v1/superuser/logs');
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.start_time).toBeDefined();
    expect(body.end_time).toBeDefined();
    expect(body.logs.length).toBeGreaterThanOrEqual(1);
  });
});

// ---------------------------------------------------------------------------
// Superuser aggregate logs
// ---------------------------------------------------------------------------
test.describe(
  'Superuser Aggregate Logs',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('superuser can read aggregate logs', async ({adminClient}) => {
      const resp = await adminClient.get('/api/v1/superuser/aggregatelogs');
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body.aggregated).toBeDefined();
    });
  },
);

// ---------------------------------------------------------------------------
// Tag restore and tag create (requires pushed image)
// ---------------------------------------------------------------------------
test.describe(
  'Tag Restore and Create',
  {tag: ['@api', '@auth:Database', '@container']},
  () => {
    test('superuser can restore a tag to a previous manifest digest', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('tagrestore');
      const repo = await superuserApi.repository(org.name, 'repo', 'public');

      // Push first image to get a manifest digest
      await pushImage(
        org.name,
        repo.name,
        'latest',
        TEST_USERS.admin.username,
        TEST_USERS.admin.password,
      );

      // Get the manifest digest of the first push
      const tagsResp1 = await adminClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/`,
      );
      expect(tagsResp1.status()).toBe(200);
      const tags1 = await tagsResp1.json();
      const firstDigest = tags1.tags[0].manifest_digest;
      expect(firstDigest).toContain('sha256');

      // Delete the tag (simulating "overwrite" -- delete then push won't change digest with busybox,
      // but restore still works as an API call)
      const deleteResp = await adminClient.delete(
        `/api/v1/repository/${org.name}/${repo.name}/tag/latest`,
      );
      expect(deleteResp.status()).toBe(204);

      // Restore the tag to the original manifest digest
      const restoreResp = await adminClient.post(
        `/api/v1/repository/${org.name}/${repo.name}/tag/latest/restore`,
        {manifest_digest: firstDigest},
      );
      expect(restoreResp.status()).toBe(200);

      // Verify tag is back
      const tagsResp2 = await adminClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/`,
      );
      expect(tagsResp2.status()).toBe(200);
      const tags2 = await tagsResp2.json();
      expect(tags2.tags.length).toBeGreaterThanOrEqual(1);
      const restoredTag = tags2.tags.find(
        (t: {name: string}) => t.name === 'latest',
      );
      expect(restoredTag).toBeDefined();
      expect(restoredTag.manifest_digest).toBe(firstDigest);
    });

    test('superuser can create a new tag pointing to existing manifest', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('tagcreate');
      const repo = await superuserApi.repository(org.name, 'repo', 'public');

      // Push image to get a manifest digest
      await pushImage(
        org.name,
        repo.name,
        'latest',
        TEST_USERS.admin.username,
        TEST_USERS.admin.password,
      );

      // Get the manifest digest
      const tagsResp = await adminClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/`,
      );
      expect(tagsResp.status()).toBe(200);
      const tags = await tagsResp.json();
      const digest = tags.tags[0].manifest_digest;

      // Create a new tag via PUT pointing to the same manifest
      const createResp = await adminClient.put(
        `/api/v1/repository/${org.name}/${repo.name}/tag/v1.0`,
        {manifest_digest: digest},
      );
      expect(createResp.status()).toBe(201);

      // Verify the new tag exists
      const tagsResp2 = await adminClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/`,
      );
      expect(tagsResp2.status()).toBe(200);
      const tags2 = await tagsResp2.json();
      const newTag = tags2.tags.find((t: {name: string}) => t.name === 'v1.0');
      expect(newTag).toBeDefined();
      expect(newTag.manifest_digest).toBe(digest);
    });
  },
);

// ---------------------------------------------------------------------------
// Permission prototype full CRUD
// ---------------------------------------------------------------------------
test.describe('Prototypes Full CRUD', {tag: ['@api', '@auth:Database']}, () => {
  test('superuser can create, list, update, and delete a permission prototype', async ({
    superuserApi,
    adminClient,
  }) => {
    const org = await superuserApi.organization('proto');
    const robot = await superuserApi.robot(org.name, 'protobot');

    // CREATE prototype
    const createResp = await adminClient.post(
      `/api/v1/organization/${org.name}/prototypes`,
      {
        delegate: {
          name: robot.fullName,
          kind: 'user',
          is_robot: true,
          is_org_member: true,
        },
        role: 'read',
      },
    );
    expect(createResp.status()).toBe(200);
    const created = await createResp.json();
    expect(created.delegate.name).toBe(robot.fullName);
    const prototypeId = created.id;

    // LIST prototypes
    const listResp = await adminClient.get(
      `/api/v1/organization/${org.name}/prototypes`,
    );
    expect(listResp.status()).toBe(200);
    const listed = await listResp.json();
    expect(listed.prototypes.length).toBeGreaterThanOrEqual(1);
    const found = listed.prototypes.find(
      (p: {id: string}) => p.id === prototypeId,
    );
    expect(found).toBeDefined();

    // UPDATE prototype role
    const updateResp = await adminClient.put(
      `/api/v1/organization/${org.name}/prototypes/${prototypeId}`,
      {role: 'admin', id: prototypeId},
    );
    expect(updateResp.status()).toBe(200);
    const updated = await updateResp.json();
    expect(updated.role).toBe('admin');

    // DELETE prototype
    const deleteResp = await adminClient.delete(
      `/api/v1/organization/${org.name}/prototypes/${prototypeId}`,
    );
    expect(deleteResp.status()).toBe(204);

    // Verify deletion
    const listResp2 = await adminClient.get(
      `/api/v1/organization/${org.name}/prototypes`,
    );
    expect(listResp2.status()).toBe(200);
    const listed2 = await listResp2.json();
    const notFound = listed2.prototypes.find(
      (p: {id: string}) => p.id === prototypeId,
    );
    expect(notFound).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// Export action logs (repo, org, user)
// ---------------------------------------------------------------------------
test.describe('Export Action Logs', {tag: ['@api', '@auth:Database']}, () => {
  test('superuser can export repository logs', async ({
    superuserApi,
    adminClient,
  }) => {
    const org = await superuserApi.organization('exportlogs');
    const repo = await superuserApi.repository(org.name, 'repo');

    const resp = await adminClient.post(
      `/api/v1/repository/${org.name}/${repo.name}/exportlogs`,
      {callback_email: 'test@example.com'},
    );
    // Export logs returns 200 (async job started)
    expect([200, 202]).toContain(resp.status());
  });

  test('superuser can export organization logs', async ({
    superuserApi,
    adminClient,
  }) => {
    const org = await superuserApi.organization('exportorglogs');

    const resp = await adminClient.post(
      `/api/v1/organization/${org.name}/exportlogs`,
      {callback_email: 'test@example.com'},
    );
    expect([200, 202]).toContain(resp.status());
  });

  test('superuser can export user logs', async ({adminClient}) => {
    const resp = await adminClient.post('/api/v1/user/exportlogs', {
      callback_email: 'test@example.com',
    });
    expect([200, 202]).toContain(resp.status());
  });
});

// ---------------------------------------------------------------------------
// User logs
// ---------------------------------------------------------------------------
test.describe('User Logs', {tag: ['@api', '@auth:Database']}, () => {
  test('superuser can read own user logs', async ({adminClient}) => {
    const resp = await adminClient.get('/api/v1/user/logs');
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.logs).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Aggregate logs per resource (repo, org, user)
// ---------------------------------------------------------------------------
test.describe(
  'Aggregate Logs Per Resource',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('superuser can read repository aggregate logs', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('agglogs');
      const repo = await superuserApi.repository(org.name, 'repo');

      const resp = await adminClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/aggregatelogs`,
      );
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body.aggregated).toBeDefined();
    });

    test('superuser can read organization aggregate logs', async ({
      superuserApi,
      adminClient,
    }) => {
      const org = await superuserApi.organization('agglogsorg');

      const resp = await adminClient.get(
        `/api/v1/organization/${org.name}/aggregatelogs`,
      );
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body.aggregated).toBeDefined();
    });

    test('superuser can read user aggregate logs', async ({adminClient}) => {
      const resp = await adminClient.get('/api/v1/user/aggregatelogs');
      expect(resp.status()).toBe(200);
      const body = await resp.json();
      expect(body.aggregated).toBeDefined();
    });
  },
);
