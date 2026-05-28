import {expect, test} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {
  pushUniqueImage,
  pushMultiArchImage,
  pullImage,
} from '../../utils/container';
import {getV2Token} from '../../utils/api';
import {
  isAwscliAvailable,
  listBucketObjects,
  listBuckets,
  deleteObject,
} from '../../utils/s3';
import {API_URL} from '../../utils/config';

function digestToS3Key(digest: string): string {
  const hash = digest.replace('sha256:', '');
  return `datastorage/registry/sha256/${hash.substring(0, 2)}/${hash}`;
}

function extractBlobDigests(manifest: Record<string, unknown>): string[] {
  if (manifest.layers) {
    return [
      (manifest.config as {digest: string}).digest,
      ...(manifest.layers as {digest: string}[]).map((l) => l.digest),
    ];
  }
  throw new Error(
    `Unexpected manifest format (expected v2): ${JSON.stringify(manifest).slice(
      0,
      200,
    )}`,
  );
}

async function fetchManifestDigests(
  request: import('@playwright/test').APIRequestContext,
  repo: string,
  tag: string,
  token: string,
): Promise<string[]> {
  const resp = await request.get(`${API_URL}/v2/${repo}/manifests/${tag}`, {
    headers: {
      Accept: 'application/vnd.docker.distribution.manifest.v2+json',
      Authorization: `Bearer ${token}`,
    },
  });
  expect(resp.ok()).toBe(true);
  return extractBlobDigests(await resp.json());
}

async function waitForReplication(
  expectedKeys: string[],
  bucketList: string[],
) {
  for (const bucket of bucketList) {
    await expect
      .poll(
        async () => {
          const objects = new Set(await listBucketObjects(bucket));
          return expectedKeys.every((key) => objects.has(key));
        },
        {
          message: `waiting for ${expectedKeys.length} blobs in "${bucket}"`,
          timeout: 60_000,
          intervals: [2_000, 5_000, 10_000],
        },
      )
      .toBe(true);
  }
}

test.describe(
  'Geo-Replication',
  {tag: ['@feature:STORAGE_REPLICATION', '@container']},
  () => {
    let buckets: string[];

    test.beforeAll(async () => {
      const awsAvailable = await isAwscliAvailable();
      test.skip(!awsAvailable, 'awscli not available');

      buckets = await listBuckets();
      test.skip(
        buckets.length < 2,
        `Need at least 2 buckets for geo-replication, found ${buckets.length}`,
      );
    });

    test('pushed image blobs replicate to all storage regions', async ({
      api,
      authenticatedRequest,
    }) => {
      test.setTimeout(120_000);

      const org = await api.organization();
      const repo = await api.repository(org.name);

      await pushUniqueImage(
        org.name,
        repo.name,
        'v1.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const token = await getV2Token(
        authenticatedRequest,
        API_URL,
        TEST_USERS.user.username,
        TEST_USERS.user.password,
        `repository:${org.name}/${repo.name}:pull`,
      );

      const digests = await fetchManifestDigests(
        authenticatedRequest,
        `${org.name}/${repo.name}`,
        'v1.0',
        token,
      );
      await waitForReplication(digests.map(digestToS3Key), buckets);
    });

    test('pull succeeds when replica blob is deleted (data survives single-region loss)', async ({
      api,
      authenticatedRequest,
    }) => {
      test.setTimeout(120_000);

      const org = await api.organization();
      const repo = await api.repository(org.name);

      await pushUniqueImage(
        org.name,
        repo.name,
        'fallback',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const token = await getV2Token(
        authenticatedRequest,
        API_URL,
        TEST_USERS.user.username,
        TEST_USERS.user.password,
        `repository:${org.name}/${repo.name}:pull`,
      );

      const digests = await fetchManifestDigests(
        authenticatedRequest,
        `${org.name}/${repo.name}`,
        'fallback',
        token,
      );
      const expectedKeys = digests.map(digestToS3Key);
      await waitForReplication(expectedKeys, buckets);

      // Delete from the last bucket (non-preferred replica).
      // Quay's _location_aware always serves from the preferred location
      // (DISTRIBUTED_STORAGE_PREFERENCE[0]) when it's in the placements list,
      // so deleting from a non-preferred replica verifies replication happened
      // while ensuring the pull still succeeds through the preferred path.
      const replicaBucket = buckets[buckets.length - 1];
      const testKey = expectedKeys[0];
      await deleteObject(replicaBucket, testKey);

      const objectsAfterDelete = await listBucketObjects(replicaBucket);
      expect(objectsAfterDelete).not.toContain(testKey);

      await pullImage(
        org.name,
        repo.name,
        'fallback',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
    });

    test('multi-arch manifest list blobs replicate to all storage regions', async ({
      api,
      authenticatedRequest,
    }) => {
      test.setTimeout(120_000);

      const org = await api.organization();
      const repo = await api.repository(org.name);

      await pushMultiArchImage(
        org.name,
        repo.name,
        'multiarch',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const token = await getV2Token(
        authenticatedRequest,
        API_URL,
        TEST_USERS.user.username,
        TEST_USERS.user.password,
        `repository:${org.name}/${repo.name}:pull`,
      );

      // Fetch manifest list and walk each platform manifest
      const listResp = await authenticatedRequest.get(
        `${API_URL}/v2/${org.name}/${repo.name}/manifests/multiarch`,
        {
          headers: {
            Accept:
              'application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.index.v1+json',
            Authorization: `Bearer ${token}`,
          },
        },
      );
      expect(listResp.ok()).toBe(true);

      const manifestList = await listResp.json();
      const allDigests: string[] = [];

      for (const entry of manifestList.manifests) {
        const platformResp = await authenticatedRequest.get(
          `${API_URL}/v2/${org.name}/${repo.name}/manifests/${entry.digest}`,
          {
            headers: {
              Accept: 'application/vnd.docker.distribution.manifest.v2+json',
              Authorization: `Bearer ${token}`,
            },
          },
        );
        expect(platformResp.ok()).toBe(true);
        allDigests.push(...extractBlobDigests(await platformResp.json()));
      }

      const uniqueKeys = [...new Set(allDigests)].map(digestToS3Key);
      await waitForReplication(uniqueKeys, buckets);
    });
  },
);
