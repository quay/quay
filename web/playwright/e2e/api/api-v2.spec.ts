/**
 * V2 Registry API tests.
 *
 * Ported from Cypress: quay_api_v2_testing.cy.js
 *
 * Covers the Docker V2 registry endpoints:
 *   - Tag listing
 *   - Manifest retrieval (by tag and digest)
 *   - Referrers listing (OCI 1.1)
 *   - Catalog listing
 *   - Manifest deletion (by digest and tag)
 *
 * All tests use a raw Playwright request context (no CSRF) and
 * authenticate via V2 bearer tokens.
 */

import path from 'path';
import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {getV2Token} from '../../utils/api/auth';
import {pushImage, orasAttach, isOrasAvailable} from '../../utils/container';
import {API_URL} from '../../utils/config';

const DOCKER_MANIFEST_V2 =
  'application/vnd.docker.distribution.manifest.v2+json';

test.describe(
  'V2 Registry API',
  {tag: ['@api', '@v2', '@container', '@auth:Database']},
  () => {
    const username = TEST_USERS.user.username;
    const password = TEST_USERS.user.password;

    // Shared state across serial tests
    let orgName: string;
    let repoName: string;
    let manifestDigest: string;

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      // Skip setup if no container runtime (tests auto-skip via @container tag)
      if (!cachedContainerAvailable) return;

      const api = new ApiClient(userContext.request);

      orgName = uniqueName('v2org');
      repoName = uniqueName('v2repo');

      // Create organization
      await api.createOrganization(orgName, `${orgName}@example.com`);

      // Create repository
      await api.createRepository(orgName, repoName, 'public');

      // Push a test image so tags/manifests exist
      await pushImage(orgName, repoName, 'latest', username, password);

      // Fetch the manifest digest up-front so all tests can use it
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
            Accept: DOCKER_MANIFEST_V2,
          },
        },
      );
      if (r.ok()) {
        manifestDigest = r.headers()['docker-content-digest'];
      }
    });

    test.afterAll(async ({userContext, cachedContainerAvailable}) => {
      if (!cachedContainerAvailable || !orgName) return;

      const api = new ApiClient(userContext.request);
      try {
        await api.deleteRepository(orgName, repoName);
      } catch {
        /* ignore cleanup errors */
      }
      try {
        await api.deleteOrganization(orgName);
      } catch {
        /* ignore cleanup errors */
      }
    });

    test('list tags of image repository', async ({playwright}) => {
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

        const r = await request.get(
          `${API_URL}/v2/${orgName}/${repoName}/tags/list`,
          {headers: {authorization: `Bearer ${v2Token}`}},
        );
        expect(r.status()).toBe(200);

        const body = await r.json();
        expect(body.tags).toContain('latest');
      } finally {
        await request.dispose();
      }
    });

    test('get manifest by tag name', async ({playwright}) => {
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

        const r = await request.get(
          `${API_URL}/v2/${orgName}/${repoName}/manifests/latest`,
          {
            headers: {
              authorization: `Bearer ${v2Token}`,
              Accept: DOCKER_MANIFEST_V2,
            },
          },
        );
        expect(r.status()).toBe(200);

        const body = await r.json();
        expect(body.layers).toBeTruthy();

        const digest = r.headers()['docker-content-digest'];
        expect(digest).toBeTruthy();
      } finally {
        await request.dispose();
      }
    });

    test('get manifest by digest', async ({playwright}) => {
      expect(manifestDigest).toBeTruthy();

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

        const r = await request.get(
          `${API_URL}/v2/${orgName}/${repoName}/manifests/${manifestDigest}`,
          {
            headers: {
              authorization: `Bearer ${v2Token}`,
              Accept: DOCKER_MANIFEST_V2,
            },
          },
        );
        expect(r.status()).toBe(200);

        const body = await r.json();
        expect(body.layers).toBeTruthy();
      } finally {
        await request.dispose();
      }
    });

    test('list referrers for manifest', async ({playwright}) => {
      expect(manifestDigest).toBeTruthy();

      const orasAvailable = await isOrasAvailable();
      test.skip(!orasAvailable, 'oras CLI required for referrer tests');

      const fixturesDir = path.resolve(__dirname, '../../fixtures/oras');

      // Attach three different artifact types
      orasAttach(
        orgName,
        repoName,
        'latest',
        username,
        password,
        'application/spdx+json',
        'producer=syft 0.63.0',
        path.join(fixturesDir, 'referrer.spdx.json'),
      );

      orasAttach(
        orgName,
        repoName,
        'latest',
        username,
        password,
        'text/spdx',
        'producer=syft 0.63.0',
        path.join(fixturesDir, 'referrer.spdx.md'),
      );

      orasAttach(
        orgName,
        repoName,
        'latest',
        username,
        password,
        'application/vnd.cyclonedx+json',
        'producer=syft 0.63.0',
        path.join(fixturesDir, 'referrer.cyclonedx.json'),
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

        const r = await request.get(
          `${API_URL}/v2/${orgName}/${repoName}/referrers/${manifestDigest}`,
          {headers: {authorization: `Bearer ${v2Token}`}},
        );
        expect(r.status()).toBe(200);

        const body = await r.json();
        expect(body.manifests).toHaveLength(3);
      } finally {
        await request.dispose();
      }
    });

    test('get catalog', async ({playwright}) => {
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

        const r = await request.get(`${API_URL}/v2/_catalog`, {
          headers: {authorization: `Bearer ${v2Token}`},
        });
        expect(r.status()).toBe(200);

        const body = await r.json();
        expect(body.repositories).toContain(`${orgName}/${repoName}`);
      } finally {
        await request.dispose();
      }
    });

    test('referrers with invalid digest returns 400 MANIFEST_INVALID', async ({
      playwright,
    }) => {
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

        const badDigest =
          'sha256:5403064f94b617f7975a19ba4d1a1299fd584397f6ee4393d0e16744ed11aab3';
        const r = await request.get(
          `${API_URL}/v2/${orgName}/${repoName}/referrers/${badDigest}`,
          {
            headers: {authorization: `Bearer ${v2Token}`},
          },
        );
        expect(r.status()).toBe(400);

        const body = await r.json();
        expect(body.errors[0].code).toBe('MANIFEST_INVALID');
      } finally {
        await request.dispose();
      }
    });

    test('delete manifest by digest', async ({playwright}) => {
      expect(manifestDigest).toBeTruthy();

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

        const r = await request.delete(
          `${API_URL}/v2/${orgName}/${repoName}/manifests/${manifestDigest}`,
          {
            headers: {
              authorization: `Bearer ${v2Token}`,
              Accept: DOCKER_MANIFEST_V2,
            },
          },
        );
        expect(r.status()).toBe(202);
      } finally {
        await request.dispose();
      }
    });

    test('delete manifest by tag name', async ({playwright}) => {
      // Push a new image with a different tag for this deletion test
      await pushImage(orgName, repoName, 'python3', username, password);

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

        const r = await request.delete(
          `${API_URL}/v2/${orgName}/${repoName}/manifests/python3`,
          {
            headers: {
              authorization: `Bearer ${v2Token}`,
              Accept: DOCKER_MANIFEST_V2,
            },
          },
        );
        expect(r.status()).toBe(202);
      } finally {
        await request.dispose();
      }
    });
  },
);
