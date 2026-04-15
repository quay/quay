/**
 * Repository API Tests
 *
 * Ported from Cypress quay-api-tests: repository CRUD, tags, manifests,
 * labels, starred repos, search, and vulnerability scanning.
 *
 * Tests that require pushed images are tagged with @container so they
 * auto-skip when no container runtime is available.
 */

import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushImage} from '../../utils/container';

// ---------------------------------------------------------------------------
// Repository CRUD
// ---------------------------------------------------------------------------

test.describe('Repository CRUD', {tag: ['@api', '@auth:Database']}, () => {
  test('create new repository under organization', async ({
    adminClient,
    superuserApi,
  }) => {
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
  });

  test('create 2nd repository under the same organization', async ({
    adminClient,
    superuserApi,
  }) => {
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
  });

  test('get existing repository', async ({adminClient, superuserApi}) => {
    const org = await superuserApi.organization('repo');
    const repo = await superuserApi.repository(org.name);

    const response = await adminClient.get(
      `/api/v1/repository/${org.name}/${repo.name}`,
    );
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body.name).toBe(repo.name);
    expect(body.namespace).toBe(org.name);
  });

  test('update repository visibility', async ({adminClient, superuserApi}) => {
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
  });

  test('update repository description', async ({adminClient, superuserApi}) => {
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
  });

  test('delete repository', async ({adminClient, superuserApi}) => {
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
  });

  test('create repository under user namespace', async ({
    adminClient,
    superuserApi,
  }) => {
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
  });
});

// ---------------------------------------------------------------------------
// Tags
// ---------------------------------------------------------------------------

test.describe(
  'Repository Tags',
  {tag: ['@api', '@auth:Database', '@container']},
  () => {
    test('get repository tags', async ({adminClient, superuserApi}) => {
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
    });

    test('delete tag', async ({adminClient, superuserApi}) => {
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
    });

    test('permanently delete (expire) tag', async ({
      adminClient,
      superuserApi,
    }) => {
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
    });

    test('get pull statistics for repository', async ({
      adminClient,
      superuserApi,
    }) => {
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
      expect(body.tags.latest.manifest_digest).toContain('sha256');
    });
  },
);

// ---------------------------------------------------------------------------
// Manifest
// ---------------------------------------------------------------------------

test.describe(
  'Repository Manifest',
  {tag: ['@api', '@auth:Database', '@container']},
  () => {
    test('get manifest digest', async ({adminClient, superuserApi}) => {
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
      expect(body.digest).toContain('sha256');
    });
  },
);

// ---------------------------------------------------------------------------
// Labels CRUD
// ---------------------------------------------------------------------------

test.describe(
  'Manifest Labels CRUD',
  {tag: ['@api', '@auth:Database', '@container']},
  () => {
    test('add label to manifest', async ({adminClient, superuserApi}) => {
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
    });

    test('list labels on manifest', async ({adminClient, superuserApi}) => {
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
      await adminClient.post(
        `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels`,
        {
          media_type: 'text/plain',
          key: 'env',
          value: 'staging',
        },
      );

      const response = await adminClient.get(
        `/api/v1/repository/${org.name}/${repo.name}/manifest/${digest}/labels`,
      );
      expect(response.status()).toBe(200);

      const body = await response.json();
      expect(body.labels).toBeTruthy();
    });

    test('get specific label', async ({adminClient, superuserApi}) => {
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
    });

    test('delete label from manifest', async ({adminClient, superuserApi}) => {
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
    });
  },
);

// ---------------------------------------------------------------------------
// Starred Repositories
// ---------------------------------------------------------------------------

test.describe('Starred Repositories', {tag: ['@api', '@auth:Database']}, () => {
  test('add star to repository', async ({adminClient, superuserApi}) => {
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
  });

  test('list starred repositories', async ({adminClient, superuserApi}) => {
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
  });

  test('remove star from repository', async ({adminClient, superuserApi}) => {
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
  });
});

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

test.describe('Search', {tag: ['@api', '@auth:Database']}, () => {
  test('search all registry context', async ({adminClient, superuserApi}) => {
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
    expect(body.results).toBeTruthy();
  });

  test('search repositories', async ({adminClient, superuserApi}) => {
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
    expect(body.results).toBeTruthy();
  });
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
