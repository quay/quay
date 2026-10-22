/**
 * Repository API Tests
 *
 * Ported from Cypress quay-api-tests: repository CRUD, tags, manifests,
 * labels, starred repos, search, and vulnerability scanning.
 *
 * Tests that require pushed images are tagged with @container so they
 * auto-skip when registry image tooling is unavailable.
 */

import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {RawApiClient} from '../../utils/api';
import {API_URL} from '../../utils/config';
import {pushImage} from '../../utils/container';

// ---------------------------------------------------------------------------
// Repository CRUD
// ---------------------------------------------------------------------------

test.describe('Repository CRUD', {tag: ['@api', '@auth:Database']}, () => {
  test(
    'create new repository under organization',
    {tag: '@superuser'},
    async ({adminClient, superuserApi}) => {
      const org = await superuserApi.organization('repo');
      const repoName = uniqueName('repo');

      const response = await adminClient.post('/api/v1/repository', {
        repo_kind: 'image',
        namespace: org.name,
        visibility: 'public',
        repository: repoName,
        description: 'repo for API automation testing',
      });
      expect(response.status()).toBe(201);

      const body = await response.json();
      expect(body.name).toBe(repoName);
      expect(body.namespace).toBe(org.name);
    },
  );

  test(
    'create 2nd repository under the same organization',
    {tag: '@superuser'},
    async ({adminClient, superuserApi}) => {
      const org = await superuserApi.organization('repo');
      const repo1 = uniqueName('repo1');
      const repo2 = uniqueName('repo2');

      const r1 = await adminClient.post('/api/v1/repository', {
        repo_kind: 'image',
        namespace: org.name,
        visibility: 'public',
        repository: repo1,
        description: 'first repo',
      });
      expect(r1.status()).toBe(201);

      const r2 = await adminClient.post('/api/v1/repository', {
        repo_kind: 'image',
        namespace: org.name,
        visibility: 'public',
        repository: repo2,
        description: 'second repo',
      });
      expect(r2.status()).toBe(201);

      const body = await r2.json();
      expect(body.name).toBe(repo2);
      expect(body.namespace).toBe(org.name);
    },
  );

  test(
    'get existing repository',
    {tag: '@superuser'},
    async ({adminClient, superuserApi}) => {
      const org = await superuserApi.organization('repo');
      const repo = await superuserApi.repository(org.name);

      const response = await adminClient.get(
        `/api/v1/repository/${org.name}/${repo.name}`,
      );
      expect(response.status()).toBe(200);

      const body = await response.json();
      expect(body.name).toBe(repo.name);
      expect(body.namespace).toBe(org.name);
    },
  );

  test(
    'update repository visibility',
    {tag: '@superuser'},
    async ({adminClient, superuserApi}) => {
      const org = await superuserApi.organization('repo');
      const repo = await superuserApi.repository(org.name);

      const response = await adminClient.post(
        `/api/v1/repository/${org.name}/${repo.name}/changevisibility`,
        {
          visibility: 'private',
        },
      );
      expect(response.status()).toBe(200);

      const body = await response.json();
      expect(body.success).toBe(true);
    },
  );

  test(
    'update repository description',
    {tag: '@superuser'},
    async ({adminClient, superuserApi}) => {
      const org = await superuserApi.organization('repo');
      const repo = await superuserApi.repository(org.name);

      const response = await adminClient.put(
        `/api/v1/repository/${org.name}/${repo.name}`,
        {
          description: 'updated description',
        },
      );
      expect(response.status()).toBe(200);

      const body = await response.json();
      expect(body.success).toBe(true);
    },
  );

  test(
    'delete repository',
    {tag: '@superuser'},
    async ({adminClient, superuserApi}) => {
      const org = await superuserApi.organization('repo');
      const repoName = uniqueName('delrepo');

      // Create repo directly (not via superuserApi to avoid double-delete)
      const create = await adminClient.post('/api/v1/repository', {
        repo_kind: 'image',
        namespace: org.name,
        visibility: 'public',
        repository: repoName,
        description: 'repo to delete',
      });
      expect(create.status()).toBe(201);

      const response = await adminClient.delete(
        `/api/v1/repository/${org.name}/${repoName}`,
      );
      expect(response.status()).toBe(204);
    },
  );

  test(
    'create repository under user namespace',
    {tag: '@superuser'},
    async ({adminClient, superuserApi}) => {
      const repoName = uniqueName('userrepo');
      const username = TEST_USERS.admin.username;

      const response = await adminClient.post('/api/v1/repository', {
        repo_kind: 'image',
        namespace: username,
        visibility: 'private',
        repository: repoName,
        description: 'repo under user namespace',
      });
      expect(response.status()).toBe(201);

      const body = await response.json();
      expect(body.name).toBe(repoName);
      expect(body.namespace).toBe(username);

      // Cleanup
      await adminClient.delete(`/api/v1/repository/${username}/${repoName}`);
    },
  );
});

// ---------------------------------------------------------------------------
// Repository admin boundaries
// ---------------------------------------------------------------------------

test.describe(
  'Repository admin boundaries',
  {tag: ['@api', '@auth:Database', '@superuser']},
  () => {
    test('writers and readers cannot change visibility, permissions or delete', async ({
      api,
      userClient,
      freshUser,
      request,
    }) => {
      const org = await api.organization('repoadmin');
      const repo = await api.repository(org.name, 'guarded');
      const team = await api.team(org.name, 'viewers');
      await api.repositoryPermission(
        org.name,
        repo.name,
        'team',
        team.name,
        'read',
      );
      const member = freshUser.user.username;
      await api.repositoryPermission(
        org.name,
        repo.name,
        'user',
        member,
        'write',
      );

      const repoPath = `/api/v1/repository/${repo.fullName}`;
      const teamPermissionPath = `${repoPath}/permissions/team/${team.name}`;
      const memberPermissionPath = `${repoPath}/permissions/user/${member}`;
      const collaborator = new RawApiClient(request, API_URL);
      await collaborator.signIn(member, freshUser.user.password);

      const repoState = async () => {
        const [repoResp, teamResp, memberResp] = await Promise.all([
          userClient.get(repoPath),
          userClient.get(teamPermissionPath),
          userClient.get(memberPermissionPath),
        ]);
        expect(repoResp.status()).toBe(200);
        expect(teamResp.status()).toBe(200);
        expect(memberResp.status()).toBe(200);
        const repoBody = await repoResp.json();
        return {
          isPublic: repoBody.is_public,
          description: repoBody.description,
          teamRole: (await teamResp.json()).role,
          memberRole: (await memberResp.json()).role,
        };
      };

      expect(
        (
          await collaborator.post(`${repoPath}/changevisibility`, {
            visibility: 'public',
          })
        ).status(),
      ).toBe(403);
      expect(
        (await collaborator.put(teamPermissionPath, {role: 'admin'})).status(),
      ).toBe(403);
      expect(
        (
          await collaborator.put(memberPermissionPath, {role: 'admin'})
        ).status(),
      ).toBe(403);
      expect((await collaborator.delete(repoPath)).status()).toBe(403);
      expect(
        (
          await collaborator.put(repoPath, {description: 'edited by a writer'})
        ).status(),
      ).toBe(200);
      expect(await repoState()).toEqual({
        isPublic: false,
        description: 'edited by a writer',
        teamRole: 'read',
        memberRole: 'write',
      });

      expect(
        (await userClient.put(memberPermissionPath, {role: 'read'})).status(),
      ).toBe(200);
      expect(
        (
          await collaborator.put(repoPath, {description: 'edited by a reader'})
        ).status(),
      ).toBe(403);

      expect(
        (
          await userClient.put(teamPermissionPath, {role: 'superadmin'})
        ).status(),
      ).toBe(400);
      expect(await repoState()).toEqual({
        isPublic: false,
        description: 'edited by a writer',
        teamRole: 'read',
        memberRole: 'read',
      });
    });
  },
);

// ---------------------------------------------------------------------------
// Tags
// ---------------------------------------------------------------------------

test.describe(
  'Repository Tags',
  {tag: ['@api', '@auth:Database', '@container']},
  () => {
    test(
      'get repository tags',
      {tag: '@superuser'},
      async ({adminClient, superuserApi}) => {
        const org = await superuserApi.organization('tag');
        const repo = await superuserApi.repository(org.name, 'tag', 'public');

        // Push an image so there is a tag to retrieve
        await pushImage(
          org.name,
          repo.name,
          'latest',
          TEST_USERS.admin.username,
          TEST_USERS.admin.password,
        );

        const response = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}/tag/`,
        );
        expect(response.status()).toBe(200);

        const body = await response.json();
        expect(body.tags).toBeTruthy();
        expect(body.tags.length).toBeGreaterThanOrEqual(1);
        expect(body.tags[0].name).toBe('latest');
      },
    );

    test(
      'delete tag',
      {tag: '@superuser'},
      async ({adminClient, superuserApi}) => {
        const org = await superuserApi.organization('tag');
        const repo = await superuserApi.repository(org.name, 'tag', 'public');

        await pushImage(
          org.name,
          repo.name,
          'latest',
          TEST_USERS.admin.username,
          TEST_USERS.admin.password,
        );

        const response = await adminClient.delete(
          `/api/v1/repository/${org.name}/${repo.name}/tag/latest`,
        );
        expect(response.status()).toBe(204);
      },
    );

    test(
      'permanently delete (expire) tag',
      {tag: '@superuser'},
      async ({adminClient, superuserApi}) => {
        const org = await superuserApi.organization('tag');
        const repo = await superuserApi.repository(org.name, 'tag', 'public');

        await pushImage(
          org.name,
          repo.name,
          'latest',
          TEST_USERS.admin.username,
          TEST_USERS.admin.password,
        );

        // First get the manifest digest
        const getRepo = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}?includeTags=true`,
        );
        expect(getRepo.status()).toBe(200);
        const repoBody = await getRepo.json();
        const manifestDigest = repoBody.tags.latest.manifest_digest;
        expect(manifestDigest).toContain('sha256');

        // Expire the tag (permanently delete).  The tag we just pushed is
        // still alive, so we must use is_alive: true so the API looks for an
        // active tag rather than one already in the time-machine window.
        const response = await adminClient.post(
          `/api/v1/repository/${org.name}/${repo.name}/tag/latest/expire`,
          {
            manifest_digest: manifestDigest,
            include_submanifests: true,
            is_alive: true,
          },
        );
        expect(response.status()).toBe(200);
      },
    );

    test(
      'get repository details with tags',
      {tag: '@superuser'},
      async ({adminClient, superuserApi}) => {
        const org = await superuserApi.organization('tag');
        const repo = await superuserApi.repository(org.name, 'tag', 'public');

        await pushImage(
          org.name,
          repo.name,
          'latest',
          TEST_USERS.admin.username,
          TEST_USERS.admin.password,
        );

        const response = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}?includeTags=true`,
        );
        expect(response.status()).toBe(200);

        const body = await response.json();
        expect(body.name).toBe(repo.name);
        expect(body.namespace).toBe(org.name);
        expect(body.tags).toBeDefined();
        expect(body.tags.latest).toBeDefined();
        expect(body.tags.latest.manifest_digest).toContain('sha256');
      },
    );
  },
);

// ---------------------------------------------------------------------------
// Manifest
// ---------------------------------------------------------------------------

test.describe(
  'Repository Manifest',
  {tag: ['@api', '@auth:Database', '@container']},
  () => {
    test(
      'get manifest digest',
      {tag: '@superuser'},
      async ({adminClient, superuserApi}) => {
        const org = await superuserApi.organization('manifest');
        const repo = await superuserApi.repository(
          org.name,
          'manifest',
          'public',
        );

        await pushImage(
          org.name,
          repo.name,
          'latest',
          TEST_USERS.admin.username,
          TEST_USERS.admin.password,
        );

        // Get the manifest digest from tags
        const getRepo = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}?includeTags=true`,
        );
        expect(getRepo.status()).toBe(200);
        const repoBody = await getRepo.json();
        const manifestDigest = repoBody.tags.latest.manifest_digest;
        expect(manifestDigest).toContain('sha256');

        // Get manifest by digest
        const response = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}/manifest/${manifestDigest}`,
        );
        expect(response.status()).toBe(200);

        const body = await response.json();
        expect(body.digest).toBe(manifestDigest);
      },
    );
  },
);

// ---------------------------------------------------------------------------
// Labels CRUD
// ---------------------------------------------------------------------------

test.describe(
  'Manifest Labels CRUD',
  {tag: ['@api', '@auth:Database', '@container']},
  () => {
    test(
      'add label to manifest',
      {tag: '@superuser'},
      async ({adminClient, superuserApi}) => {
        const org = await superuserApi.organization('label');
        const repo = await superuserApi.repository(org.name, 'label', 'public');

        await pushImage(
          org.name,
          repo.name,
          'latest',
          TEST_USERS.admin.username,
          TEST_USERS.admin.password,
        );

        // Get manifest digest
        const getRepo = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}?includeTags=true`,
        );
        const repoBody = await getRepo.json();
        const digest = repoBody.tags.latest.manifest_digest;

        const response = await adminClient.post(
          `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels`,
          {
            media_type: 'text/plain',
            key: 'env',
            value: 'prod',
          },
        );
        expect(response.status()).toBe(201);

        const body = await response.json();
        expect(body.label.key).toBe('env');
        expect(body.label.value).toBe('prod');
      },
    );

    test(
      'list labels on manifest',
      {tag: '@superuser'},
      async ({adminClient, superuserApi}) => {
        const org = await superuserApi.organization('label');
        const repo = await superuserApi.repository(org.name, 'label', 'public');

        await pushImage(
          org.name,
          repo.name,
          'latest',
          TEST_USERS.admin.username,
          TEST_USERS.admin.password,
        );

        const getRepo = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}?includeTags=true`,
        );
        const repoBody = await getRepo.json();
        const digest = repoBody.tags.latest.manifest_digest;

        // Add a label first
        const createResp = await adminClient.post(
          `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels`,
          {
            media_type: 'text/plain',
            key: 'env',
            value: 'staging',
          },
        );
        expect(createResp.status()).toBe(201);

        const response = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels`,
        );
        expect(response.status()).toBe(200);

        const body = await response.json();
        expect(body.labels).toBeInstanceOf(Array);
        expect(body.labels.length).toBeGreaterThan(0);
        const found = body.labels.some(
          (l: {key: string; value: string}) =>
            l.key === 'env' && l.value === 'staging',
        );
        expect(found).toBe(true);
      },
    );

    test(
      'get specific label',
      {tag: '@superuser'},
      async ({adminClient, superuserApi}) => {
        const org = await superuserApi.organization('label');
        const repo = await superuserApi.repository(org.name, 'label', 'public');

        await pushImage(
          org.name,
          repo.name,
          'latest',
          TEST_USERS.admin.username,
          TEST_USERS.admin.password,
        );

        const getRepo = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}?includeTags=true`,
        );
        const repoBody = await getRepo.json();
        const digest = repoBody.tags.latest.manifest_digest;

        // Create a label
        const createLabel = await adminClient.post(
          `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels`,
          {
            media_type: 'text/plain',
            key: 'env',
            value: 'prod',
          },
        );
        const labelId = (await createLabel.json()).label.id;

        // Get the specific label
        const response = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels/${labelId}`,
        );
        expect(response.status()).toBe(200);

        const body = await response.json();
        expect(body.key).toBe('env');
        expect(body.value).toBe('prod');
        expect(body.id).toBe(labelId);
      },
    );

    test(
      'delete label from manifest',
      {tag: '@superuser'},
      async ({adminClient, superuserApi}) => {
        const org = await superuserApi.organization('label');
        const repo = await superuserApi.repository(org.name, 'label', 'public');

        await pushImage(
          org.name,
          repo.name,
          'latest',
          TEST_USERS.admin.username,
          TEST_USERS.admin.password,
        );

        const getRepo = await adminClient.get(
          `/api/v1/repository/${org.name}/${repo.name}?includeTags=true`,
        );
        const repoBody = await getRepo.json();
        const digest = repoBody.tags.latest.manifest_digest;

        // Create a label
        const createLabel = await adminClient.post(
          `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels`,
          {
            media_type: 'text/plain',
            key: 'env',
            value: 'dev',
          },
        );
        const labelId = (await createLabel.json()).label.id;

        // Delete the label
        const response = await adminClient.delete(
          `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels/${labelId}`,
        );
        expect(response.status()).toBe(204);
      },
    );
  },
);

// ---------------------------------------------------------------------------
// Starred Repositories
// ---------------------------------------------------------------------------

test.describe('Starred Repositories', {tag: ['@api', '@auth:Database']}, () => {
  test(
    'add star to repository',
    {tag: '@superuser'},
    async ({adminClient, superuserApi}) => {
      const org = await superuserApi.organization('star');
      const repo = await superuserApi.repository(org.name, 'star', 'public');

      const response = await adminClient.post('/api/v1/user/starred', {
        namespace: org.name,
        repository: repo.name,
      });
      expect(response.status()).toBe(201);

      const body = await response.json();
      expect(body.namespace).toContain(org.name);
      expect(body.repository).toContain(repo.name);

      // Cleanup: remove star
      await adminClient.delete(`/api/v1/user/starred/${org.name}/${repo.name}`);
    },
  );

  test(
    'list starred repositories',
    {tag: '@superuser'},
    async ({adminClient, superuserApi}) => {
      const org = await superuserApi.organization('star');
      const repo = await superuserApi.repository(org.name, 'star', 'public');

      // Star the repo
      await adminClient.post('/api/v1/user/starred', {
        namespace: org.name,
        repository: repo.name,
      });

      const response = await adminClient.get('/api/v1/user/starred');
      expect(response.status()).toBe(200);

      const body = await response.json();
      expect(body.repositories).toBeTruthy();
      expect(body.repositories.length).toBeGreaterThanOrEqual(1);

      const found = body.repositories.some(
        (r: {name: string}) => r.name === repo.name,
      );
      expect(found).toBe(true);

      // Cleanup: remove star
      await adminClient.delete(`/api/v1/user/starred/${org.name}/${repo.name}`);
    },
  );

  test(
    'remove star from repository',
    {tag: '@superuser'},
    async ({adminClient, superuserApi}) => {
      const org = await superuserApi.organization('star');
      const repo = await superuserApi.repository(org.name, 'star', 'public');

      // Star it first
      await adminClient.post('/api/v1/user/starred', {
        namespace: org.name,
        repository: repo.name,
      });

      // Remove the star
      const response = await adminClient.delete(
        `/api/v1/user/starred/${org.name}/${repo.name}`,
      );
      expect(response.status()).toBe(204);
    },
  );
});

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

test.describe('Search', {tag: ['@api', '@auth:Database']}, () => {
  test(
    'search all registry context',
    {tag: '@superuser'},
    async ({adminClient, superuserApi}) => {
      const org = await superuserApi.organization('search');
      const repo = await superuserApi.repository(
        org.name,
        'searchable',
        'public',
      );

      const response = await adminClient.get(
        `/api/v1/find/all?query=${repo.name}`,
      );
      expect(response.status()).toBe(200);

      const body = await response.json();
      expect(body.results).toBeInstanceOf(Array);
      expect(body.results.length).toBeGreaterThan(0);
      const found = body.results.some(
        (r: {name: string}) => r.name === repo.name,
      );
      expect(found).toBe(true);
    },
  );

  test(
    'search repositories',
    {tag: '@superuser'},
    async ({adminClient, superuserApi}) => {
      const org = await superuserApi.organization('search');
      const repo = await superuserApi.repository(
        org.name,
        'searchable',
        'public',
      );

      const response = await adminClient.get(
        `/api/v1/find/repositories?query=${repo.name}`,
      );
      expect(response.status()).toBe(200);

      const body = await response.json();
      expect(body.results).toBeInstanceOf(Array);
      expect(body.results.length).toBeGreaterThan(0);
      const found = body.results.some(
        (r: {name: string}) => r.name === repo.name,
      );
      expect(found).toBe(true);
    },
  );
});

// ---------------------------------------------------------------------------
// Vulnerability Scanning (requires Clair integration)
// ---------------------------------------------------------------------------

test.describe(
  'Vulnerability Scanning',
  {tag: ['@api', '@auth:Database']},
  () => {
    test('list repository vulnerabilities', async () => {
      test.skip(true, 'Requires Clair integration');
    });
  },
);
