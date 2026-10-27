/**
 * Object storage verification tests.
 *
 * Verifies that pushed image blobs land in the configured S3-compatible
 * backend with the expected keys, that blob downloads redirect to the storage
 * backend, and that deleting a repository removes its blobs from every bucket.
 *
 * Requires:
 *   - crane CLI (for push)
 *   - awscli in PATH
 *   - S3_ENDPOINT, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
 *   - S3_REGION optional (default: us-east-1)
 *   - S3_BUCKETS and S3_STORAGE_PATH matching Quay's DISTRIBUTED_STORAGE_CONFIG.
 *     The defaults (quay-us-east,quay-eu-west and datastorage/registry) match
 *     local-dev/garage/georep-config.yaml; set both for any other S3 setup.
 *     See utils/s3.ts for details.
 *   - The host in Quay's presigned storage URLs must resolve from the test
 *     runner (CI adds "127.0.0.1 garage" to /etc/hosts in setup-quay).
 *
 * Run locally:
 *   S3_ENDPOINT=http://localhost:3900 S3_REGION=us-east-1 \
 *     pnpm exec playwright test \
 *     playwright/e2e/storage/object-storage.spec.ts
 */

import {createHash} from 'crypto';

import {expect, test} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {
  isCraneAvailable,
  pushUniqueImage,
  pushUniqueImageWithLayerBytes,
  pullImage,
} from '../../utils/container';
import {getV2Token} from '../../utils/api';
import {
  isS3Configured,
  getStorageBuckets,
  getPrimaryBucket,
  blobKey,
  headObject,
} from '../../utils/s3';
import {API_URL} from '../../utils/config';

// Sized so the single-chunk server-side copy goes through boto's managed
// multipart copy (> 8 MiB); the test does not assert which copy API was used.
const LAYER_BYTES = 12 * 1024 * 1024; // 12 MiB

// Worst case: up to 60 s until the first dequeue + 300 s retry when
// namespace GC holds the shared LARGE_GARBAGE_COLLECTION lock
// (workers/repositorygcworker.py, workers/queueworker.py) + up to 60 s
// until the next poll (= 420 s), plus 60 s margin for the purge.
const GC_TIMEOUT_MS = 480_000;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface ManifestV2 {
  schemaVersion: number;
  mediaType: string;
  config: {digest: string; size: number};
  layers: Array<{digest: string; size: number; mediaType: string}>;
}

async function fetchManifest(
  request: import('@playwright/test').APIRequestContext,
  repo: string,
  tag: string,
  token: string,
): Promise<ManifestV2> {
  const resp = await request.get(`${API_URL}/v2/${repo}/manifests/${tag}`, {
    headers: {
      Accept: 'application/vnd.docker.distribution.manifest.v2+json',
      Authorization: `Bearer ${token}`,
    },
  });
  expect(resp.ok(), `manifest fetch for ${repo}:${tag} failed`).toBe(true);
  return resp.json() as Promise<ManifestV2>;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe(
  'Object Storage',
  {
    tag: [
      '@api',
      '@storage',
      '@object-storage',
      '@container',
      '@PROJQUAY-13727',
    ],
  },
  () => {
    test.beforeAll(async () => {
      test.skip(
        !(await isS3Configured()),
        'S3 storage not configured (S3_ENDPOINT and aws CLI required)',
      );
      test.skip(
        !(await isCraneAvailable()),
        'crane CLI required for image push',
      );
    });

    // ---------------------------------------------------------------------------
    test('pushed blob is stored in the bucket with the expected key and size', async ({
      api,
      authenticatedRequest,
    }) => {
      test.setTimeout(120_000);

      const primaryBucket = getPrimaryBucket();

      const org = await api.organization();
      const repo = await api.repository(org.name);
      const tag = 'v1.0';

      // Push a unique image with a layer large enough to exercise multipart copy
      await pushUniqueImageWithLayerBytes(
        org.name,
        repo.name,
        tag,
        TEST_USERS.user.username,
        TEST_USERS.user.password,
        LAYER_BYTES,
      );

      const token = await getV2Token(
        authenticatedRequest,
        API_URL,
        TEST_USERS.user.username,
        TEST_USERS.user.password,
        `repository:${org.name}/${repo.name}:pull`,
      );

      const manifest = await fetchManifest(
        authenticatedRequest,
        `${org.name}/${repo.name}`,
        tag,
        token,
      );

      expect(
        manifest.layers.length,
        'manifest must have at least one layer',
      ).toBeGreaterThan(0);

      const layer = manifest.layers[manifest.layers.length - 1];
      const layerDigest = layer.digest;
      const declaredSize = layer.size;

      const key = blobKey(layerDigest);
      const meta = await headObject(primaryBucket, key);

      expect(
        meta,
        `S3 object ${key} not found in bucket ${primaryBucket}`,
      ).not.toBeNull();

      if (meta !== null) {
        expect(
          meta.size,
          `S3 object size in bucket ${primaryBucket} must match declared manifest layer size`,
        ).toBe(declaredSize);
      }

      // Pull via skopeo — it verifies layer digests while copying, confirming
      // the registry can reconstruct and serve the stored blob correctly
      await pullImage(
        org.name,
        repo.name,
        tag,
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
    });

    // ---------------------------------------------------------------------------
    test('blob download redirects to storage (direct or storage proxy) and serves the blob', async ({
      api,
      authenticatedRequest,
      request,
    }) => {
      test.setTimeout(60_000);

      const org = await api.organization();
      const repo = await api.repository(org.name);
      const tag = 'v1.0';

      // Small layer is sufficient — redirect behaviour is independent of size
      await pushUniqueImage(
        org.name,
        repo.name,
        tag,
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

      const manifest = await fetchManifest(
        authenticatedRequest,
        `${org.name}/${repo.name}`,
        tag,
        token,
      );

      expect(manifest.layers.length).toBeGreaterThan(0);
      const layerDigest = manifest.layers[manifest.layers.length - 1].digest;

      // GET the blob endpoint with maxRedirects: 0 — expect a 302 redirect
      const blobResp = await authenticatedRequest.get(
        `${API_URL}/v2/${org.name}/${repo.name}/blobs/${layerDigest}`,
        {
          headers: {Authorization: `Bearer ${token}`},
          maxRedirects: 0,
        },
      );

      expect(
        blobResp.status(),
        'blob endpoint must return 302 when storage provides direct download URLs',
      ).toBe(302);

      const location = blobResp.headers()['location'];
      expect(location, 'Location header must be present on 302').toBeTruthy();

      const locUrl = new URL(location);

      // Proxy URL structure (FEATURE_PROXY_STORAGE):
      //   /_storage_proxy/<b64jwt>/<scheme>/<storageHost>/<bucket/key>?<presigned>
      // Direct URL: scheme://storageHost/<bucket/key>?<presigned>
      const isProxy = locUrl.pathname.startsWith('/_storage_proxy/');

      if (isProxy) {
        test
          .info()
          .annotations.push({type: 'mode', description: 'storage proxy'});

        // Path segments: ['', '_storage_proxy', <token>, <scheme>, <host>, ...rest]
        const segments = locUrl.pathname.split('/');
        expect(
          segments.length,
          'proxy path must have at least 5 segments (_storage_proxy/<token>/<scheme>/<host>/...)',
        ).toBeGreaterThanOrEqual(5);
        expect(segments[1]).toBe('_storage_proxy');

        const embeddedScheme = segments[3];
        expect(
          embeddedScheme === 'http' || embeddedScheme === 'https',
          `embedded scheme must be http or https, got: ${embeddedScheme}`,
        ).toBe(true);

        const embeddedHost = segments[4];
        expect(embeddedHost, 'embedded host must be present').toBeTruthy();
      } else {
        test.info().annotations.push({type: 'mode', description: 'direct'});
      }

      // In both modes: path ends with the blob key suffix
      const keySuffix = blobKey(layerDigest).split('/').slice(-3).join('/');
      expect(
        locUrl.pathname.endsWith(`/${keySuffix}`),
        `Location path must end with /${keySuffix}`,
      ).toBe(true);

      // In both modes: presigned-URL signature present in the query string
      // (proxy mode embeds the presigned query from the original S3 URL)
      const hasSignature =
        locUrl.searchParams.has('X-Amz-Signature') ||
        locUrl.searchParams.has('Signature');
      expect(
        hasSignature,
        'Location URL must carry a presigned-URL signature (X-Amz-Signature or Signature)',
      ).toBe(true);

      // In both modes: GET the Location URL without the Quay Authorization
      // header and verify the sha256 of the body matches the layer digest.
      const directResp = await request.get(location);
      expect(
        directResp.ok(),
        `Storage GET failed: ${directResp.status()}`,
      ).toBe(true);

      const body = await directResp.body();
      const actualDigest = `sha256:${createHash('sha256')
        .update(body)
        .digest('hex')}`;
      expect(
        actualDigest,
        'sha256 of body from storage URL must equal the layer digest',
      ).toBe(layerDigest);
    });

    // ---------------------------------------------------------------------------
    test('deleting a repository removes its blobs from the bucket', async ({
      api,
      authenticatedRequest,
    }) => {
      test.setTimeout(120_000 + 60_000 + GC_TIMEOUT_MS); // setup + replication wait + GC wait

      const buckets = getStorageBuckets();
      const org = await api.organization();
      const repo = await api.repository(org.name);
      const tag = 'v1.0';

      // Push a unique image with a random layer so no other repo shares it
      await pushUniqueImageWithLayerBytes(
        org.name,
        repo.name,
        tag,
        TEST_USERS.user.username,
        TEST_USERS.user.password,
        1024 * 1024, // 1 MiB
      );

      const token = await getV2Token(
        authenticatedRequest,
        API_URL,
        TEST_USERS.user.username,
        TEST_USERS.user.password,
        `repository:${org.name}/${repo.name}:pull`,
      );

      const manifest = await fetchManifest(
        authenticatedRequest,
        `${org.name}/${repo.name}`,
        tag,
        token,
      );

      expect(manifest.layers.length).toBeGreaterThan(0);
      const layerDigest = manifest.layers[manifest.layers.length - 1].digest;
      const key = blobKey(layerDigest);

      // Wait until the layer is present in ALL buckets (geo-replication)
      await expect
        .poll(
          async () => {
            const checks = await Promise.all(
              buckets.map((b) => headObject(b, key)),
            );
            return checks.every((r) => r !== null);
          },
          {
            message: `waiting for blob ${key} to replicate to all buckets: ${buckets.join(
              ', ',
            )}`,
            timeout: 60_000,
            intervals: [2_000, 5_000, 10_000],
          },
        )
        .toBe(true);

      // Delete the repository. The api fixture's cleanup will also call
      // deleteRepository, but it ignores 404, so pre-deletion is safe.
      await api.raw.deleteRepository(org.name, repo.name);

      // Poll every bucket until the layer blob is gone (GC has run)
      await expect
        .poll(
          async () => {
            const checks = await Promise.all(
              buckets.map((b) => headObject(b, key)),
            );
            return checks.every((r) => r === null);
          },
          {
            message: `waiting for GC to remove blob ${key} from all buckets`,
            timeout: GC_TIMEOUT_MS,
            intervals: [5_000, 10_000, 15_000],
          },
        )
        .toBe(true);
    });
  },
);
