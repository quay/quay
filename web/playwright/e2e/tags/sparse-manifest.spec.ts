/**
 * Sparse Manifest Visualization Tests (PROJQUAY-10261)
 *
 * Tests the UI indicators for sparse manifest lists - manifest lists where
 * some child manifests are not present locally (typically from pull-through proxy).
 *
 * Uses API mocking to simulate sparse manifest responses since creating actual
 * sparse manifests requires database-level manipulation.
 */

import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushMultiArchImage} from '../../utils/container';
import {API_URL} from '../../utils/config';

test.describe(
  'Sparse Manifest Visualization',
  {tag: ['@tags', '@sparse-manifest', '@container']},
  () => {
    // Shared test data
    let testRepo: {namespace: string; name: string; fullName: string};

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      // Skip setup if no container runtime
      if (!cachedContainerAvailable) return;

      const repoName = `sparse-test-${Date.now()}`;
      testRepo = {
        namespace: TEST_USERS.user.username,
        name: repoName,
        fullName: `${TEST_USERS.user.username}/${repoName}`,
      };

      // Create the repository via API
      const csrfResponse = await userContext.request.get(
        `${API_URL}/csrf_token`,
      );
      const {csrf_token} = await csrfResponse.json();

      await userContext.request.post(`${API_URL}/api/v1/repository`, {
        headers: {'X-CSRF-Token': csrf_token},
        data: {
          namespace: testRepo.namespace,
          repository: testRepo.name,
          visibility: 'private',
          description: '',
          repo_kind: 'image',
        },
      });

      // Push a real multi-arch image
      await pushMultiArchImage(
        testRepo.namespace,
        testRepo.name,
        'multiarch',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
    });

    test.afterAll(async ({userContext}) => {
      if (!testRepo) return;

      try {
        const csrfResponse = await userContext.request.get(
          `${API_URL}/csrf_token`,
        );
        const {csrf_token} = await csrfResponse.json();

        await userContext.request.delete(
          `${API_URL}/api/v1/repository/${testRepo.namespace}/${testRepo.name}`,
          {headers: {'X-CSRF-Token': csrf_token}},
        );
      } catch {
        // Ignore cleanup errors
      }
    });

    test('shows sparse label for sparse manifest list in tags table', async ({
      authenticatedPage,
    }) => {
      // Mock the tag API to return a sparse manifest
      await authenticatedPage.route(
        `**/api/v1/repository/${testRepo.namespace}/${testRepo.name}/tag/**`,
        async (route) => {
          const response = await route.fetch();
          const json = await response.json();

          // Modify tags to be sparse
          if (json.tags) {
            json.tags = json.tags.map(
              (tag: {is_manifest_list?: boolean; name: string}) => {
                if (tag.is_manifest_list) {
                  return {
                    ...tag,
                    is_sparse: true,
                    child_manifest_count: 3,
                    present_child_count: 1,
                    child_manifests_presence: {
                      'sha256:present123': true,
                      'sha256:missing456': false,
                      'sha256:missing789': false,
                    },
                  };
                }
                return tag;
              },
            );
          }

          await route.fulfill({response, json});
        },
      );

      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);

      // Wait for tags to load
      await expect(
        authenticatedPage.getByRole('link', {name: 'multiarch'}),
      ).toBeVisible();

      // Verify sparse label is displayed
      const sparseLabel = authenticatedPage.getByTestId(
        'sparse-manifest-label',
      );
      await expect(sparseLabel).toBeVisible();
      await expect(sparseLabel).toHaveText('Sparse (1/3)');
    });

    test('shows missing label for missing child manifests in expanded view', async ({
      authenticatedPage,
    }) => {
      // Mock both tag list and manifest endpoints
      await authenticatedPage.route(
        `**/api/v1/repository/${testRepo.namespace}/${testRepo.name}/tag/**`,
        async (route) => {
          const response = await route.fetch();
          const json = await response.json();

          if (json.tags) {
            json.tags = json.tags.map(
              (tag: {is_manifest_list?: boolean; name: string}) => {
                if (tag.is_manifest_list) {
                  return {
                    ...tag,
                    is_sparse: true,
                    child_manifest_count: 2,
                    present_child_count: 1,
                    child_manifests_presence: {
                      'sha256:amd64present': true,
                      'sha256:arm64missing': false,
                    },
                  };
                }
                return tag;
              },
            );
          }

          await route.fulfill({response, json});
        },
      );

      // Mock manifest endpoint to include is_present info
      await authenticatedPage.route(
        `**/api/v1/repository/${testRepo.namespace}/${testRepo.name}/manifest/**`,
        async (route) => {
          const response = await route.fetch();
          const json = await response.json();

          // If this is a manifest list, modify child manifests
          if (json.manifest_data) {
            try {
              const manifestData = JSON.parse(json.manifest_data);
              if (manifestData.manifests) {
                manifestData.manifests = manifestData.manifests.map(
                  (
                    m: {digest: string; platform?: {architecture: string}},
                    idx: number,
                  ) => ({
                    ...m,
                    is_present: idx === 0, // First one present, rest missing
                  }),
                );
                json.manifest_data = JSON.stringify(manifestData);
              }
            } catch {
              // Not a manifest list, ignore
            }
          }

          await route.fulfill({response, json});
        },
      );

      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);

      // Wait for tags to load
      await expect(
        authenticatedPage.getByRole('link', {name: 'multiarch'}),
      ).toBeVisible();

      // Expand the manifest list row
      const expandButton = authenticatedPage
        .getByRole('row')
        .filter({
          has: authenticatedPage.getByRole('link', {name: 'multiarch'}),
        })
        .getByRole('button', {name: /expand/i})
        .first();

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
    }) => {
      // Mock tag endpoint
      await authenticatedPage.route(
        `**/api/v1/repository/${testRepo.namespace}/${testRepo.name}/tag/**`,
        async (route) => {
          const response = await route.fetch();
          const json = await response.json();

          if (json.tags) {
            json.tags = json.tags.map(
              (tag: {is_manifest_list?: boolean; name: string}) => {
                if (tag.is_manifest_list && tag.name === 'multiarch') {
                  return {
                    ...tag,
                    is_sparse: true,
                    child_manifest_count: 2,
                    present_child_count: 1,
                    child_manifests_presence: {
                      'sha256:present': true,
                      'sha256:missing': false,
                    },
                  };
                }
                return tag;
              },
            );
          }

          await route.fulfill({response, json});
        },
      );

      // Mock manifest endpoint to add is_present to child manifests
      await authenticatedPage.route(
        `**/api/v1/repository/${testRepo.namespace}/${testRepo.name}/manifest/**`,
        async (route) => {
          const response = await route.fetch();
          const json = await response.json();

          if (json.manifest_data) {
            try {
              const manifestData = JSON.parse(json.manifest_data);
              if (manifestData.manifests) {
                manifestData.manifests = manifestData.manifests.map(
                  (m: {digest: string}, idx: number) => ({
                    ...m,
                    is_present: idx === 0,
                  }),
                );
                json.manifest_data = JSON.stringify(manifestData);
              }
            } catch {
              // Ignore
            }
          }

          await route.fulfill({response, json});
        },
      );

      await authenticatedPage.goto(
        `/repository/${testRepo.fullName}/tag/multiarch`,
      );

      // Wait for page to load
      await expect(
        authenticatedPage.getByRole('heading', {
          level: 1,
          name: /multiarch/,
        }),
      ).toBeVisible();

      // Verify sparse alert banner is displayed
      const sparseAlert = authenticatedPage.getByTestId(
        'sparse-manifest-alert',
      );
      await expect(sparseAlert).toBeVisible();
      await expect(sparseAlert).toContainText('Sparse Manifest List');
      await expect(sparseAlert).toContainText(
        'not all architectures are present locally',
      );
    });

    test('disables missing architectures in architecture selector', async ({
      authenticatedPage,
    }) => {
      // Mock tag and manifest endpoints
      await authenticatedPage.route(
        `**/api/v1/repository/${testRepo.namespace}/${testRepo.name}/tag/**`,
        async (route) => {
          const response = await route.fetch();
          const json = await response.json();

          if (json.tags) {
            json.tags = json.tags.map(
              (tag: {is_manifest_list?: boolean; name: string}) => {
                if (tag.is_manifest_list && tag.name === 'multiarch') {
                  return {
                    ...tag,
                    is_sparse: true,
                    child_manifest_count: 2,
                    present_child_count: 1,
                    child_manifests_presence: {
                      'sha256:amd64present': true,
                      'sha256:arm64missing': false,
                    },
                  };
                }
                return tag;
              },
            );
          }

          await route.fulfill({response, json});
        },
      );

      await authenticatedPage.route(
        `**/api/v1/repository/${testRepo.namespace}/${testRepo.name}/manifest/**`,
        async (route) => {
          const response = await route.fetch();
          const json = await response.json();

          if (json.manifest_data) {
            try {
              const manifestData = JSON.parse(json.manifest_data);
              if (
                manifestData.manifests &&
                manifestData.manifests.length >= 2
              ) {
                // Mark first as present, second as missing
                manifestData.manifests[0].is_present = true;
                manifestData.manifests[1].is_present = false;
                json.manifest_data = JSON.stringify(manifestData);
              }
            } catch {
              // Ignore
            }
          }

          await route.fulfill({response, json});
        },
      );

      await authenticatedPage.goto(
        `/repository/${testRepo.fullName}/tag/multiarch`,
      );

      // Wait for page to load
      await expect(
        authenticatedPage.getByRole('heading', {
          level: 1,
          name: /multiarch/,
        }),
      ).toBeVisible();

      // Find and click the architecture selector
      const archSelector = authenticatedPage.getByText(/linux on/i).first();
      await expect(archSelector).toBeVisible();
      await archSelector.click();

      // Check for disabled option with Missing label
      const missingOption = authenticatedPage.getByTestId(
        'missing-arch-option',
      );
      await expect(missingOption.first()).toBeVisible();

      // Verify the missing option has the "Missing" label
      await expect(missingOption.first()).toContainText('Missing');
    });

    test('does not show sparse label for complete manifest list', async ({
      authenticatedPage,
    }) => {
      // Don't mock - use the actual (non-sparse) data
      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);

      // Wait for tags to load
      await expect(
        authenticatedPage.getByRole('link', {name: 'multiarch'}),
      ).toBeVisible();

      // Verify sparse label is NOT displayed for complete manifest
      const sparseLabel = authenticatedPage.getByTestId(
        'sparse-manifest-label',
      );
      await expect(sparseLabel).not.toBeVisible();
    });

    test('shows N/A for security and size of missing architectures', async ({
      authenticatedPage,
    }) => {
      // Mock both endpoints
      await authenticatedPage.route(
        `**/api/v1/repository/${testRepo.namespace}/${testRepo.name}/tag/**`,
        async (route) => {
          const response = await route.fetch();
          const json = await response.json();

          if (json.tags) {
            json.tags = json.tags.map((tag: {is_manifest_list?: boolean}) => {
              if (tag.is_manifest_list) {
                return {
                  ...tag,
                  is_sparse: true,
                  child_manifest_count: 2,
                  present_child_count: 1,
                  child_manifests_presence: {
                    'sha256:present': true,
                    'sha256:missing': false,
                  },
                };
              }
              return tag;
            });
          }

          await route.fulfill({response, json});
        },
      );

      await authenticatedPage.route(
        `**/api/v1/repository/${testRepo.namespace}/${testRepo.name}/manifest/**`,
        async (route) => {
          const response = await route.fetch();
          const json = await response.json();

          if (json.manifest_data) {
            try {
              const manifestData = JSON.parse(json.manifest_data);
              if (manifestData.manifests) {
                manifestData.manifests = manifestData.manifests.map(
                  (m: {digest: string}, idx: number) => ({
                    ...m,
                    is_present: idx === 0,
                  }),
                );
                json.manifest_data = JSON.stringify(manifestData);
              }
            } catch {
              // Ignore
            }
          }

          await route.fulfill({response, json});
        },
      );

      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);

      // Wait for tags to load
      await expect(
        authenticatedPage.getByRole('link', {name: 'multiarch'}),
      ).toBeVisible();

      // Expand the manifest list row
      const expandButton = authenticatedPage
        .getByRole('row')
        .filter({
          has: authenticatedPage.getByRole('link', {name: 'multiarch'}),
        })
        .getByRole('button', {name: /expand/i})
        .first();

      await expandButton.click();

      // Wait for expanded content and check for N/A text
      // The N/A appears for security and size columns on missing manifests
      await expect(authenticatedPage.getByText('N/A').first()).toBeVisible({
        timeout: 10000,
      });
    });
  },
);

test.describe(
  'Sparse Manifest - Non-manifest-list tags',
  {tag: ['@tags']},
  () => {
    test('does not show sparse info for single-architecture tags', async ({
      authenticatedPage,
      api,
    }) => {
      // Create a repository with a single-arch image using mocked response
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
                  manifest_digest: 'sha256:abc123',
                  size: 1000,
                  last_modified: new Date().toISOString(),
                  reversion: false,
                  // Intentionally no is_sparse, child_manifest_count, etc.
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
