import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {
  pushMultiArchImage,
  pushImage,
  isContainerRuntimeAvailable,
} from '../../utils/container';

test.describe(
  'Tag Details - Multi-Architecture Manifest Layers',
  {tag: ['@tags', '@layers']},
  () => {
    // Shared test data created once per describe block
    let testRepo: {namespace: string; name: string; fullName: string};
    let hasContainerRuntime = false;

    test.beforeAll(async ({userContext}) => {
      // Check if container runtime is available for pushing images
      hasContainerRuntime = await isContainerRuntimeAvailable();

      if (!hasContainerRuntime) {
        console.log(
          'Skipping multi-arch layer tests: no container runtime available',
        );
        return;
      }

      // Use the pre-authenticated userContext (already logged in as test user)
      const api = new ApiClient(userContext.request);

      // Create repository for test images
      const repoName = `layers-test-${Date.now()}`;
      await api.createRepository(TEST_USERS.user.username, repoName, 'private');

      testRepo = {
        namespace: TEST_USERS.user.username,
        name: repoName,
        fullName: `${TEST_USERS.user.username}/${repoName}`,
      };

      // Push multi-arch image
      await pushMultiArchImage(
        testRepo.namespace,
        testRepo.name,
        'manifestlist',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Push single-arch image for comparison test
      await pushImage(
        testRepo.namespace,
        testRepo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
    });

    test.afterAll(async ({userContext}) => {
      if (!testRepo) return;

      // Cleanup: delete the test repository using pre-authenticated context
      const api = new ApiClient(userContext.request);

      try {
        await api.deleteRepository(testRepo.namespace, testRepo.name);
      } catch {
        // Ignore cleanup errors
      }
    });

    test.beforeEach(async () => {
      test.skip(
        !hasContainerRuntime,
        'Skipping: no container runtime available to push test images',
      );
    });

    test('displays layers for multi-architecture manifest child', async ({
      authenticatedPage,
    }) => {
      // Navigate to the manifestlist tag with layers tab
      await authenticatedPage.goto(
        `/repository/${testRepo.fullName}/tag/manifestlist?tab=layers`,
      );

      // Wait for page to fully load by checking for the page heading
      await expect(
        authenticatedPage.getByRole('heading', {
          level: 1,
          name: new RegExp(`${testRepo.name}:manifestlist`),
        }),
      ).toBeVisible();

      // Verify we're on the Layers tab
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Layers'}),
      ).toBeVisible();

      // Verify "Manifest Layers" heading is displayed
      await expect(
        authenticatedPage.getByText('Manifest Layers'),
      ).toBeVisible();

      // The key assertion: layers should be displayed, NOT "No layers found"
      // This was the bug - multi-arch manifests were showing "No layers found"
      await expect(
        authenticatedPage.getByText('No layers found for this manifest.'),
      ).not.toBeVisible();

      // Verify at least one layer is displayed (layers have role="listitem")
      const layers = authenticatedPage.getByRole('listitem');
      await expect(layers.first()).toBeVisible();
    });

    test('updates layers when switching architecture', async ({
      authenticatedPage,
    }) => {
      // Navigate to the manifestlist tag
      await authenticatedPage.goto(
        `/repository/${testRepo.fullName}/tag/manifestlist`,
      );

      // Wait for page to fully load by checking for the page heading
      await expect(
        authenticatedPage.getByRole('heading', {
          level: 1,
          name: new RegExp(`${testRepo.name}:manifestlist`),
        }),
      ).toBeVisible();

      // Verify architecture selector is visible (indicates multi-arch manifest)
      const archSelector = authenticatedPage.getByText(/linux on amd64/i);
      await expect(archSelector).toBeVisible();

      // Click to open architecture dropdown
      await archSelector.click();

      // Select a different architecture (arm64 or another available one)
      const arm64Option = authenticatedPage.getByText(/linux on arm64/i);
      if (await arm64Option.isVisible()) {
        await arm64Option.click();
      } else {
        // If arm64 not available, just close the dropdown and continue
        await authenticatedPage.keyboard.press('Escape');
      }

      // Navigate to Layers tab
      await authenticatedPage.getByRole('tab', {name: 'Layers'}).click();

      // Verify layers are displayed for the selected architecture
      await expect(
        authenticatedPage.getByText('Manifest Layers'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('No layers found for this manifest.'),
      ).not.toBeVisible();

      // Verify at least one layer is displayed
      const layers = authenticatedPage.getByRole('listitem');
      await expect(layers.first()).toBeVisible();
    });

    test('single-architecture image still displays layers correctly', async ({
      authenticatedPage,
    }) => {
      // Navigate to a single-arch tag (latest) - Layers tab
      await authenticatedPage.goto(
        `/repository/${testRepo.fullName}/tag/latest?tab=layers`,
      );

      // Wait for page to fully load by checking for the page heading
      await expect(
        authenticatedPage.getByRole('heading', {
          level: 1,
          name: new RegExp(`${testRepo.name}:latest`),
        }),
      ).toBeVisible();

      // Verify layers are displayed for single-arch image
      await expect(
        authenticatedPage.getByText('Manifest Layers'),
      ).toBeVisible();

      // Single-arch images should also show layers
      const layers = authenticatedPage.getByRole('listitem');

      // For busybox image, we expect layers to be present
      await expect(layers.first()).toBeVisible();
      await expect(
        authenticatedPage.getByText('No layers found for this manifest.'),
      ).not.toBeVisible();
    });
  },
);
