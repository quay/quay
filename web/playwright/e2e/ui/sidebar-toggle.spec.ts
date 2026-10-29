import {test, expect} from '../../fixtures';
import type {Page} from '@playwright/test';

// PF hides a collapsed mobile sidebar with opacity and a transform, which
// toBeVisible() ignores; role queries skip its aria-hidden subtree instead.
const sidebarLink = (page: Page) =>
  page
    .getByRole('navigation', {name: 'Global'})
    .getByRole('link', {name: 'Organizations'});

const hamburger = (page: Page) =>
  page.getByRole('button', {name: 'Global navigation'});

async function expectSidebarOpen(page: Page) {
  await expect(sidebarLink(page)).toBeVisible();
  await expect(sidebarLink(page)).toBeInViewport();
}

async function expectSidebarClosed(page: Page) {
  await expect(sidebarLink(page)).toBeHidden();
}

test.describe(
  'Sidebar toggle',
  {tag: ['@ui', '@sidebar-toggle', '@PROJQUAY-11965']},
  () => {
    test.beforeEach(async ({authenticatedPage}) => {
      // The desktop state persists in the worker-shared context's localStorage.
      await authenticatedPage.addInitScript(() =>
        localStorage.removeItem('quay-sidebar-open'),
      );
    });

    test('hamburger opens and closes the sidebar below the xl breakpoint', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.setViewportSize({width: 1000, height: 800});
      await authenticatedPage.goto('/organization');
      await expect(hamburger(authenticatedPage)).toBeVisible();
      await expectSidebarClosed(authenticatedPage);

      await hamburger(authenticatedPage).click();
      await expectSidebarOpen(authenticatedPage);

      await hamburger(authenticatedPage).click();
      await expectSidebarClosed(authenticatedPage);
    });

    test('hamburger closes and reopens the sidebar at desktop width', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.setViewportSize({width: 1400, height: 900});
      await authenticatedPage.goto('/organization');
      await expectSidebarOpen(authenticatedPage);

      await hamburger(authenticatedPage).click();
      await expectSidebarClosed(authenticatedPage);

      await hamburger(authenticatedPage).click();
      await expectSidebarOpen(authenticatedPage);
    });
  },
);
