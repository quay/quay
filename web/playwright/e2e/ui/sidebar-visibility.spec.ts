/**
 * Sidebar visibility tests
 *
 * Verifies the global sidebar is hidden on detail pages (repository, organization)
 * where tab navigation provides contextual nav, and visible on list pages.
 *
 * Ref: PROJQUAY-11889
 */

import {test, expect} from '../../fixtures';

test.describe(
  'Sidebar visibility',
  {tag: ['@ui', '@sidebar', '@PROJQUAY-11889']},
  () => {
    test('sidebar is visible on repository list page', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto('/repository');
      await expect(authenticatedPage.locator('.page-sidebar')).toBeVisible();
    });

    test('sidebar is visible on organization list page', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto('/organization');
      await expect(authenticatedPage.locator('.page-sidebar')).toBeVisible();
    });

    test('sidebar is hidden on repository detail page', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await authenticatedPage.goto(`/repository/${repo.fullName}`);

      // Tab navigation should be visible (proves we're on a detail page)
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Information'}),
      ).toBeVisible();

      // Sidebar should not be visible
      await expect(
        authenticatedPage.locator('.page-sidebar'),
      ).not.toBeVisible();
    });

    test('sidebar is hidden on organization detail page', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('sidebarorg');
      await authenticatedPage.goto(`/organization/${org.name}`);

      // Org detail content should be visible (proves we're on a detail page)
      await expect(authenticatedPage.locator('h1')).toBeVisible();

      // Sidebar should not be visible
      await expect(
        authenticatedPage.locator('.page-sidebar'),
      ).not.toBeVisible();
    });
  },
);
