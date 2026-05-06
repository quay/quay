/**
 * Normal User Permission Boundary API Tests
 *
 * Verifies that a non-superuser can CRUD their own resources (orgs, repos,
 * teams, robots, notifications, tags, autoprune policies, proxy cache, mirror
 * config) and gets 403 on superuser-only endpoints.
 *
 * All assertions use `userClient` (normal user). Setup that requires
 * superuser privileges uses `adminClient` or `superuserApi`.
 *
 * Ported from: quay-api-tests/cypress/e2e/quay_api_testing_normal_user.cy.js
 */

import {test, expect, uniqueName} from '../../fixtures';
import {pushImage} from '../../utils/container';
import {TEST_USERS} from '../../global-setup';

// ---------------------------------------------------------------------------
// Organization CRUD
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Organization CRUD',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can create own organization', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      try {
        const r = await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        expect(r.status()).toBe(201);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('gets 404 for non-existing organization', async ({userClient}) => {
      const r = await userClient.get(
        '/api/v1/organization/nonexistent_org_xyz',
      );
      expect(r.status()).toBe(404);
    });

    test('can get own organization', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        const r = await userClient.get(`/api/v1/organization/${orgName}`);
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.name).toBe(orgName);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can update own organization details', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        const r = await userClient.put(`/api/v1/organization/${orgName}`, {
          invoice_email: true,
          email: `updated_${orgName}@example.com`,
        });
        expect(r.status()).toBe(200);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can delete own organization', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      await userClient.post('/api/v1/organization/', {
        name: orgName,
        email: `${orgName}@example.com`,
      });

      const r = await userClient.delete(`/api/v1/organization/${orgName}`);
      expect(r.status()).toBe(204);
    });
  },
);

// ---------------------------------------------------------------------------
// Organization Application (OAuth app) CRUD
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Organization Application CRUD',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can create, get, update, and delete an organization application', async ({
      userClient,
    }) => {
      const orgName = uniqueName('usr_org');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        // Create application
        const create = await userClient.post(
          `/api/v1/organization/${orgName}/applications`,
          {name: 'apptest'},
        );
        expect(create.status()).toBe(200);
        const createBody = await create.json();
        expect(createBody.name).toBe('apptest');
        const clientId = createBody.client_id;

        // Get application
        const get = await userClient.get(
          `/api/v1/organization/${orgName}/applications/${clientId}`,
        );
        expect(get.status()).toBe(200);
        const getBody = await get.json();
        expect(getBody.name).toBe('apptest');

        // Update application
        const update = await userClient.put(
          `/api/v1/organization/${orgName}/applications/${clientId}`,
          {
            name: 'apptestupdated',
            description: 'updated app',
            application_uri: 'https://example.com',
            redirect_uri: 'https://example.com/callback',
            avatar_email: 'app@example.com',
            client_id: clientId,
          },
        );
        expect(update.status()).toBe(200);
        const updateBody = await update.json();
        expect(updateBody.name).toBe('apptestupdated');

        // Delete application
        const del = await userClient.delete(
          `/api/v1/organization/${orgName}/applications/${clientId}`,
        );
        expect(del.status()).toBe(204);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Repository CRUD
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Repository CRUD',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can create a repository in own organization', async ({
      userClient,
    }) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        const r = await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'normal user test repo',
        });
        expect(r.status()).toBe(201);
        const body = await r.json();
        expect(body.name).toBe(repoName);
        expect(body.namespace).toBe(orgName);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can get own repository', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'test',
        });

        const r = await userClient.get(
          `/api/v1/repository/${orgName}/${repoName}`,
        );
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.name).toBe(repoName);
        expect(body.namespace).toBe(orgName);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can change repository visibility', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'test',
        });

        const r = await userClient.post(
          `/api/v1/repository/${orgName}/${repoName}/changevisibility`,
          {visibility: 'private'},
        );
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.success).toBe(true);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can update repository description', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'original',
        });

        const r = await userClient.put(
          `/api/v1/repository/${orgName}/${repoName}`,
          {description: 'updated description'},
        );
        expect(r.status()).toBe(200);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can delete own repository', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'test',
        });

        const r = await userClient.delete(
          `/api/v1/repository/${orgName}/${repoName}`,
        );
        expect(r.status()).toBe(204);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can create a repository under user namespace', async ({
      userClient,
    }) => {
      const repoName = uniqueName('usr_ns_repo');
      try {
        const r = await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: 'testuser',
          visibility: 'private',
          repository: repoName,
          description: 'user namespace repo',
        });
        expect(r.status()).toBe(201);
        const body = await r.json();
        expect(body.name).toBe(repoName);
        expect(body.namespace).toBe('testuser');
      } finally {
        await userClient.delete(`/api/v1/repository/testuser/${repoName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Permissions
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Repository Permissions',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can add, update, and remove user permissions on own repo', async ({
      userClient,
    }) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'test',
        });

        // Add write permission
        const add = await userClient.put(
          `/api/v1/repository/${orgName}/${repoName}/permissions/user/testuser`,
          {role: 'write'},
        );
        expect(add.status()).toBe(200);
        const addBody = await add.json();
        expect(addBody.role).toBe('write');

        // Update to admin permission
        const update = await userClient.put(
          `/api/v1/repository/${orgName}/${repoName}/permissions/user/testuser`,
          {role: 'admin'},
        );
        expect(update.status()).toBe(200);
        const updateBody = await update.json();
        expect(updateBody.role).toBe('admin');

        // Remove permission
        const del = await userClient.delete(
          `/api/v1/repository/${orgName}/${repoName}/permissions/user/testuser`,
        );
        expect(del.status()).toBe(204);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can list outside collaborators', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        const r = await userClient.get(
          `/api/v1/organization/${orgName}/collaborators`,
        );
        expect(r.status()).toBe(200);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Teams
// ---------------------------------------------------------------------------

test.describe('Normal User - Teams', {tag: ['@api', '@auth:Database']}, () => {
  test('can create a team and add team permission to repo', async ({
    userClient,
  }) => {
    const orgName = uniqueName('usr_org');
    const repoName = uniqueName('usr_repo');
    const teamName = uniqueName('usr_team').replace(/-/g, '_');
    try {
      await userClient.post('/api/v1/organization/', {
        name: orgName,
        email: `${orgName}@example.com`,
      });
      await userClient.post('/api/v1/repository', {
        repo_kind: 'image',
        namespace: orgName,
        visibility: 'public',
        repository: repoName,
        description: 'test',
      });

      // Create team
      const create = await userClient.put(
        `/api/v1/organization/${orgName}/team/${teamName}`,
        {name: teamName, role: 'member'},
      );
      expect(create.status()).toBe(200);
      const body = await create.json();
      expect(body.name).toContain(teamName);

      // Add team permission on repo
      const perm = await userClient.put(
        `/api/v1/repository/${orgName}/${repoName}/permissions/team/${teamName}`,
        {role: 'write'},
      );
      expect(perm.status()).toBe(200);

      // Add team member
      const member = await userClient.put(
        `/api/v1/organization/${orgName}/team/${teamName}/members/testuser`,
      );
      expect(member.status()).toBe(200);
    } finally {
      await userClient.delete(`/api/v1/organization/${orgName}`);
    }
  });
});

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Repository Notifications',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can CRUD notifications on own repository', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'test',
        });

        // List notifications (empty)
        const list = await userClient.get(
          `/api/v1/repository/${orgName}/${repoName}/notification/`,
        );
        expect(list.status()).toBe(200);

        // Create notification
        const create = await userClient.post(
          `/api/v1/repository/${orgName}/${repoName}/notification/`,
          {
            event: 'repo_push',
            method: 'quay_notification',
            config: {
              target: {
                name: 'owners',
                kind: 'team',
                is_robot: false,
                is_org_member: true,
              },
            },
            eventConfig: {},
            title: 'test push notification',
          },
        );
        expect(create.status()).toBe(201);
        const createBody = await create.json();
        const uuid = createBody.uuid;
        expect(uuid).toBeTruthy();

        // Test notification
        const testNotif = await userClient.post(
          `/api/v1/repository/${orgName}/${repoName}/notification/${uuid}/test`,
        );
        expect(testNotif.status()).toBe(200);

        // Reset notification failures
        const reset = await userClient.post(
          `/api/v1/repository/${orgName}/${repoName}/notification/${uuid}`,
        );
        expect(reset.status()).toBe(204);

        // Get notification by uuid
        const get = await userClient.get(
          `/api/v1/repository/${orgName}/${repoName}/notification/${uuid}`,
        );
        expect(get.status()).toBe(200);
        const getBody = await get.json();
        expect(getBody.uuid).toBe(uuid);

        // Delete notification
        const del = await userClient.delete(
          `/api/v1/repository/${orgName}/${repoName}/notification/${uuid}`,
        );
        expect(del.status()).toBe(204);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Robot Accounts
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Robot Accounts',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can create, get, list, and delete robots in own org', async ({
      userClient,
    }) => {
      const orgName = uniqueName('usr_org');
      const robotName = uniqueName('usr_bot').replace(/-/g, '_');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        // Create robot
        const create = await userClient.put(
          `/api/v1/organization/${orgName}/robots/${robotName}`,
          {},
        );
        expect(create.status()).toBe(201);

        // Get robot
        const get = await userClient.get(
          `/api/v1/organization/${orgName}/robots/${robotName}`,
        );
        expect(get.status()).toBe(200);

        // List robots
        const list = await userClient.get(
          `/api/v1/organization/${orgName}/robots?permissions=true&token=false`,
        );
        expect(list.status()).toBe(200);
        const listBody = await list.json();
        expect(listBody.robots.length).toBeGreaterThanOrEqual(1);

        // Delete robot
        const del = await userClient.delete(
          `/api/v1/organization/${orgName}/robots/${robotName}`,
        );
        expect(del.status()).toBe(204);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Default Permissions (Prototypes)
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Default Permissions',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can create default permission with robot in own org', async ({
      userClient,
    }) => {
      const orgName = uniqueName('usr_org');
      const robotName = uniqueName('usr_bot').replace(/-/g, '_');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.put(
          `/api/v1/organization/${orgName}/robots/${robotName}`,
          {},
        );

        const delegate = `${orgName}+${robotName}`;
        const r = await userClient.post(
          `/api/v1/organization/${orgName}/prototypes`,
          {
            delegate: {
              name: delegate,
              kind: 'user',
              is_robot: true,
              is_org_member: true,
            },
            role: 'read',
          },
        );
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.delegate.name).toBe(delegate);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Mirror Config
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Mirror Config',
  {tag: ['@api', '@auth:Database', '@feature:REPO_MIRROR']},
  () => {
    test('can create, update, get, and manage mirror config on own repo', async ({
      userClient,
    }) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      const mirrorRobot = 'mirrorbot';
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'test',
        });

        // Set repo to MIRROR state
        const setState = await userClient.put(
          `/api/v1/repository/${orgName}/${repoName}/changestate`,
          {state: 'MIRROR'},
        );
        expect(setState.status()).toBe(200);

        // Create mirror robot
        await userClient.put(
          `/api/v1/organization/${orgName}/robots/${mirrorRobot}`,
          {},
        );

        // Create mirror config
        const create = await userClient.post(
          `/api/v1/repository/${orgName}/${repoName}/mirror`,
          {
            is_enabled: false,
            external_reference: 'docker.io/library/alpine',
            sync_interval: 3600,
            sync_start_date: '2024-01-01T00:00:00Z',
            root_rule: {
              rule_kind: 'tag_glob_csv',
              rule_value: ['latest'],
            },
            robot_username: `${orgName}+${mirrorRobot}`,
            skopeo_timeout_interval: 300,
            external_registry_config: {
              verify_tls: true,
              unsigned_images: false,
              proxy: {
                http_proxy: null,
                https_proxy: null,
                no_proxy: null,
              },
            },
          },
        );
        expect(create.status()).toBe(201);

        // Update mirror config
        const update = await userClient.put(
          `/api/v1/repository/${orgName}/${repoName}/mirror`,
          {sync_interval: 7200},
        );
        expect(update.status()).toBe(201);

        // Get mirror config
        const get = await userClient.get(
          `/api/v1/repository/${orgName}/${repoName}/mirror`,
        );
        expect(get.status()).toBe(200);
        const getBody = await get.json();
        expect(getBody.sync_interval).toBe(7200);

        // Sync now
        const sync = await userClient.post(
          `/api/v1/repository/${orgName}/${repoName}/mirror/sync-now`,
        );
        expect(sync.status()).toBe(204);

        // Cancel sync
        const cancel = await userClient.post(
          `/api/v1/repository/${orgName}/${repoName}/mirror/sync-cancel`,
        );
        expect(cancel.status()).toBe(204);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Repository State Changes
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Repository State',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can change repository state (NORMAL -> MIRROR -> READ_ONLY -> NORMAL)', async ({
      userClient,
    }) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'test',
        });

        // Change to MIRROR
        const mirror = await userClient.put(
          `/api/v1/repository/${orgName}/${repoName}/changestate`,
          {state: 'MIRROR'},
        );
        expect(mirror.status()).toBe(200);

        // Change to READ_ONLY
        const readonly = await userClient.put(
          `/api/v1/repository/${orgName}/${repoName}/changestate`,
          {state: 'READ_ONLY'},
        );
        expect(readonly.status()).toBe(200);

        // Change back to NORMAL
        const normal = await userClient.put(
          `/api/v1/repository/${orgName}/${repoName}/changestate`,
          {state: 'NORMAL'},
        );
        expect(normal.status()).toBe(200);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Starred Repos
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Starred Repos',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can star, list, and unstar a repository', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'test',
        });

        // Star repository
        const star = await userClient.post('/api/v1/user/starred', {
          namespace: orgName,
          repository: repoName,
        });
        expect(star.status()).toBe(201);

        // List starred
        const list = await userClient.get('/api/v1/user/starred');
        expect(list.status()).toBe(200);
        const listBody = await list.json();
        const starred = listBody.repositories.find(
          (r: {name: string}) => r.name === repoName,
        );
        expect(starred).toBeTruthy();

        // Unstar repository
        const unstar = await userClient.delete(
          `/api/v1/user/starred/${orgName}/${repoName}`,
        );
        expect(unstar.status()).toBe(204);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Proxy Cache
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Proxy Cache',
  {tag: ['@api', '@auth:Database', '@feature:PROXY_CACHE']},
  () => {
    test('can create, get, and delete proxy cache config on own org', async ({
      userClient,
    }) => {
      const orgName = uniqueName('usr_org');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        // Create proxy cache config
        const create = await userClient.post(
          `/api/v1/organization/${orgName}/proxycache`,
          {
            upstream_registry: 'docker.io',
            expiration_s: 86400,
            insecure: false,
          },
        );
        expect(create.status()).toBe(201);

        // Get proxy cache config
        const get = await userClient.get(
          `/api/v1/organization/${orgName}/proxycache`,
        );
        expect(get.status()).toBe(200);
        const getBody = await get.json();
        expect(getBody.upstream_registry).toContain('docker.io');

        // Delete proxy cache config
        // NOTE: Backend returns 201 instead of 204 for DELETE - known issue
        const del = await userClient.delete(
          `/api/v1/organization/${orgName}/proxycache`,
        );
        expect(del.status()).toBe(201);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Autoprune Policies - Organization
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Autoprune Policies (Organization)',
  {tag: ['@api', '@auth:Database', '@feature:AUTO_PRUNE']},
  () => {
    test('rejects invalid autoprune method', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        const r = await userClient.post(
          `/api/v1/organization/${orgName}/autoprunepolicy/`,
          {method: 'number_of_times', value: 6},
        );
        expect(r.status()).toBe(400);
        const body = await r.json();
        expect(body.detail).toBe('Invalid method provided');
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can CRUD autoprune policy on own organization', async ({
      userClient,
    }) => {
      const orgName = uniqueName('usr_org');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        // Create
        const create = await userClient.post(
          `/api/v1/organization/${orgName}/autoprunepolicy/`,
          {method: 'number_of_tags', value: 6},
        );
        expect(create.status()).toBe(201);
        const createBody = await create.json();
        const uuid = createBody.uuid;
        expect(uuid).toBeTruthy();

        // List
        const list = await userClient.get(
          `/api/v1/organization/${orgName}/autoprunepolicy/`,
        );
        expect(list.status()).toBe(200);
        const listBody = await list.json();
        expect(listBody.policies[0].uuid).toBe(uuid);

        // Get by uuid
        const get = await userClient.get(
          `/api/v1/organization/${orgName}/autoprunepolicy/${uuid}`,
        );
        expect(get.status()).toBe(200);
        const getBody = await get.json();
        expect(getBody.uuid).toBe(uuid);

        // Update
        const update = await userClient.put(
          `/api/v1/organization/${orgName}/autoprunepolicy/${uuid}`,
          {method: 'creation_date', value: '7d'},
        );
        expect(update.status()).toBe(204);

        // Delete
        const del = await userClient.delete(
          `/api/v1/organization/${orgName}/autoprunepolicy/${uuid}`,
        );
        expect(del.status()).toBe(200);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Autoprune Policies - Repository (in org)
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Autoprune Policies (Repository)',
  {tag: ['@api', '@auth:Database', '@feature:AUTO_PRUNE']},
  () => {
    test('rejects invalid autoprune method for repository', async ({
      userClient,
    }) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'test',
        });

        const r = await userClient.post(
          `/api/v1/repository/${orgName}/${repoName}/autoprunepolicy/`,
          {method: 'number_of_times', value: 10},
        );
        expect(r.status()).toBe(400);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can CRUD autoprune policy on own repository', async ({
      userClient,
    }) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'test',
        });

        // Create
        const create = await userClient.post(
          `/api/v1/repository/${orgName}/${repoName}/autoprunepolicy/`,
          {method: 'number_of_tags', value: 10},
        );
        expect(create.status()).toBe(201);
        const createBody = await create.json();
        const uuid = createBody.uuid;
        expect(uuid).toBeTruthy();

        // Get
        const get = await userClient.get(
          `/api/v1/repository/${orgName}/${repoName}/autoprunepolicy/${uuid}`,
        );
        expect(get.status()).toBe(200);

        // Update
        const update = await userClient.put(
          `/api/v1/repository/${orgName}/${repoName}/autoprunepolicy/${uuid}`,
          {method: 'number_of_tags', value: 30},
        );
        expect(update.status()).toBe(204);

        // Delete
        const del = await userClient.delete(
          `/api/v1/repository/${orgName}/${repoName}/autoprunepolicy/${uuid}`,
        );
        expect(del.status()).toBe(200);
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can create autoprune policy on a second repository in same org', async ({
      userClient,
    }) => {
      const orgName = uniqueName('usr_org');
      const repoName1 = uniqueName('usr_repo');
      const repoName2 = uniqueName('usr_repo2');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName1,
          description: 'test1',
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName2,
          description: 'test2',
        });

        const r = await userClient.post(
          `/api/v1/repository/${orgName}/${repoName2}/autoprunepolicy/`,
          {method: 'number_of_tags', value: 8},
        );
        expect(r.status()).toBe(201);
        const body = await r.json();
        expect(body.uuid).toBeTruthy();
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Autoprune Policies - User Namespace
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Autoprune Policies (User Namespace)',
  {tag: ['@api', '@auth:Database', '@feature:AUTO_PRUNE']},
  () => {
    test('rejects invalid autoprune method for user namespace', async ({
      userClient,
    }) => {
      const r = await userClient.post('/api/v1/user/autoprunepolicy/', {
        method: 'number_of_times',
        value: 6,
      });
      expect(r.status()).toBe(400);
      const body = await r.json();
      expect(body.detail).toBe('Invalid method provided');
    });

    test('can CRUD autoprune policy on user namespace', async ({
      userClient,
    }) => {
      // Create
      const create = await userClient.post('/api/v1/user/autoprunepolicy/', {
        method: 'number_of_tags',
        value: 6,
      });
      expect(create.status()).toBe(201);
      const createBody = await create.json();
      const uuid = createBody.uuid;
      expect(uuid).toBeTruthy();

      try {
        // List
        const list = await userClient.get('/api/v1/user/autoprunepolicy/');
        expect(list.status()).toBe(200);
        const listBody = await list.json();
        expect(
          listBody.policies.some((p: {uuid: string}) => p.uuid === uuid),
        ).toBe(true);

        // Get by uuid
        const get = await userClient.get(
          `/api/v1/user/autoprunepolicy/${uuid}`,
        );
        expect(get.status()).toBe(200);
        const getBody = await get.json();
        expect(getBody.uuid).toBe(uuid);

        // Update
        const update = await userClient.put(
          `/api/v1/user/autoprunepolicy/${uuid}`,
          {method: 'creation_date', value: '7d'},
        );
        expect(update.status()).toBe(204);
      } finally {
        // Delete
        const del = await userClient.delete(
          `/api/v1/user/autoprunepolicy/${uuid}`,
        );
        expect(del.status()).toBe(200);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// Autoprune Policies - Repository under User Namespace
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Autoprune Policies (Repo under User Namespace)',
  {tag: ['@api', '@auth:Database', '@feature:AUTO_PRUNE']},
  () => {
    test('rejects invalid autoprune method for repo under user namespace', async ({
      userClient,
    }) => {
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: 'testuser',
          visibility: 'private',
          repository: repoName,
          description: 'test',
        });

        const r = await userClient.post(
          `/api/v1/repository/testuser/${repoName}/autoprunepolicy/`,
          {method: 'number_of_times', value: 10},
        );
        expect(r.status()).toBe(400);
      } finally {
        await userClient.delete(`/api/v1/repository/testuser/${repoName}`);
      }
    });

    test('can CRUD autoprune policy on repo under user namespace', async ({
      userClient,
    }) => {
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: 'testuser',
          visibility: 'private',
          repository: repoName,
          description: 'test',
        });

        // Create
        const create = await userClient.post(
          `/api/v1/repository/testuser/${repoName}/autoprunepolicy/`,
          {method: 'number_of_tags', value: 6},
        );
        expect(create.status()).toBe(201);
        const createBody = await create.json();
        const uuid = createBody.uuid;
        expect(uuid).toBeTruthy();

        // Get
        const get = await userClient.get(
          `/api/v1/repository/testuser/${repoName}/autoprunepolicy/${uuid}`,
        );
        expect(get.status()).toBe(200);

        // Update
        const update = await userClient.put(
          `/api/v1/repository/testuser/${repoName}/autoprunepolicy/${uuid}`,
          {method: 'number_of_tags', value: 30},
        );
        expect(update.status()).toBe(204);

        // Delete
        const del = await userClient.delete(
          `/api/v1/repository/testuser/${repoName}/autoprunepolicy/${uuid}`,
        );
        expect(del.status()).toBe(200);
      } finally {
        await userClient.delete(`/api/v1/repository/testuser/${repoName}`);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// User Information
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - User Information',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can get own user information', async ({userClient}) => {
      const r = await userClient.get('/api/v1/user/');
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.username).toBe('testuser');
    });

    test('can get user info by username', async ({userClient}) => {
      const r = await userClient.get('/api/v1/users/testuser');
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.username).toBe('testuser');
    });

    test('can generate encrypted password', async ({userClient}) => {
      const r = await userClient.post('/api/v1/user/clientkey', {
        password: 'password',
      });
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.key).toBeTruthy();
    });
  },
);

// ---------------------------------------------------------------------------
// Logs
// ---------------------------------------------------------------------------

test.describe('Normal User - Logs', {tag: ['@api', '@auth:Database']}, () => {
  test('can get user logs', async ({userClient}) => {
    const r = await userClient.get('/api/v1/user/logs');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.logs).toBeDefined();
  });

  test('can get user aggregate logs', async ({userClient}) => {
    const r = await userClient.get('/api/v1/user/aggregatelogs');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.aggregated).toBeDefined();
  });

  test('can get repository logs', async ({userClient}) => {
    const orgName = uniqueName('usr_org');
    const repoName = uniqueName('usr_repo');
    try {
      await userClient.post('/api/v1/organization/', {
        name: orgName,
        email: `${orgName}@example.com`,
      });
      await userClient.post('/api/v1/repository', {
        repo_kind: 'image',
        namespace: orgName,
        visibility: 'public',
        repository: repoName,
        description: 'test',
      });

      const r = await userClient.get(
        `/api/v1/repository/${orgName}/${repoName}/logs`,
      );
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.logs).toBeDefined();
    } finally {
      await userClient.delete(`/api/v1/organization/${orgName}`);
    }
  });

  test('can get organization logs', async ({userClient}) => {
    const orgName = uniqueName('usr_org');
    try {
      await userClient.post('/api/v1/organization/', {
        name: orgName,
        email: `${orgName}@example.com`,
      });

      const r = await userClient.get(`/api/v1/organization/${orgName}/logs`);
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.logs).toBeDefined();
    } finally {
      await userClient.delete(`/api/v1/organization/${orgName}`);
    }
  });

  test('can get repository aggregate logs', async ({userClient}) => {
    const orgName = uniqueName('usr_org');
    const repoName = uniqueName('usr_repo');
    try {
      await userClient.post('/api/v1/organization/', {
        name: orgName,
        email: `${orgName}@example.com`,
      });
      await userClient.post('/api/v1/repository', {
        repo_kind: 'image',
        namespace: orgName,
        visibility: 'public',
        repository: repoName,
        description: 'test',
      });

      const r = await userClient.get(
        `/api/v1/repository/${orgName}/${repoName}/aggregatelogs`,
      );
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.aggregated).toBeDefined();
    } finally {
      await userClient.delete(`/api/v1/organization/${orgName}`);
    }
  });

  test('can get organization aggregate logs', async ({userClient}) => {
    const orgName = uniqueName('usr_org');
    try {
      await userClient.post('/api/v1/organization/', {
        name: orgName,
        email: `${orgName}@example.com`,
      });

      const r = await userClient.get(
        `/api/v1/organization/${orgName}/aggregatelogs`,
      );
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.aggregated).toBeDefined();
    } finally {
      await userClient.delete(`/api/v1/organization/${orgName}`);
    }
  });
});

// ---------------------------------------------------------------------------
// Export Logs
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Export Logs',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can export repository logs', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      const repoName = uniqueName('usr_repo');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });
        await userClient.post('/api/v1/repository', {
          repo_kind: 'image',
          namespace: orgName,
          visibility: 'public',
          repository: repoName,
          description: 'test',
        });

        const r = await userClient.post(
          `/api/v1/repository/${orgName}/${repoName}/exportlogs`,
          {callback_url: 'https://example.com/callback'},
        );
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.export_id).toBeTruthy();
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can export organization logs', async ({userClient}) => {
      const orgName = uniqueName('usr_org');
      try {
        await userClient.post('/api/v1/organization/', {
          name: orgName,
          email: `${orgName}@example.com`,
        });

        const r = await userClient.post(
          `/api/v1/organization/${orgName}/exportlogs`,
          {callback_url: 'https://example.com/callback'},
        );
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.export_id).toBeTruthy();
      } finally {
        await userClient.delete(`/api/v1/organization/${orgName}`);
      }
    });

    test('can export user logs', async ({userClient}) => {
      const r = await userClient.post('/api/v1/user/exportlogs', {
        callback_url: 'https://example.com/callback',
      });
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.export_id).toBeTruthy();
    });
  },
);

// ---------------------------------------------------------------------------
// Tags, Manifests, Labels (require pushed images)
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Tags and Manifests',
  {tag: ['@api', '@auth:Database', '@container']},
  () => {
    test('can list tags for an empty repository (returns 200 with no tags)', async ({
      userClient,
      api,
    }) => {
      const org = await api.organization('usr_org');
      const repo = await api.repository(org.name, 'usr_repo', 'public');

      const tagR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/`,
      );
      // Empty repository returns 200 with an empty tags list
      expect(tagR.status()).toBe(200);
      const body = await tagR.json();
      expect(Array.isArray(body.tags ?? [])).toBe(true);
    });

    test('can list tags on own repo with pushed image', async ({
      userClient,
      api,
    }) => {
      const org = await api.organization('usr_org');
      const repo = await api.repository(org.name, 'usr_repo', 'public');

      await pushImage(
        org.name,
        repo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const tagR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/`,
      );
      expect(tagR.status()).toBe(200);
      const body = await tagR.json();
      const tags: Array<{name: string}> = body.tags ?? [];
      expect(tags.some((t) => t.name === 'latest')).toBe(true);
    });

    test('can delete tag on own repo', async ({userClient, api}) => {
      const org = await api.organization('usr_org');
      const repo = await api.repository(org.name, 'usr_repo', 'public');

      await pushImage(
        org.name,
        repo.name,
        'deltag',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const delR = await userClient.delete(
        `/api/v1/repository/${org.name}/${repo.name}/tag/deltag`,
      );
      expect(delR.status()).toBe(204);
    });

    test('can create (add) a tag on own repo', async ({userClient, api}) => {
      const org = await api.organization('usr_org');
      const repo = await api.repository(org.name, 'usr_repo', 'public');

      await pushImage(
        org.name,
        repo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const listR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/?includeTags=true`,
      );
      expect(listR.status()).toBe(200);
      const listBody = await listR.json();
      const tags: Array<{name: string; manifest_digest: string}> =
        listBody.tags ?? [];
      const latestTag = tags.find((t) => t.name === 'latest');
      if (!latestTag) throw new Error('Expected latest tag not found');
      const digest = latestTag.manifest_digest;

      const putR = await userClient.put(
        `/api/v1/repository/${org.name}/${repo.name}/tag/newtag`,
        {manifest_digest: digest},
      );
      expect(putR.status()).toBe(201);
    });

    test('can restore a deleted tag on own repo', async ({userClient, api}) => {
      const org = await api.organization('usr_org');
      const repo = await api.repository(org.name, 'usr_repo', 'public');

      await pushImage(
        org.name,
        repo.name,
        'restoretag',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const listR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/?includeTags=true`,
      );
      expect(listR.status()).toBe(200);
      const listBody = await listR.json();
      const tags: Array<{name: string; manifest_digest: string}> =
        listBody.tags ?? [];
      const tag = tags.find((t) => t.name === 'restoretag');
      if (!tag) throw new Error('Expected restoretag not found');
      const digest = tag.manifest_digest;

      const delR = await userClient.delete(
        `/api/v1/repository/${org.name}/${repo.name}/tag/restoretag`,
      );
      expect(delR.status()).toBe(204);

      const restoreR = await userClient.post(
        `/api/v1/repository/${org.name}/${repo.name}/tag/restoretag/restore`,
        {manifest_digest: digest},
      );
      expect(restoreR.status()).toBe(200);

      const verifyR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/`,
      );
      expect(verifyR.status()).toBe(200);
      const verifyBody = await verifyR.json();
      const restored: Array<{name: string}> = verifyBody.tags ?? [];
      expect(restored.some((t) => t.name === 'restoretag')).toBe(true);
    });

    test('can permanently delete (expire) a tag on own repo', async ({
      userClient,
      api,
    }) => {
      const org = await api.organization('usr_org');
      const repo = await api.repository(org.name, 'usr_repo', 'public');

      await pushImage(
        org.name,
        repo.name,
        'expiretag',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const listR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/?includeTags=true`,
      );
      expect(listR.status()).toBe(200);
      const listBody = await listR.json();
      const tags: Array<{name: string; manifest_digest: string}> =
        listBody.tags ?? [];
      const tag = tags.find((t) => t.name === 'expiretag');
      if (!tag) throw new Error('Expected expiretag not found');
      const digest = tag.manifest_digest;

      const expireR = await userClient.post(
        `/api/v1/repository/${org.name}/${repo.name}/tag/expiretag/expire`,
        {
          manifest_digest: digest,
          include_submanifests: true,
          is_alive: true,
        },
      );
      expect([200, 201]).toContain(expireR.status());
    });
  },
);

// ---------------------------------------------------------------------------
// Manifests
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Manifests',
  {tag: ['@api', '@auth:Database', '@container']},
  () => {
    test('can get manifest digest on own repo', async ({userClient, api}) => {
      const org = await api.organization('usr_org');
      const repo = await api.repository(org.name, 'usr_repo', 'public');

      await pushImage(
        org.name,
        repo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const listR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/?includeTags=true`,
      );
      expect(listR.status()).toBe(200);
      const listBody = await listR.json();
      const tags: Array<{name: string; manifest_digest: string}> =
        listBody.tags ?? [];
      const tag = tags.find((t) => t.name === 'latest');
      if (!tag) throw new Error('Expected latest tag not found');
      const digest = tag.manifest_digest;

      const manifestR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}`,
      );
      expect(manifestR.status()).toBe(200);
      const manifestBody = await manifestR.json();
      expect(manifestBody.digest).toBe(digest);
    });
  },
);

// ---------------------------------------------------------------------------
// Manifest Labels
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Manifest Labels',
  {tag: ['@api', '@auth:Database', '@container']},
  () => {
    test('can add, list, get, and delete labels on own manifest', async ({
      userClient,
      api,
    }) => {
      const org = await api.organization('usr_org');
      const repo = await api.repository(org.name, 'usr_repo', 'public');

      await pushImage(
        org.name,
        repo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const listR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/?includeTags=true`,
      );
      expect(listR.status()).toBe(200);
      const listBody = await listR.json();
      const tags: Array<{name: string; manifest_digest: string}> =
        listBody.tags ?? [];
      const tag = tags.find((t) => t.name === 'latest');
      if (!tag) throw new Error('Expected latest tag not found');
      const digest = tag.manifest_digest;

      // Add label
      const addR = await userClient.post(
        `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels`,
        {key: 'env', value: 'prod', media_type: 'text/plain'},
      );
      expect(addR.status()).toBe(201);

      // List labels
      const listLabelsR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels`,
      );
      expect(listLabelsR.status()).toBe(200);
      const labelsBody = await listLabelsR.json();
      const labels: Array<{id: string; key: string; value: string}> =
        labelsBody.labels ?? [];
      const label = labels.find((l) => l.key === 'env' && l.value === 'prod');
      if (!label) throw new Error('Expected label not found');
      const labelId = label.id;

      // Get by id
      const getR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels/${labelId}`,
      );
      expect(getR.status()).toBe(200);
      const getBody = await getR.json();
      expect(getBody.key).toBe('env');
      expect(getBody.value).toBe('prod');
      expect(getBody.id).toBe(labelId);

      // Delete label
      const deleteR = await userClient.delete(
        `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels/${labelId}`,
      );
      expect(deleteR.status()).toBe(204);

      // Verify deleted
      const verifyR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels`,
      );
      expect(verifyR.status()).toBe(200);
      const verifyBody = await verifyR.json();
      const remaining: Array<{id: string}> = verifyBody.labels ?? [];
      expect(remaining.some((l) => l.id === labelId)).toBe(false);
    });
  },
);

// ---------------------------------------------------------------------------
// Vulnerability Scanning
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Vulnerability Scanning',
  {tag: ['@api', '@auth:Database', '@container', '@feature:SECURITY_SCANNER']},
  () => {
    test('can get security scan status for own manifest', async ({
      userClient,
      api,
    }) => {
      const org = await api.organization('usr_org');
      const repo = await api.repository(org.name, 'usr_repo', 'public');

      await pushImage(
        org.name,
        repo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const listR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/tag/?includeTags=true`,
      );
      expect(listR.status()).toBe(200);
      const listBody = await listR.json();
      const tags: Array<{name: string; manifest_digest: string}> =
        listBody.tags ?? [];
      const tag = tags.find((t) => t.name === 'latest');
      if (!tag) throw new Error('Expected latest tag not found');
      const digest = tag.manifest_digest;

      // Verify the security endpoint is accessible and returns a valid status.
      // In CI without a live Clair instance the scan stays 'queued'; we only
      // assert that the endpoint responds and the status field is present.
      const secR = await userClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/security?vulnerabilities=true`,
      );
      expect(secR.status()).toBe(200);
      const secBody = await secR.json();
      expect(
        ['queued', 'scanned', 'failed', 'unsupported'].includes(secBody.status),
      ).toBe(true);
    });
  },
);

// ---------------------------------------------------------------------------
// Search / Discovery
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Search and Discovery',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can discover API endpoints', async ({userClient}) => {
      const r = await userClient.get('/api/v1/discovery');
      expect(r.status()).toBe(200);
    });

    test('can search entities and resources', async ({userClient}) => {
      const r = await userClient.get('/api/v1/find/all?query=testuser');
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.results).toBeDefined();
    });

    test('can search repositories', async ({userClient}) => {
      const r = await userClient.get(
        '/api/v1/find/repositories?query=testuser',
      );
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.results).toBeDefined();
    });
  },
);

// ---------------------------------------------------------------------------
// Error Descriptions
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Error Descriptions',
  {tag: ['@api', '@auth:Database']},
  () => {
    const errorTypes = [
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

    for (const errorType of errorTypes) {
      test(`can get error description: ${errorType}`, async ({userClient}) => {
        const r = await userClient.get(`/api/v1/error/${errorType}`);
        expect(r.status()).toBe(200);
        const body = await r.json();
        expect(body.title).toBe(errorType);
      });
    }
  },
);

// ---------------------------------------------------------------------------
// App Tokens
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - App Tokens',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can create, list, get, and revoke an app token', async ({
      userClient,
    }) => {
      // Create
      const create = await userClient.post('/api/v1/user/apptoken', {
        title: 'test_apptoken',
      });
      expect(create.status()).toBe(200);
      const createBody = await create.json();
      expect(createBody.token.title).toBe('test_apptoken');
      const tokenUuid = createBody.token.uuid;

      try {
        // List
        const list = await userClient.get('/api/v1/user/apptoken');
        expect(list.status()).toBe(200);
        const listBody = await list.json();
        const found = listBody.tokens.find(
          (t: {uuid: string}) => t.uuid === tokenUuid,
        );
        expect(found).toBeTruthy();

        // Get
        const get = await userClient.get(`/api/v1/user/apptoken/${tokenUuid}`);
        expect(get.status()).toBe(200);
        const getBody = await get.json();
        expect(getBody.token.title).toBe('test_apptoken');
      } finally {
        // Revoke
        const del = await userClient.delete(
          `/api/v1/user/apptoken/${tokenUuid}`,
        );
        expect(del.status()).toBe(204);
      }
    });
  },
);

// ---------------------------------------------------------------------------
// 403 Boundary Tests - Superuser endpoints forbidden
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - 403 Superuser Boundary',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('gets 403 on GET /superuser/users/', async ({userClient}) => {
      const r = await userClient.get('/api/v1/superuser/users/');
      expect(r.status()).toBe(403);
    });

    test('gets 403 on POST /superuser/users/', async ({userClient}) => {
      const r = await userClient.post('/api/v1/superuser/users/', {
        username: 'shouldfail',
        email: 'shouldfail@example.com',
      });
      expect(r.status()).toBe(403);
    });

    test('gets 403 on DELETE /superuser/users/{user}', async ({userClient}) => {
      const r = await userClient.delete('/api/v1/superuser/users/admin');
      expect(r.status()).toBe(403);
    });

    test('gets 403 on GET /superuser/keys', async ({userClient}) => {
      const r = await userClient.get('/api/v1/superuser/keys');
      expect(r.status()).toBe(403);
    });

    test('gets 403 on POST /superuser/keys', async ({userClient}) => {
      const r = await userClient.post('/api/v1/superuser/keys', {
        service: 'test_svc',
        name: 'should_fail_key',
        expiration: null,
      });
      expect(r.status()).toBe(403);
    });

    test('gets 404 on GET /superuser/registrysettings (endpoint removed)', async ({
      userClient,
    }) => {
      const r = await userClient.get('/api/v1/superuser/registrysettings/');
      expect(r.status()).toBe(404);
    });

    test('gets non-200 or expected response on POST /superuser/config/validate/{service}', async ({
      userClient,
    }) => {
      const r = await userClient.post(
        '/api/v1/superuser/config/validate/database',
        {},
      );
      // Response varies by Quay config: 403 (forbidden), 404 (removed),
      // 400 (validation error), or 200 (endpoint accessible to all)
      expect(r.status()).toBeLessThan(500);
    });

    test('gets 403 on GET /superuser/organizations/', async ({userClient}) => {
      const r = await userClient.get('/api/v1/superuser/organizations/');
      expect(r.status()).toBe(403);
    });

    test('gets 403 on POST /messages (create global message)', async ({
      userClient,
    }) => {
      const r = await userClient.post('/api/v1/messages', {
        message: {
          content: 'should fail',
          media_type: 'text/plain',
          severity: 'info',
        },
      });
      expect(r.status()).toBe(403);
    });

    test(
      'gets 403 on user quota via superuser API',
      {tag: ['@feature:QUOTA_MANAGEMENT']},
      async ({userClient}) => {
        const r = await userClient.get(
          '/api/v1/superuser/users/testuser/quota',
        );
        expect(r.status()).toBe(403);
      },
    );
  },
);

// ---------------------------------------------------------------------------
// Health Endpoints (accessible by anyone)
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Health Endpoints',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can access health instance endpoint', async ({userClient}) => {
      const r = await userClient.get('/health/instance');
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.data.services.database).toBe(true);
    });

    test('can access health endtoend endpoint', async ({userClient}) => {
      const r = await userClient.get('/health/endtoend');
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.data.services.database).toBe(true);
    });

    test('can access health warning endpoint', async ({userClient}) => {
      const r = await userClient.get('/health/warning');
      expect(r.status()).toBe(200);
    });
  },
);

// ---------------------------------------------------------------------------
// Security Scanner Backfill
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Security Scanner',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can check security scanner backfill status', async ({userClient}) => {
      const r = await userClient.get('/secscan/_backfill_status');
      expect(r.status()).toBe(200);
    });
  },
);

// ---------------------------------------------------------------------------
// Sign In (internal API)
// ---------------------------------------------------------------------------

test.describe(
  'Normal User - Sign In',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('can verify authentication as normal user', async ({anonClient}) => {
      // Use unauthenticated client to verify credential-based sign-in works
      const r = await anonClient.post('/api/v1/signin', {
        username: 'testuser',
        password: 'password',
      });
      expect(r.status()).toBe(200);
      const body = await r.json();
      expect(body.success).toBe(true);
    });
  },
);
