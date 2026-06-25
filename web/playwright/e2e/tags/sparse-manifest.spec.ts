/**
 * Sparse Manifest Visualization Tests (PROJQUAY-10261)
 *
 * Tests the UI indicators for sparse manifest lists - manifest lists where
 * some child manifests are not present locally (typically from pull-through proxy).
 *
 * Uses complete API mocking to simulate sparse manifest responses since creating
 * actual sparse manifests requires database-level manipulation.
 */

import {test, expect} from '../../fixtures';

// Mock data for a sparse manifest list
const MOCK_MANIFEST_DIGEST =
  'sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef';
const MOCK_CHILD_DIGEST_1 =
  'sha256:aaaa111122223333444455556666777788889999aaaabbbbccccddddeeeeffff';
const MOCK_CHILD_DIGEST_2 =
  'sha256:bbbb111122223333444455556666777788889999aaaabbbbccccddddeeeeffff';

function createMockTagsResponse(options: {
  tagName: string;
  isSparse: boolean;
  presentCount: number;
  totalCount: number;
}) {
  const childManifestsPresence: Record<string, boolean> = {};
  childManifestsPresence[MOCK_CHILD_DIGEST_1] = true;
  childManifestsPresence[MOCK_CHILD_DIGEST_2] = false;

  return {
    tags: [
      {
        name: options.tagName,
        manifest_digest: MOCK_MANIFEST_DIGEST,
        is_manifest_list: true,
        size: 2048,
        last_modified: new Date().toISOString(),
        reversion: false,
        start_ts: Math.floor(Date.now() / 1000),
        is_sparse: options.isSparse,
        child_manifest_count: options.totalCount,
        present_child_count: options.presentCount,
        child_manifests_presence: options.isSparse
          ? childManifestsPresence
          : undefined,
      },
    ],
    page: 1,
    has_additional: false,
  };
}

function createMockManifestResponse(options: {
  childDigests: Array<{
    digest: string;
    os: string;
    architecture: string;
  }>;
}) {
  return {
    digest: MOCK_MANIFEST_DIGEST,
    is_manifest_list: true,
    manifest_data: JSON.stringify({
      schemaVersion: 2,
      mediaType: 'application/vnd.docker.distribution.manifest.list.v2+json',
      manifests: options.childDigests.map((child) => ({
        digest: child.digest,
        mediaType: 'application/vnd.docker.distribution.manifest.v2+json',
        size: 1024,
        platform: {
          os: child.os,
          architecture: child.architecture,
        },
      })),
    }),
  };
}

test.describe('Sparse Manifest Visualization', {tag: ['@tags']}, () => {
  test('shows sparse label for sparse manifest list in tags table', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();

    // Mock tag API to return a sparse manifest
    await authenticatedPage.route(
      `**/api/v1/repository/${repo.namespace}/${repo.name}/tag/**`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            createMockTagsResponse({
              tagName: 'multiarch',
              isSparse: true,
              presentCount: 1,
              totalCount: 3,
            }),
          ),
        });
      },
    );

    // Mock manifest endpoint
    await authenticatedPage.route(
      `**/api/v1/repository/${repo.namespace}/${repo.name}/manifest/**`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            createMockManifestResponse({
              childDigests: [
                {
                  digest: MOCK_CHILD_DIGEST_1,
                  os: 'linux',
                  architecture: 'amd64',
                },
                {
                  digest: MOCK_CHILD_DIGEST_2,
                  os: 'linux',
                  architecture: 'arm64',
                },
              ],
            }),
          ),
        });
      },
    );

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

    // Wait for tags to load
    await expect(
      authenticatedPage.getByRole('link', {name: 'multiarch'}),
    ).toBeVisible();

    // Verify sparse label is displayed
    const sparseLabel = authenticatedPage.getByTestId('sparse-manifest-label');
    await expect(sparseLabel).toBeVisible();
    await expect(sparseLabel).toHaveText('Sparse (1/3)');
  });

  test('shows missing label for missing child manifests in expanded view', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();

    // Mock tag API to return a sparse manifest with child_manifests_presence
    await authenticatedPage.route(
      `**/api/v1/repository/${repo.namespace}/${repo.name}/tag/**`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            createMockTagsResponse({
              tagName: 'multiarch',
              isSparse: true,
              presentCount: 1,
              totalCount: 2,
            }),
          ),
        });
      },
    );

    // Mock manifest endpoint
    await authenticatedPage.route(
      `**/api/v1/repository/${repo.namespace}/${repo.name}/manifest/**`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            createMockManifestResponse({
              childDigests: [
                {
                  digest: MOCK_CHILD_DIGEST_1,
                  os: 'linux',
                  architecture: 'amd64',
                },
                {
                  digest: MOCK_CHILD_DIGEST_2,
                  os: 'linux',
                  architecture: 'arm64',
                },
              ],
            }),
          ),
        });
      },
    );

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

    // Wait for tags to load
    await expect(
      authenticatedPage.getByRole('link', {name: 'multiarch'}),
    ).toBeVisible();

    // Find the row with multiarch tag and click the expand toggle
    const tagRow = authenticatedPage.getByTestId('table-entry').filter({
      has: authenticatedPage.getByRole('link', {name: 'multiarch'}),
    });

    // The expand button in PatternFly table is a button within the first Td
    const expandButton = tagRow.locator('button').first();
    await expect(expandButton).toBeVisible({timeout: 10000});
    await expandButton.click();

    // Wait for child rows to appear and check for missing label
    const missingLabel = authenticatedPage.getByTestId(
      'missing-manifest-label',
    );
    await expect(missingLabel.first()).toBeVisible({timeout: 10000});
    await expect(missingLabel.first()).toHaveText('Missing');
  });

  test('shows sparse alert banner on tag details page', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();

    // Mock tag endpoint to return a sparse manifest
    await authenticatedPage.route(
      `**/api/v1/repository/${repo.namespace}/${repo.name}/tag/**`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            createMockTagsResponse({
              tagName: 'multiarch',
              isSparse: true,
              presentCount: 1,
              totalCount: 2,
            }),
          ),
        });
      },
    );

    // Mock manifest endpoint
    await authenticatedPage.route(
      `**/api/v1/repository/${repo.namespace}/${repo.name}/manifest/**`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            createMockManifestResponse({
              childDigests: [
                {
                  digest: MOCK_CHILD_DIGEST_1,
                  os: 'linux',
                  architecture: 'amd64',
                },
                {
                  digest: MOCK_CHILD_DIGEST_2,
                  os: 'linux',
                  architecture: 'arm64',
                },
              ],
            }),
          ),
        });
      },
    );

    await authenticatedPage.goto(`/repository/${repo.fullName}/tag/multiarch`);

    // Wait for page to load
    await expect(
      authenticatedPage.getByRole('heading', {
        level: 1,
        name: new RegExp(`${repo.name}:multiarch`),
      }),
    ).toBeVisible();

    // Verify sparse alert banner is displayed
    const sparseAlert = authenticatedPage.getByTestId('sparse-manifest-alert');
    await expect(sparseAlert).toBeVisible();
    await expect(sparseAlert).toContainText('Sparse Manifest List');
    await expect(sparseAlert).toContainText(
      'not all architectures are present locally',
    );
  });

  test('disables missing architectures in architecture selector', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();

    // Mock tag endpoint
    await authenticatedPage.route(
      `**/api/v1/repository/${repo.namespace}/${repo.name}/tag/**`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            createMockTagsResponse({
              tagName: 'multiarch',
              isSparse: true,
              presentCount: 1,
              totalCount: 2,
            }),
          ),
        });
      },
    );

    // Mock manifest endpoint
    await authenticatedPage.route(
      `**/api/v1/repository/${repo.namespace}/${repo.name}/manifest/**`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            createMockManifestResponse({
              childDigests: [
                {
                  digest: MOCK_CHILD_DIGEST_1,
                  os: 'linux',
                  architecture: 'amd64',
                },
                {
                  digest: MOCK_CHILD_DIGEST_2,
                  os: 'linux',
                  architecture: 'arm64',
                },
              ],
            }),
          ),
        });
      },
    );

    await authenticatedPage.goto(`/repository/${repo.fullName}/tag/multiarch`);

    // Wait for page to load
    await expect(
      authenticatedPage.getByRole('heading', {
        level: 1,
        name: new RegExp(`${repo.name}:multiarch`),
      }),
    ).toBeVisible();

    // Find and click the architecture selector toggle button
    // The first architecture (linux/amd64) is present and should be auto-selected
    const archToggle = authenticatedPage.getByRole('button', {
      name: /linux on amd64/i,
    });
    await expect(archToggle).toBeVisible({timeout: 10000});
    await archToggle.click();

    // The dropdown should now be open, showing all architectures
    // The second architecture (linux/arm64) should be disabled with "Missing" label
    const missingOption = authenticatedPage.getByRole('option', {
      name: /linux on arm64.*Missing/i,
    });
    await expect(missingOption).toBeVisible({timeout: 5000});

    // Verify the option is disabled (uses the HTML disabled attribute)
    await expect(missingOption).toBeDisabled();
  });

  test('does not show sparse label for complete manifest list', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();

    // Mock tag API to return a complete (non-sparse) manifest list
    await authenticatedPage.route(
      `**/api/v1/repository/${repo.namespace}/${repo.name}/tag/**`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            createMockTagsResponse({
              tagName: 'complete',
              isSparse: false,
              presentCount: 2,
              totalCount: 2,
            }),
          ),
        });
      },
    );

    // Mock manifest endpoint
    await authenticatedPage.route(
      `**/api/v1/repository/${repo.namespace}/${repo.name}/manifest/**`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            createMockManifestResponse({
              childDigests: [
                {
                  digest: MOCK_CHILD_DIGEST_1,
                  os: 'linux',
                  architecture: 'amd64',
                },
                {
                  digest: MOCK_CHILD_DIGEST_2,
                  os: 'linux',
                  architecture: 'arm64',
                },
              ],
            }),
          ),
        });
      },
    );

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

    // Wait for tag to be visible
    await expect(
      authenticatedPage.getByRole('link', {name: 'complete'}),
    ).toBeVisible();

    // Verify sparse label is NOT displayed for complete manifest
    const sparseLabel = authenticatedPage.getByTestId('sparse-manifest-label');
    await expect(sparseLabel).not.toBeVisible();
  });

  test('shows N/A for security and size of missing architectures', async ({
    authenticatedPage,
    api,
  }) => {
    const repo = await api.repository();

    // Mock tag API
    await authenticatedPage.route(
      `**/api/v1/repository/${repo.namespace}/${repo.name}/tag/**`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            createMockTagsResponse({
              tagName: 'multiarch',
              isSparse: true,
              presentCount: 1,
              totalCount: 2,
            }),
          ),
        });
      },
    );

    // Mock manifest endpoint
    await authenticatedPage.route(
      `**/api/v1/repository/${repo.namespace}/${repo.name}/manifest/**`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(
            createMockManifestResponse({
              childDigests: [
                {
                  digest: MOCK_CHILD_DIGEST_1,
                  os: 'linux',
                  architecture: 'amd64',
                },
                {
                  digest: MOCK_CHILD_DIGEST_2,
                  os: 'linux',
                  architecture: 'arm64',
                },
              ],
            }),
          ),
        });
      },
    );

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

    // Wait for tags to load
    await expect(
      authenticatedPage.getByRole('link', {name: 'multiarch'}),
    ).toBeVisible();

    // Find the row with multiarch tag and click expand
    const tagRow = authenticatedPage.getByTestId('table-entry').filter({
      has: authenticatedPage.getByRole('link', {name: 'multiarch'}),
    });

    const expandButton = tagRow.locator('button').first();
    await expect(expandButton).toBeVisible({timeout: 10000});
    await expandButton.click();

    // Wait for expanded content and check for N/A text
    // The N/A appears for security and size columns on missing manifests
    await expect(authenticatedPage.getByText('N/A').first()).toBeVisible({
      timeout: 10000,
    });
  });
});

test.describe(
  'Sparse Manifest - Non-manifest-list tags',
  {tag: ['@tags']},
  () => {
    test('does not show sparse info for single-architecture tags', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();

      // Mock response for a non-manifest-list tag
      await authenticatedPage.route(
        `**/api/v1/repository/${repo.namespace}/${repo.name}/tag/**`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              tags: [
                {
                  name: 'single-arch',
                  is_manifest_list: false,
                  manifest_digest:
                    'sha256:abc123def456789abc123def456789abc123def456789abc123def456789abcd',
                  size: 1000,
                  last_modified: new Date().toISOString(),
                  reversion: false,
                },
              ],
              page: 1,
              has_additional: false,
            }),
          });
        },
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      // Wait for tag to be visible
      await expect(
        authenticatedPage.getByRole('link', {name: 'single-arch'}),
      ).toBeVisible();

      // Verify no sparse label is shown
      const sparseLabel = authenticatedPage.getByTestId(
        'sparse-manifest-label',
      );
      await expect(sparseLabel).not.toBeVisible();
    });
  },
);
