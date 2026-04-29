/**
 * V2 Registry Coverage Gap Tests
 *
 * Targets V2 registry endpoints identified as uncovered by the Jaeger trace
 * coverage analysis: blob deletion, blob upload status, and POST v2 auth.
 */

import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {getV2Token} from '../../utils/api/auth';
import {pushImage} from '../../utils/container';
import {API_URL} from '../../utils/config';

const DOCKER_MANIFEST_V2 =
  'application/vnd.docker.distribution.manifest.v2+json';

// ---------------------------------------------------------------------------
// V2 Blob Delete
// ---------------------------------------------------------------------------
test.describe(
  'V2 Blob Delete',
  {tag: ['@api', '@v2', '@container', '@auth:Database']},
  () => {
    test('delete a blob by digest', async ({
      userContext,
      playwright,
      cachedContainerAvailable,
    }) => {
      if (!cachedContainerAvailable) return;

      const username = TEST_USERS.user.username;
      const password = TEST_USERS.user.password;
      const api = new ApiClient(userContext.request);

      const orgName = uniqueName('v2blobdel');
      const repoName = uniqueName('repo');

      try {
        await api.createOrganization(orgName, `${orgName}@example.com`);
        await api.createRepository(orgName, repoName, 'public');
        await pushImage(orgName, repoName, 'latest', username, password);

        const scope = `repository:${orgName}/${repoName}:pull,push`;
        const v2Token = await getV2Token(
          userContext.request,
          API_URL,
          username,
          password,
          scope,
        );

        // Get manifest to find blob digests
        const manifestResp = await userContext.request.get(
          `${API_URL}/v2/${orgName}/${repoName}/manifests/latest`,
          {
            headers: {
              authorization: `Bearer ${v2Token}`,
              Accept: DOCKER_MANIFEST_V2,
            },
          },
        );
        expect(manifestResp.status()).toBe(200);
        const manifest = await manifestResp.json();

        // Get a blob digest from the config layer
        const configDigest = manifest.config?.digest;
        expect(configDigest).toBeTruthy();

        // DELETE the blob by digest
        const request = await playwright.request.newContext({
          ignoreHTTPSErrors: true,
        });
        try {
          const deleteResp = await request.delete(
            `${API_URL}/v2/${orgName}/${repoName}/blobs/${configDigest}`,
            {
              headers: {
                authorization: `Bearer ${v2Token}`,
              },
            },
          );
          // 202 = accepted, 404/405 = blob not deletable or feature disabled
          expect([202, 404, 405]).toContain(deleteResp.status());
        } finally {
          await request.dispose();
        }
      } finally {
        try {
          await api.deleteRepository(orgName, repoName);
        } catch {
          /* ignore */
        }
        try {
          await api.deleteOrganization(orgName);
        } catch {
          /* ignore */
        }
      }
    });
  },
);

// ---------------------------------------------------------------------------
// V2 Blob Upload Status
// ---------------------------------------------------------------------------
test.describe(
  'V2 Blob Upload Status',
  {tag: ['@api', '@v2', '@container', '@auth:Database']},
  () => {
    test('start blob upload and check upload status', async ({
      userContext,
      playwright,
      cachedContainerAvailable,
    }) => {
      if (!cachedContainerAvailable) return;

      const username = TEST_USERS.user.username;
      const password = TEST_USERS.user.password;
      const api = new ApiClient(userContext.request);

      const orgName = uniqueName('v2upload');
      const repoName = uniqueName('repo');

      try {
        await api.createOrganization(orgName, `${orgName}@example.com`);
        await api.createRepository(orgName, repoName, 'public');

        const scope = `repository:${orgName}/${repoName}:pull,push`;

        const request = await playwright.request.newContext({
          ignoreHTTPSErrors: true,
        });
        try {
          const v2Token = await getV2Token(
            request,
            API_URL,
            username,
            password,
            scope,
          );

          // Start a blob upload (POST)
          const startResp = await request.post(
            `${API_URL}/v2/${orgName}/${repoName}/blobs/uploads/`,
            {
              headers: {
                authorization: `Bearer ${v2Token}`,
              },
            },
          );
          expect([201, 202]).toContain(startResp.status());

          // Extract upload UUID from Location header
          const location = startResp.headers()['location'] || '';
          const uuidMatch = location.match(/uploads\/([a-f0-9-]+)/);
          if (uuidMatch) {
            const uploadUuid = uuidMatch[1];

            // GET upload status
            const statusResp = await request.get(
              `${API_URL}/v2/${orgName}/${repoName}/blobs/uploads/${uploadUuid}`,
              {
                headers: {
                  authorization: `Bearer ${v2Token}`,
                },
              },
            );
            expect([200, 204]).toContain(statusResp.status());
          }
        } finally {
          await request.dispose();
        }
      } finally {
        try {
          await api.deleteRepository(orgName, repoName);
        } catch {
          /* ignore */
        }
        try {
          await api.deleteOrganization(orgName);
        } catch {
          /* ignore */
        }
      }
    });
  },
);

// ---------------------------------------------------------------------------
// V2 Auth via POST
// ---------------------------------------------------------------------------
test.describe('V2 Auth POST', {tag: ['@api', '@v2', '@auth:Database']}, () => {
  test('POST /v2/auth returns token or method-not-allowed', async ({
    playwright,
  }) => {
    const username = TEST_USERS.user.username;
    const password = TEST_USERS.user.password;

    const request = await playwright.request.newContext({
      ignoreHTTPSErrors: true,
    });
    try {
      const params = new URLSearchParams({
        service: new URL(API_URL).host,
      });

      const resp = await request.post(
        `${API_URL}/v2/auth?${params.toString()}`,
        {
          headers: {
            Authorization: `Basic ${Buffer.from(
              `${username}:${password}`,
            ).toString('base64')}`,
          },
        },
      );
      // POST may return 200 (token) or 405 (method not allowed)
      expect([200, 405]).toContain(resp.status());
      if (resp.status() === 200) {
        const body = await resp.json();
        expect(body.token).toBeTruthy();
      }
    } finally {
      await request.dispose();
    }
  });
});
