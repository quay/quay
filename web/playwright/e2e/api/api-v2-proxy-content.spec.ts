/*
 * v2 registry tests for proxied organizations
 */

import {test, expect, uniqueName, skipUnlessFeature} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {getV2Token} from '../../utils/api/auth';
import {API_URL} from '../../utils/config';
import {proxyOptionFromEnv} from '../../utils/proxy';

// Standalone APIRequestContexts don't inherit `use.proxy`; set it explicitly so
// registry calls work when Quay is reachable only via a proxy. undefined locally.
const REQUEST_PROXY = proxyOptionFromEnv();

test.describe(
  'V2 registry tests for proxied organizations',
  {
    tag: [
      '@api',
      '@v2',
      '@container',
      '@auth:Database',
      '@feature:PROXY_CACHE',
    ],
  },
  // gunicorn-blobstream only runs when the proxy cache feature is turned on. The tag
  // @feature:PROXY_CACHE skips the test otherwise.
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

    test.beforeAll(
      async ({userContext, cachedContainerAvailable, cachedQuayConfig}) => {
        // @feature flag is applied per test so gate tests if the feature is not available
        test.skip(...skipUnlessFeature(cachedQuayConfig, 'PROXY_CACHE'));

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
      },
    );

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
        ...(REQUEST_PROXY ? {proxy: REQUEST_PROXY} : {}),
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
        ...(REQUEST_PROXY ? {proxy: REQUEST_PROXY} : {}),
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

        // Verify content-length header when present. Some environments (e.g. Prow
        // aws-s3 with OpenShift routing) omit this header on redirected S3 blob
        // responses; content delivery correctness is already verified above via
        // blobData.length. See: https://github.com/quay/quay/issues/7608
        const blobHeaderResponse = await blobRequest.headers();
        if ('content-length' in blobHeaderResponse) {
          expect(parseInt(blobHeaderResponse['content-length'])).toBe(blobSize);
        }
      } finally {
        await request.dispose();
      }
    });

    test('concurrent first pulls of different tags from a new upstream repo must all succeed', async ({
      playwright,
      userContext,
    }) => {
      // using a completely different repository here to not clash with previous tests
      const upstreamRepo = 'prometheus/node-exporter';
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
        ...(REQUEST_PROXY ? {proxy: REQUEST_PROXY} : {}),
      });

      try {
        // check upstream tags
        const upstream = await request.get(
          `https://quay.io/api/v1/repository/${upstreamRepo}/tag/?limit=20&onlyActiveTags=true`,
          {headers: {'X-Requested-With': 'XMLHttpRequest'}},
        );

        expect(upstream.status()).toBe(200);

        // grab 6 tags
        const tagNames: string[] = [
          ...new Set<string>(
            (await upstream.json()).tags.map((t: {name: string}) => t.name),
          ),
        ].slice(0, 6);
        expect(tagNames.length).toBeGreaterThan(1);

        // generate token
        const tokenFor = () =>
          getV2Token(
            request,
            API_URL,
            USERNAME,
            PASSWORD,
            `repository:${orgName}/${upstreamRepo}:pull`,
          );

        // generate headers
        const headers = {
          accept: [
            'application/vnd.docker.distribution.manifest.v2+json',
            'application/vnd.docker.distribution.manifest.list.v2+json',
            'application/vnd.oci.image.index.v1+json',
            'application/vnd.oci.image.manifest.v1+json',
          ].join(', '),
        };

        // no tags exist locally and neither does the repository, so every request
        // actually races to create the repo
        const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
        const responses = await Promise.all(
          tagNames.map(async (tag) => {
            const v2Token = await tokenFor();
            return request.get(
              `${API_URL}/v2/${orgName}/${upstreamRepo}/manifests/${tag}`,
              {headers: {...headers, authorization: `Bearer ${v2Token}`}},
            );
          }),
        );

        expect(responses.map((r) => r.status())).toEqual(
          tagNames.map(() => 200),
        );

        // every tag now has to be locally stored
        const tagResponse = await userContext.request.get(
          `${API_URL}/api/v1/repository/${orgName}/${upstreamRepo}/tag/?onlyActiveTags=true&limit=100`,
          {headers: {'X-Requested-With': 'XMLHttpRequest'}},
        );
        expect(tagResponse.status()).toBe(200);

        // map locally available tags to upstream tags
        const localTags: string[] = (await tagResponse.json()).tags.map(
          (t: {name: string}) => t.name,
        );
        expect(localTags).toEqual(expect.arrayContaining(tagNames));
      } finally {
        await request.dispose();
      }
    });
  },
);
