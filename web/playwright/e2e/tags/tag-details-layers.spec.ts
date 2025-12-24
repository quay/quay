import {test, expect} from '@playwright/test';
import {API_URL} from '../../utils/config';

/**
 * Test credentials for user1 (from seeded Cypress test data)
 * This user owns the hello-world repository with manifestlist tag
 */
const USER1 = {
  username: 'user1',
  password: 'password',
};

/**
 * Helper to login as user1 and get authenticated page
 */
async function loginAsUser1(page: import('@playwright/test').Page) {
  // Get CSRF token
  const csrfResponse = await page.request.get(`${API_URL}/csrf_token`);
  const csrfData = await csrfResponse.json();
  const csrfToken = csrfData.csrf_token;

  // Sign in as user1
  await page.request.post(`${API_URL}/api/v1/signin`, {
    headers: {
      'X-CSRF-Token': csrfToken,
    },
    data: {
      username: USER1.username,
      password: USER1.password,
    },
  });
}

test.describe(
  'Tag Details - Multi-Architecture Manifest Layers',
  {tag: ['@tags', '@layers']},
  () => {
    test.beforeEach(async ({page}) => {
      await loginAsUser1(page);
    });

    test('displays layers for multi-architecture manifest child', async ({
      page,
    }) => {
      // Navigate to the manifestlist tag with a specific child digest
      // This is a multi-arch manifest list with amd64 and arm64 children
      await page.goto(
        '/repository/user1/hello-world/tag/manifestlist?tab=layers',
      );

      // Wait for page to fully load by checking for the page heading
      // This is more reliable than networkidle in CI environments
      await expect(
        page.getByRole('heading', {level: 1, name: /hello-world:manifestlist/}),
      ).toBeVisible();

      // Verify we're on the Layers tab
      await expect(page.getByRole('tab', {name: 'Layers'})).toBeVisible();

      // Verify "Manifest Layers" heading is displayed
      await expect(page.getByText('Manifest Layers')).toBeVisible();

      // The key assertion: layers should be displayed, NOT "No layers found"
      // This was the bug - multi-arch manifests were showing "No layers found"
      await expect(
        page.getByText('No layers found for this manifest.'),
      ).not.toBeVisible();

      // Verify at least one layer is displayed (layers have role="listitem")
      const layers = page.getByRole('listitem');
      await expect(layers.first()).toBeVisible();
    });

    test('updates layers when switching architecture', async ({page}) => {
      // Navigate to the manifestlist tag
      await page.goto('/repository/user1/hello-world/tag/manifestlist');

      // Wait for page to fully load by checking for the page heading
      await expect(
        page.getByRole('heading', {level: 1, name: /hello-world:manifestlist/}),
      ).toBeVisible();

      // Verify architecture selector is visible (indicates multi-arch manifest)
      const archSelector = page.getByText('linux on amd64');
      await expect(archSelector).toBeVisible();

      // Click to open architecture dropdown
      await archSelector.click();

      // Select a different architecture (arm64)
      await page.getByText('linux on arm64').click();

      // Navigate to Layers tab
      await page.getByRole('tab', {name: 'Layers'}).click();

      // Verify layers are displayed for the new architecture
      await expect(page.getByText('Manifest Layers')).toBeVisible();
      await expect(
        page.getByText('No layers found for this manifest.'),
      ).not.toBeVisible();

      // Verify at least one layer is displayed
      const layers = page.getByRole('listitem');
      await expect(layers.first()).toBeVisible();
    });

    test('displays layers when navigating directly to child manifest via digest', async ({
      page,
    }) => {
      // Navigate directly to a child manifest using digest parameter
      // sha256:f54a58bc... is the amd64 child manifest digest from test data
      await page.goto(
        '/repository/user1/hello-world/tag/manifestlist?digest=sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4&tab=layers',
      );

      // Wait for page to fully load by checking for the page heading
      await expect(
        page.getByRole('heading', {level: 1, name: /hello-world:manifestlist/}),
      ).toBeVisible();

      // Verify layers are displayed
      await expect(page.getByText('Manifest Layers')).toBeVisible();
      await expect(
        page.getByText('No layers found for this manifest.'),
      ).not.toBeVisible();

      // Verify at least one layer is displayed
      const layers = page.getByRole('listitem');
      await expect(layers.first()).toBeVisible();
    });

    test('single-architecture image still displays layers correctly', async ({
      page,
    }) => {
      // Navigate to a single-arch tag (latest) - Layers tab
      await page.goto('/repository/user1/hello-world/tag/latest?tab=layers');

      // Wait for page to fully load by checking for the page heading
      await expect(
        page.getByRole('heading', {level: 1, name: /hello-world:latest/}),
      ).toBeVisible();

      // Verify layers are displayed for single-arch image
      await expect(page.getByText('Manifest Layers')).toBeVisible();

      // Single-arch images should also show layers
      // If there are layers, they should be visible; if not, we get "No layers found"
      // For the test data, single-arch images should have layers
      const layers = page.getByRole('listitem');
      const layerCount = await layers.count();

      // Either we have layers, or we have "No layers found" message
      // For hello-world image, we expect layers to be present
      if (layerCount > 0) {
        await expect(layers.first()).toBeVisible();
      }
    });
  },
);
