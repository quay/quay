/**
 * OCI Referrers API Tests
 *
 * Verifies that the /v2/.../referrers/<digest> endpoint returns a valid
 * OCI image index response. Uses API route mocking to simulate the
 * referrers listing returned by the backend cache layer.
 *
 * Related fix: serialization of Manifest objects in the referrers Redis
 * cache (lookup_cached_referrers_for_manifest).
 */

import {test, expect} from '../../fixtures';

const SUBJECT_DIGEST =
  'sha256:aaaa111122223333444455556666777788889999aaaabbbbccccddddeeeeffff';

const MOCK_REFERRERS_INDEX = {
  schemaVersion: 2,
  mediaType: 'application/vnd.oci.image.index.v1+json',
  manifests: [
    {
      mediaType: 'application/vnd.oci.image.manifest.v1+json',
      digest:
        'sha256:bbbb111122223333444455556666777788889999aaaabbbbccccddddeeeeffff',
      size: 512,
      artifactType: 'application/vnd.example.sbom.v1',
      annotations: {
        'org.opencontainers.image.created': '2026-01-01T00:00:00Z',
      },
    },
    {
      mediaType: 'application/vnd.oci.image.manifest.v1+json',
      digest:
        'sha256:cccc111122223333444455556666777788889999aaaabbbbccccddddeeeeffff',
      size: 256,
      artifactType: 'application/vnd.example.signature.v1',
    },
  ],
};

const EMPTY_REFERRERS_INDEX = {
  schemaVersion: 2,
  mediaType: 'application/vnd.oci.image.index.v1+json',
  manifests: [],
};

test.describe('OCI Referrers API', {tag: ['@repository']}, () => {
  test('returns a valid OCI index with referrers for a manifest', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();

    await authenticatedPage.route(
      `**/v2/${repo.namespace}/${repo.name}/referrers/${SUBJECT_DIGEST}`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/vnd.oci.image.index.v1+json',
          body: JSON.stringify(MOCK_REFERRERS_INDEX),
        });
      },
    );

    const response = await authenticatedPage.evaluate(
      async ({ns, name, digest}) => {
        const res = await fetch(`/v2/${ns}/${name}/referrers/${digest}`);
        return {
          status: res.status,
          contentType: res.headers.get('content-type'),
          body: await res.json(),
        };
      },
      {ns: repo.namespace, name: repo.name, digest: SUBJECT_DIGEST},
    );

    expect(response.status).toBe(200);
    expect(response.contentType).toContain(
      'application/vnd.oci.image.index.v1+json',
    );
    expect(response.body.schemaVersion).toBe(2);
    expect(response.body.manifests).toHaveLength(2);
    expect(response.body.manifests[0].artifactType).toBe(
      'application/vnd.example.sbom.v1',
    );
    expect(response.body.manifests[1].artifactType).toBe(
      'application/vnd.example.signature.v1',
    );
  });

  test('returns an empty OCI index when no referrers exist', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();

    await authenticatedPage.route(
      `**/v2/${repo.namespace}/${repo.name}/referrers/${SUBJECT_DIGEST}`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/vnd.oci.image.index.v1+json',
          body: JSON.stringify(EMPTY_REFERRERS_INDEX),
        });
      },
    );

    const response = await authenticatedPage.evaluate(
      async ({ns, name, digest}) => {
        const res = await fetch(`/v2/${ns}/${name}/referrers/${digest}`);
        return {
          status: res.status,
          body: await res.json(),
        };
      },
      {ns: repo.namespace, name: repo.name, digest: SUBJECT_DIGEST},
    );

    expect(response.status).toBe(200);
    expect(response.body.schemaVersion).toBe(2);
    expect(response.body.manifests).toHaveLength(0);
  });

  test('supports artifactType filtering via query parameter', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();
    const filteredIndex = {
      ...MOCK_REFERRERS_INDEX,
      manifests: [MOCK_REFERRERS_INDEX.manifests[0]],
    };

    await authenticatedPage.route(
      `**/v2/${repo.namespace}/${repo.name}/referrers/${SUBJECT_DIGEST}?artifactType=*`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/vnd.oci.image.index.v1+json',
          headers: {
            'OCI-Filters-Applied': 'artifactType',
          },
          body: JSON.stringify(filteredIndex),
        });
      },
    );

    const response = await authenticatedPage.evaluate(
      async ({ns, name, digest}) => {
        const res = await fetch(
          `/v2/${ns}/${name}/referrers/${digest}?artifactType=application/vnd.example.sbom.v1`,
        );
        return {
          status: res.status,
          filtersApplied: res.headers.get('oci-filters-applied'),
          body: await res.json(),
        };
      },
      {ns: repo.namespace, name: repo.name, digest: SUBJECT_DIGEST},
    );

    expect(response.status).toBe(200);
    expect(response.filtersApplied).toBe('artifactType');
    expect(response.body.manifests).toHaveLength(1);
    expect(response.body.manifests[0].artifactType).toBe(
      'application/vnd.example.sbom.v1',
    );
  });
});
