/**
 * PROJQUAY-10837: Tag Expiration Disabled for Org Mirror Repositories
 *
 * Verifies that tag expiration controls are disabled when the repository
 * is in a non-NORMAL state (e.g., ORG_MIRROR). Uses route interception
 * to simulate the ORG_MIRROR state without requiring the full org mirror
 * worker setup.
 */

import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushImage} from '../../utils/container';

/**
 * Intercept the repository details API and override the state to ORG_MIRROR.
 */
async function mockOrgMirrorState(
  page: import('@playwright/test').Page,
  namespace: string,
  repoName: string,
) {
  await page.route(
    `**/api/v1/repository/${namespace}/${repoName}?*`,
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue();
        return;
      }
      const response = await route.fetch();
      const body = await response.json();
      body.state = 'ORG_MIRROR';
      await route.fulfill({
        status: response.status(),
        headers: response.headers(),
        body: JSON.stringify(body),
      });
    },
  );
}

test.describe(
  'Tag Expiration - Org Mirror Repositories',
  {tag: ['@tags', '@feature:ORG_MIRROR', '@container']},
  () => {
    test('expiration column shows "Never" as non-clickable text for ORG_MIRROR repo', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1.0.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await mockOrgMirrorState(authenticatedPage, repo.namespace, repo.name);
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
      ).toBeVisible();

      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});

      // "Never" should be visible but NOT rendered as a clickable link
      const neverText = tagRow.getByText('Never');
      await expect(neverText).toBeVisible();

      const neverLink = tagRow.locator('a', {hasText: 'Never'});
      await expect(neverLink).not.toBeVisible();
    });

    test('change expiration action is disabled in kebab menu for ORG_MIRROR repo', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1.0.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await mockOrgMirrorState(authenticatedPage, repo.namespace, repo.name);
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
      ).toBeVisible();

      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});

      await tagRow.getByLabel('Tag actions kebab').click();

      const expirationAction = authenticatedPage.getByRole('menuitem', {
        name: 'Change expiration',
      });
      await expect(expirationAction).toBeDisabled();
    });

    test('bulk set expiration is disabled in toolbar for ORG_MIRROR repo', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1.0.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await mockOrgMirrorState(authenticatedPage, repo.namespace, repo.name);
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
      ).toBeVisible();

      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});

      // Select the tag
      await tagRow.getByRole('checkbox').click();

      // Open bulk actions kebab
      await authenticatedPage.getByTestId('bulk-actions-kebab').click();

      const setExpirationAction = authenticatedPage.getByRole('menuitem', {
        name: 'Set expiration',
      });
      await expect(setExpirationAction).toBeDisabled();
    });

    test('existing expiration is displayed as read-only for ORG_MIRROR repo', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1.0.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Set expiration before mocking the state
      const expirationTimestamp =
        Math.floor(Date.now() / 1000) + 30 * 24 * 60 * 60;
      await api.raw.setTagExpiration(
        repo.namespace,
        repo.name,
        'v1.0.0',
        expirationTimestamp,
      );

      await mockOrgMirrorState(authenticatedPage, repo.namespace, repo.name);
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
      ).toBeVisible();

      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});

      const expirationCell = tagRow.locator('[data-label="Expires"]');

      // Expiration should be shown but NOT as a clickable link
      await expect(expirationCell.locator('a')).not.toBeVisible();

      // The expiration text (span) should still be present
      await expect(expirationCell.locator('span').first()).toBeVisible();
    });

    test('clicking Never text does not open expiration modal for ORG_MIRROR repo', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1.0.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await mockOrgMirrorState(authenticatedPage, repo.namespace, repo.name);
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
      ).toBeVisible();

      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});

      // Click "Never" text
      const neverText = tagRow.getByText('Never');
      await neverText.click();

      // Expiration modal should NOT open
      await expect(
        authenticatedPage.getByTestId('edit-expiration-tags'),
      ).not.toBeVisible();
    });
  },
);
