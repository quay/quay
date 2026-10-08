/*
 * v2 registry tests for proxied organizations
 */

import {test, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {getV2Token} from '../../utils/api/auth';
import {API_URL} from '../../utils/config';

test.describe(
  'V2 registry tests for proxied organizations',
  {tag: ['@api', '@v2', '@container', '@auth:Database']},
  () => {
    // Tests share same state (orgName, repoName, manifestDigest) and must
    // run sequentially.
    test.describe.configure({mode: 'serial'});

    const USERNAME = TEST_USERS.user.username;
    const PASSWORD = TEST_USERS.user.password;

    // shared state across all tests
    let orgName: string;
    let repoName: string;

    // blob information
    let blobDigest: string;
    let blobSize: number;

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      // skip setup if registry tooling is unavailable
      if (!cachedContainerAvailable) return;

      const api = new ApiClient(userContext.request);
      orgName = uniqueName('proxycache');

      // create organization
      await api.createOrganization(orgName, `${orgName}@example.com`);

      // create proxy organization
      await api.createProxyCacheConfig(orgName, {
        upstream_registry: 'quay.io',
        expiration_s: 3600,
        insecure: false,
      });
    });

    // cleanup
    test.afterAll(async ({userContext, cachedContainerAvailable}) => {
      if (!cachedContainerAvailable || !orgName) return;
      const api = new ApiClient(userContext.request);
      try {
        await api.deleteOrganization(orgName);
      } catch {
        /* ignore all API errors here */
      }
    });

    test('Test pull through proxy cache', async ({playwright}) => {
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      repoName = 'prometheus/busybox';

      try {
        const scope = `repository:${orgName}/${repoName}:push,pull`;
        const v2Token = await getV2Token(
          request,
          API_URL,
          USERNAME,
          PASSWORD,
          scope,
        );

        const tag = 'latest';

        // construct headers
        const headers = {
          authorization: `Bearer ${v2Token}`,
          accept: [
            `application/vnd.docker.distribution.manifest.v2+json`,
            `application/vnd.docker.distribution.manifest.list.v2+json`,
          ].join(', '),
        };

        // issue a GET manifest request
        const manifestPath = `${API_URL}/v2/${orgName}/${repoName}/manifests`;
        const blobPath = `${API_URL}/v2/${orgName}/${repoName}/blobs`;
        const r = await request.get(`${manifestPath}/${tag}`, {headers});

        expect(r.status()).toBe(200);
        const body = await r.json();

        // check if returned image is a manifest list
        if (body.manifests) {
          // got a manifest list so fetch platform specific digest
          const platformDigest = body.manifests[0].digest;
          const platformR = await request.get(
            `${manifestPath}/${platformDigest}`,
            {headers},
          );
          const platformBody = await platformR.json();
          blobDigest = platformBody.layers[0].digest;
          blobSize = platformBody.layers[0].size;
        } else {
          blobDigest = body.layers[0].digest;
          blobSize = body.layers[0].size;
        }

        // issue a blob fetch request (follows redirects) and verify the full blob is returned
        const blobRequest = await request.get(`${blobPath}/${blobDigest}`, {
          headers,
        });
        expect(blobRequest.status()).toBe(200);

        // verify that the amount of data provided is the same as the blob size
        const blobData = await blobRequest.body();
        expect(blobData.length).toBe(blobSize);
      } finally {
        await request.dispose();
      }
    });

    // Known limitation: it's currently difficult to verify that the 2nd pull is not coming from upstream
    // as blobs are shared across multiple tests and may already be saved in the backend (storage is content
    // addressable and there's only one blob and one ImageStorage entry per blob). Therefore, we just verify
    // that the blob can be pulled properly the 2nd time, with no errors raised.
    //
    // An improvement would be to add a full lifecycle:
    // 1. clean up the entire registry so that no blobs are stored locally
    // 2. create a completely new organization and proxy configuration
    // 3. pull the image from upstream to verify it contains _upstream_proxy in the Location header
    // 4. verify blob content (blob SHA and size)
    // 5. repeat the process verifying that there is no _upstream_proxy in the Location header
    // 6. verify blob content (blob SHA and size)
    test('second pull returns 200 with the correct content', async ({
      playwright,
      userContext,
    }) => {
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });

      try {
        const scope = `repository:${orgName}/${repoName}:push,pull`;
        const v2Token = await getV2Token(
          request,
          API_URL,
          USERNAME,
          PASSWORD,
          scope,
        );

        // construct headers
        const headers = {
          authorization: `Bearer ${v2Token}`,
        };

        // blob should be served from local storage
        // first, verify that the tag we previously pulled exists
        const tagResponse = await userContext.request.get(
          `${API_URL}/api/v1/repository/${orgName}/${repoName}/tag/?specificTag=latest&onlyActiveTags=true`,
        );

        expect(tagResponse.status()).toBe(200);
        const tagBody = await tagResponse.json();
        expect(tagBody.tags.length).toBeGreaterThan(0);

        // pull blob immediately
        const blobPath = `${API_URL}/v2/${orgName}/${repoName}/blobs`;
        const blobRequest = await request.get(`${blobPath}/${blobDigest}`, {
          headers,
        });
        expect(blobRequest.status()).toBe(200);

        // verify that the amount of data provided is the same as the blob size
        const blobData = await blobRequest.body();
        expect(blobData.length).toBe(blobSize);

        // When Quay serves the blob directly (no S3 direct-download), it
        // sets Content-Length explicitly. When Quay redirects to S3 (as in
        // Prow aws-s3 runs), the final response comes from S3 and the header
        // may be absent (e.g. chunked encoding or OpenShift ingress stripping).
        // Content delivery correctness is already verified above via blobData.length,
        // so only assert the header value when the header is actually present.
        const blobHeaderResponse = await blobRequest.headers();
        const contentLengthHeader = blobHeaderResponse['content-length'];
        if (contentLengthHeader !== undefined) {
          expect(parseInt(contentLengthHeader)).toBe(blobSize);
        }
      } finally {
        await request.dispose();
      }
    });
  },
);
