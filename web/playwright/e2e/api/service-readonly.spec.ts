import type {APIRequestContext, APIResponse} from '@playwright/test';
import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

const DEFAULT_PUBLIC_REPOSITORY = 'quay-qetest/alpine';
const DEFAULT_PUBLIC_TAG = 'latest';
const MANIFEST_ACCEPT = [
  'application/vnd.docker.distribution.manifest.v2+json',
  'application/vnd.docker.distribution.manifest.list.v2+json',
  'application/vnd.oci.image.manifest.v1+json',
  'application/vnd.oci.image.index.v1+json',
].join(', ');

type QuayTag = {
  name: string;
};

function getPublicRepository(): string {
  return (
    process.env.QUAY_E2E_PUBLIC_REPOSITORY || DEFAULT_PUBLIC_REPOSITORY
  ).replace(/^https?:\/\/[^/]+\//, '');
}

function getPublicTag(): string {
  return process.env.QUAY_E2E_PUBLIC_TAG || DEFAULT_PUBLIC_TAG;
}

async function expectStatus(
  response: APIResponse,
  expectedStatus: number,
  label: string,
): Promise<void> {
  if (response.status() === expectedStatus) return;

  throw new Error(
    `${label} returned ${response.status()} instead of ${expectedStatus}: ${await response.text()}`,
  );
}

async function getAnonymousV2Token(
  request: APIRequestContext,
  repository: string,
): Promise<string> {
  const params = new URLSearchParams({
    service: new URL(API_URL).host,
    scope: `repository:${repository}:pull`,
  });
  const response = await request.get(`${API_URL}/v2/auth?${params.toString()}`);
  await expectStatus(response, 200, 'Anonymous v2 auth');

  const body = (await response.json()) as {token?: string};
  if (!body.token) {
    throw new Error('Anonymous v2 auth did not return a token');
  }

  return body.token;
}

test.describe(
  'Service read-only APIs',
  {tag: ['@api', '@service-safe']},
  () => {
    test('health and discovery endpoints are readable', async ({request}) => {
      for (const endpoint of [
        '/health/instance',
        '/health/endtoend',
        '/health/warning',
      ]) {
        const response = await request.get(`${API_URL}${endpoint}`);
        await expectStatus(response, 200, endpoint);
        const body = await response.json();
        expect(body.status_code).toBe(200);
        expect(body.data?.services).toBeTruthy();
      }

      const discoveryResponse = await request.get(
        `${API_URL}/api/v1/discovery`,
      );
      await expectStatus(discoveryResponse, 200, '/api/v1/discovery');
      const discovery = await discoveryResponse.json();
      expect(Object.keys(discovery).length).toBeGreaterThan(0);
    });

    test('registry v2 endpoint is reachable', async ({request}) => {
      const response = await request.get(`${API_URL}/v2/`);

      expect([200, 401]).toContain(response.status());
      if (response.status() === 401) {
        expect(response.headers()['www-authenticate']).toContain('/v2/auth');
      }
    });
  },
);

test.describe(
  'Service public repository reads',
  {tag: ['@api', '@service-integration']},
  () => {
    test('public repository is readable through registry v2', async ({
      request,
    }) => {
      const repository = getPublicRepository();
      const preferredTag = getPublicTag();
      const token = await getAnonymousV2Token(request, repository);
      const authHeaders = {authorization: `Bearer ${token}`};
      const v2TagsResponse = await request.get(
        `${API_URL}/v2/${repository}/tags/list`,
        {headers: authHeaders},
      );
      await expectStatus(v2TagsResponse, 200, `/v2/${repository}/tags/list`);
      const v2TagsBody = (await v2TagsResponse.json()) as {tags?: string[]};
      const tags = (v2TagsBody.tags || []).map((name) => ({name}));
      const tag =
        tags.find((candidate) => candidate.name === preferredTag) || tags[0];

      if (!tag?.name) {
        throw new Error(
          `${repository} did not expose readable tags (set QUAY_E2E_PUBLIC_REPOSITORY if this target uses a different public repo)`,
        );
      }

      const v2ManifestResponse = await request.get(
        `${API_URL}/v2/${repository}/manifests/${tag.name}`,
        {
          headers: {
            ...authHeaders,
            Accept: MANIFEST_ACCEPT,
          },
        },
      );
      await expectStatus(
        v2ManifestResponse,
        200,
        `/v2/${repository}/manifests/${tag.name}`,
      );
      expect(
        v2ManifestResponse.headers()['docker-content-digest'],
      ).toBeTruthy();
    });
  },
);
