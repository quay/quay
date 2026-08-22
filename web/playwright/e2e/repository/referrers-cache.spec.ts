/**
 * OCI Referrers cache serialization e2e test.
 *
 * Validates that the referrers endpoint returns consistent results across
 * repeated calls (exercising the cache serialization/deserialization path).
 */

import path from 'path';
import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {getV2Token} from '../../utils/api/auth';
import {pushImage, orasAttach, isOrasAvailable} from '../../utils/container';
import {API_URL} from '../../utils/config';

test.describe(
  'OCI Referrers Cache',
  {tag: ['@repository', '@container', '@auth:Database']},
  () => {
    test.describe.configure({mode: 'serial'});

    const username = TEST_USERS.user.username;
    const password = TEST_USERS.user.password;

    let orgName: string;
    let repoName: string;
    let manifestDigest: string;

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      if (!cachedContainerAvailable) return;

      const api = new ApiClient(userContext.request);

      orgName = uniqueName('refcache');
      repoName = uniqueName('repo');

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
      const r = await userContext.request.get(
        `${API_URL}/v2/${orgName}/${repoName}/manifests/latest`,
        {
          headers: {
            authorization: `Bearer ${v2Token}`,
            Accept: 'application/vnd.docker.distribution.manifest.v2+json',
          },
        },
      );
      expect(r.status()).toBe(200);
      manifestDigest = r.headers()['docker-content-digest'];
      expect(manifestDigest).toBeTruthy();
    });

    test.afterAll(async ({userContext, cachedContainerAvailable}) => {
      if (!cachedContainerAvailable || !orgName) return;

      const api = new ApiClient(userContext.request);
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
    });

    test('referrers endpoint returns consistent results across repeated calls', async ({
      playwright,
    }) => {
      const orasAvailable = await isOrasAvailable();
      test.skip(!orasAvailable, 'oras CLI required for referrer tests');

      const fixturesDir = path.resolve(__dirname, '../../fixtures/oras');

      orasAttach(
        orgName,
        repoName,
        'latest',
        username,
        password,
        'application/spdx+json',
        'producer=test',
        path.join(fixturesDir, 'referrer.spdx.json'),
      );

      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const scope = `repository:${orgName}/${repoName}:pull,push`;
        const v2Token = await getV2Token(
          request,
          API_URL,
          username,
          password,
          scope,
        );

        const url = `${API_URL}/v2/${orgName}/${repoName}/referrers/${manifestDigest}`;
        const headers = {authorization: `Bearer ${v2Token}`};

        // Wait for the referrer to appear
        await expect
          .poll(
            async () => {
              const r = await request.get(url, {headers});
              expect(r.status()).toBe(200);
              const body = await r.json();
              return body.manifests.length;
            },
            {
              message: 'Waiting for referrer to appear in index',
              timeout: 10_000,
              intervals: [500, 1_000, 2_000],
            },
          )
          .toBe(1);

        // Second call exercises the cache hit path; response must be identical
        const cached = await request.get(url, {headers});
        expect(cached.status()).toBe(200);
        const cachedBody = await cached.json();
        expect(cachedBody.manifests).toHaveLength(1);
        expect(cachedBody.manifests[0].artifactType).toBe(
          'application/spdx+json',
        );
      } finally {
        await request.dispose();
      }
    });
  },
);
