/**
 * Storage proxy URL binding (FEATURE_PROXY_STORAGE).
 *
 * With proxy storage on, a blob GET redirects to
 *   /_storage_proxy/<b64 jwt>/<scheme>/<host>/<object path>?<presigned query>
 * and nginx serves it only when /_storage_proxy_auth
 * (storage/downloadproxy.py) finds the scheme, host and path signed in the
 * JWT equal to the requested ones; any mismatch is a 401.
 *
 * Requires object storage that hands out direct download URLs (e.g. the
 * Garage georep setup) and crane for the push.
 */

import {createHash} from 'crypto';

import {expect, test} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {getV2Token} from '../../utils/api/auth';
import {isCraneAvailable, pushUniqueImage} from '../../utils/container';
import {API_URL} from '../../utils/config';

function sha256Digest(body: Buffer): string {
  return `sha256:${createHash('sha256').update(body).digest('hex')}`;
}

// ['', '_storage_proxy', token, scheme, host, ...object path] + query
function splitProxyUrl(location: string) {
  const url = new URL(location);
  const segments = url.pathname.split('/');
  expect(segments[1], `not a storage proxy URL: ${location}`).toBe(
    '_storage_proxy',
  );
  return {
    origin: url.origin,
    token: segments[2],
    scheme: segments[3],
    host: segments[4],
    object: segments.slice(5).join('/') + url.search,
  };
}

test.describe(
  'Storage proxy URL binding',
  {tag: ['@api', '@v2', '@container', '@storage', '@feature:PROXY_STORAGE']},
  () => {
    test.beforeAll(async () => {
      test.skip(
        !(await isCraneAvailable()),
        'crane CLI required for image push',
      );
    });

    test('a proxy URL is refused for any object or host but its own', async ({
      api,
      authenticatedRequest,
      request,
    }) => {
      const {username, password} = TEST_USERS.user;
      const org = await api.organization();
      const repo = await api.repository(org.name);
      const repoPath = `${org.name}/${repo.name}`;
      await pushUniqueImage(org.name, repo.name, 'v1', username, password);

      const token = await getV2Token(
        authenticatedRequest,
        API_URL,
        username,
        password,
        `repository:${repoPath}:pull`,
      );
      const manifestResp = await authenticatedRequest.get(
        `${API_URL}/v2/${repoPath}/manifests/v1`,
        {
          headers: {
            Accept: 'application/vnd.docker.distribution.manifest.v2+json',
            Authorization: `Bearer ${token}`,
          },
        },
      );
      expect(manifestResp.ok()).toBe(true);
      const manifest = await manifestResp.json();
      // Config and the unique layer: two distinct blobs.
      const digestA: string = manifest.config.digest;
      const digestB: string =
        manifest.layers[manifest.layers.length - 1].digest;
      expect(digestA).not.toBe(digestB);

      const proxyUrlFor = async (digest: string) => {
        const resp = await authenticatedRequest.get(
          `${API_URL}/v2/${repoPath}/blobs/${digest}`,
          {headers: {Authorization: `Bearer ${token}`}, maxRedirects: 0},
        );
        expect(resp.status(), `blob ${digest} must redirect`).toBe(302);
        return resp.headers()['location'];
      };
      const urlA = await proxyUrlFor(digestA);
      const urlB = await proxyUrlFor(digestB);

      // As minted, each URL serves its own blob, so the object path and
      // presigned query of B are valid on their own.
      for (const [url, digest] of [
        [urlA, digestA],
        [urlB, digestB],
      ]) {
        const resp = await request.get(url);
        expect(resp.status(), `minted proxy URL for ${digest}`).toBe(200);
        expect(sha256Digest(await resp.body())).toBe(digest);
      }

      const a = splitProxyUrl(urlA);
      const b = splitProxyUrl(urlB);
      expect(a.object).not.toBe(b.object);

      // A's token on B's object path.
      const swapped = await request.get(
        `${a.origin}/_storage_proxy/${a.token}/${b.scheme}/${b.host}/${b.object}`,
      );
      expect(swapped.status(), "A's token on B's object").toBe(401);

      // A's token and object on another storage host.
      const rehosted = await request.get(
        `${a.origin}/_storage_proxy/${a.token}/${a.scheme}/storage.invalid/${a.object}`,
      );
      expect(rehosted.status(), "A's token on another host").toBe(401);
    });
  },
);
