/**
 * Nested OCI Image Index regression test for PROJQUAY-8272.
 *
 * Verifies that pushing a nested OCI image index (an index whose child
 * manifests include another index) succeeds via the V2 registry API.
 *
 * Before the fix, the registry returned a 500 error with
 * "Unable to retrieve manifest labels" when the outer index was pushed,
 * because the label-retrieval code did not account for child manifests
 * that are themselves indexes (which have no config blob / labels).
 */

import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {getV2Token} from '../../utils/api/auth';
import {pushImage} from '../../utils/container';
import {API_URL} from '../../utils/config';

const OCI_INDEX_MEDIA_TYPE = 'application/vnd.oci.image.index.v1+json';
const DOCKER_MANIFEST_V2 =
  'application/vnd.docker.distribution.manifest.v2+json';

test.describe(
  'Nested OCI Image Index (PROJQUAY-8272)',
  {tag: ['@api', '@container', '@PROJQUAY-8272', '@auth:Database']},
  () => {
    const username = TEST_USERS.user.username;
    const password = TEST_USERS.user.password;

    test('push nested OCI image index succeeds', async ({
      api,
      playwright,
      cachedContainerAvailable,
    }) => {
      test.skip(!cachedContainerAvailable, 'Container tooling not available');

      // Create org and repo using api fixture (auto-cleanup on test end)
      const org = await api.organization('nestidx');
      const repo = await api.repository(org.name, 'repo', 'public');

      // Push two test images so their manifests exist in the repo
      await pushImage(org.name, repo.name, 'img1', username, password);
      await pushImage(org.name, repo.name, 'img2', username, password);

      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const scope = `repository:${org.name}/${repo.name}:pull,push`;
        const v2Token = await getV2Token(
          request,
          API_URL,
          username,
          password,
          scope,
        );
        const headers = {authorization: `Bearer ${v2Token}`};

        // --- Fetch manifests for both pushed images ---

        const img1Resp = await request.get(
          `${API_URL}/v2/${org.name}/${repo.name}/manifests/img1`,
          {headers: {...headers, Accept: DOCKER_MANIFEST_V2}},
        );
        expect(img1Resp.status()).toBe(200);
        const img1Digest = img1Resp.headers()['docker-content-digest'];
        const img1Body = await img1Resp.body();
        const img1Size = img1Body.byteLength;
        expect(img1Digest).toBeTruthy();

        const img2Resp = await request.get(
          `${API_URL}/v2/${org.name}/${repo.name}/manifests/img2`,
          {headers: {...headers, Accept: DOCKER_MANIFEST_V2}},
        );
        expect(img2Resp.status()).toBe(200);
        const img2Digest = img2Resp.headers()['docker-content-digest'];
        const img2Body = await img2Resp.body();
        const img2Size = img2Body.byteLength;
        expect(img2Digest).toBeTruthy();

        // --- Build inner OCI index referencing both images ---

        const innerIndex = {
          schemaVersion: 2,
          mediaType: OCI_INDEX_MEDIA_TYPE,
          manifests: [
            {
              mediaType: DOCKER_MANIFEST_V2,
              digest: img1Digest,
              size: img1Size,
              platform: {architecture: 'amd64', os: 'linux'},
            },
            {
              mediaType: DOCKER_MANIFEST_V2,
              digest: img2Digest,
              size: img2Size,
              platform: {architecture: 'arm64', os: 'linux'},
            },
          ],
        };
        const innerIndexBody = JSON.stringify(innerIndex);

        // --- PUT inner index ---

        const innerPutResp = await request.put(
          `${API_URL}/v2/${org.name}/${repo.name}/manifests/inner-index`,
          {
            headers: {
              ...headers,
              'Content-Type': OCI_INDEX_MEDIA_TYPE,
            },
            data: innerIndexBody,
          },
        );
        expect(innerPutResp.status()).toBe(201);

        // --- GET inner index to obtain its digest and size ---

        const innerGetResp = await request.get(
          `${API_URL}/v2/${org.name}/${repo.name}/manifests/inner-index`,
          {headers: {...headers, Accept: OCI_INDEX_MEDIA_TYPE}},
        );
        expect(innerGetResp.status()).toBe(200);
        const innerDigest = innerGetResp.headers()['docker-content-digest'];
        const innerGetBody = await innerGetResp.body();
        const innerSize = innerGetBody.byteLength;
        expect(innerDigest).toBeTruthy();

        // --- Build outer (nested) index referencing inner index + one image ---
        // This is the key scenario: an index whose child is another index.
        // Before the fix, pushing this returned 500 because the registry
        // tried to read labels from the inner index (which has no config blob).

        const outerIndex = {
          schemaVersion: 2,
          mediaType: OCI_INDEX_MEDIA_TYPE,
          manifests: [
            {
              mediaType: OCI_INDEX_MEDIA_TYPE,
              digest: innerDigest,
              size: innerSize,
            },
            {
              mediaType: DOCKER_MANIFEST_V2,
              digest: img1Digest,
              size: img1Size,
              platform: {architecture: 'amd64', os: 'linux'},
            },
          ],
        };
        const outerIndexBody = JSON.stringify(outerIndex);

        // --- PUT outer (nested) index ---
        // Before the PROJQUAY-8272 fix, this returned 500 with
        // "Unable to retrieve manifest labels"

        const outerPutResp = await request.put(
          `${API_URL}/v2/${org.name}/${repo.name}/manifests/nested-index`,
          {
            headers: {
              ...headers,
              'Content-Type': OCI_INDEX_MEDIA_TYPE,
            },
            data: outerIndexBody,
          },
        );
        expect(outerPutResp.status()).toBe(201);

        // --- Verify the nested index can be retrieved ---

        const outerGetResp = await request.get(
          `${API_URL}/v2/${org.name}/${repo.name}/manifests/nested-index`,
          {headers: {...headers, Accept: OCI_INDEX_MEDIA_TYPE}},
        );
        expect(outerGetResp.status()).toBe(200);

        const outerBody = await outerGetResp.json();
        expect(outerBody.schemaVersion).toBe(2);
        expect(outerBody.manifests).toHaveLength(2);
      } finally {
        await request.dispose();
      }
    });
  },
);
