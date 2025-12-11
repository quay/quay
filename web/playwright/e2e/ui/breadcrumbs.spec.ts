/**
 * Breadcrumbs navigation tests
 *
 * Verifies breadcrumb navigation is displayed correctly across different pages.
 */

import {test, expect, uniqueName} from '../../fixtures';
import {
  createOrganization,
  deleteOrganization,
  createRepository,
  deleteRepository,
  createTeam,
  deleteTeam,
} from '../../utils/api';
import {TEST_USERS} from '../../global-setup';
import {pushImage, isContainerRuntimeAvailable} from '../../utils/container';

test.describe('Breadcrumbs', {tag: ['@ui', '@breadcrumbs']}, () => {
  test.describe('List pages (no breadcrumbs)', () => {
    test('organization list page has no breadcrumbs', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto('/organization');
      await expect(
        authenticatedPage.getByTestId('page-breadcrumbs-list'),
      ).not.toBeVisible();
    });

    test('repository list page has no breadcrumbs', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto('/repository');
      await expect(
        authenticatedPage.getByTestId('page-breadcrumbs-list'),
      ).not.toBeVisible();
    });
  });

  test.describe('Organization breadcrumbs', () => {
    let orgName: string;

    test.beforeEach(async ({authenticatedRequest}) => {
      orgName = uniqueName('breadcrumborg');
      await createOrganization(authenticatedRequest, orgName);
    });

    test.afterEach(async ({authenticatedRequest}) => {
      try {
        await deleteOrganization(authenticatedRequest, orgName);
      } catch {
        // Already deleted or never created
      }
    });

    test('organization page shows correct breadcrumbs', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/organization/${orgName}`);

      const breadcrumbNav = authenticatedPage.getByTestId(
        'page-breadcrumbs-list',
      );
      await expect(breadcrumbNav).toBeVisible();

      const items = breadcrumbNav.locator('li');
      await expect(items).toHaveCount(2);

      // First item: Organization
      await expect(items.nth(0)).toHaveText('Organization');
      await expect(items.nth(0).locator('a')).toHaveAttribute(
        'href',
        '/organization',
      );

      // Second item: org name (disabled link)
      await expect(items.nth(1)).toHaveText(orgName);
      await expect(items.nth(1).locator('a')).toHaveClass(/disabled-link/);
      await expect(items.nth(1).locator('a')).toHaveAttribute(
        'href',
        `/organization/${orgName}`,
      );
    });
  });

  test.describe('Repository breadcrumbs', () => {
    let orgName: string;
    let repoName: string;

    test.beforeEach(async ({authenticatedRequest}) => {
      orgName = uniqueName('breadcrumborg');
      repoName = uniqueName('breadcrumbrepo');
      await createOrganization(authenticatedRequest, orgName);
      await createRepository(authenticatedRequest, orgName, repoName);
    });

    test.afterEach(async ({authenticatedRequest}) => {
      try {
        await deleteRepository(authenticatedRequest, orgName, repoName);
      } catch {
        // Already deleted
      }
      try {
        await deleteOrganization(authenticatedRequest, orgName);
      } catch {
        // Already deleted
      }
    });

    test('repository page shows correct breadcrumbs', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/repository/${orgName}/${repoName}`);

      const breadcrumbNav = authenticatedPage.getByTestId(
        'page-breadcrumbs-list',
      );
      await expect(breadcrumbNav).toBeVisible();

      const items = breadcrumbNav.locator('li');
      await expect(items).toHaveCount(3);

      // First item: Repository
      await expect(items.nth(0)).toHaveText('Repository');
      await expect(items.nth(0).locator('a')).toHaveAttribute(
        'href',
        '/repository',
      );

      // Second item: org name
      await expect(items.nth(1)).toHaveText(orgName);
      await expect(items.nth(1).locator('a')).toHaveAttribute(
        'href',
        `/organization/${orgName}`,
      );

      // Third item: repo name (disabled link)
      await expect(items.nth(2)).toHaveText(repoName);
      await expect(items.nth(2).locator('a')).toHaveClass(/disabled-link/);
      await expect(items.nth(2).locator('a')).toHaveAttribute(
        'href',
        `/repository/${orgName}/${repoName}`,
      );
    });
  });

  test.describe('Tag breadcrumbs', () => {
    let orgName: string;
    let repoName: string;
    const tagName = 'latest';

    test.beforeEach(async ({authenticatedRequest}) => {
      // Check if container runtime is available
      const hasRuntime = await isContainerRuntimeAvailable();
      test.skip(
        !hasRuntime,
        'No container runtime available for pushing images',
      );

      orgName = uniqueName('breadcrumborg');
      repoName = uniqueName('breadcrumbrepo');
      await createOrganization(authenticatedRequest, orgName);
      await createRepository(authenticatedRequest, orgName, repoName);

      // Push an image with a tag
      await pushImage(
        orgName,
        repoName,
        tagName,
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
    });

    test.afterEach(async ({authenticatedRequest}) => {
      try {
        await deleteRepository(authenticatedRequest, orgName, repoName);
      } catch {
        // Already deleted
      }
      try {
        await deleteOrganization(authenticatedRequest, orgName);
      } catch {
        // Already deleted
      }
    });

    test('tag page shows correct breadcrumbs', async ({authenticatedPage}) => {
      await authenticatedPage.goto(
        `/repository/${orgName}/${repoName}/tag/${tagName}`,
      );

      const breadcrumbNav = authenticatedPage.getByTestId(
        'page-breadcrumbs-list',
      );
      await expect(breadcrumbNav).toBeVisible();

      const items = breadcrumbNav.locator('li');
      await expect(items).toHaveCount(4);

      // First item: Repository
      await expect(items.nth(0)).toHaveText('Repository');
      await expect(items.nth(0).locator('a')).toHaveAttribute(
        'href',
        '/repository',
      );

      // Second item: org name
      await expect(items.nth(1)).toHaveText(orgName);
      await expect(items.nth(1).locator('a')).toHaveAttribute(
        'href',
        `/organization/${orgName}`,
      );

      // Third item: repo name
      await expect(items.nth(2)).toHaveText(repoName);
      await expect(items.nth(2).locator('a')).toHaveAttribute(
        'href',
        `/repository/${orgName}/${repoName}`,
      );

      // Fourth item: tag name (disabled link)
      await expect(items.nth(3)).toHaveText(tagName);
      await expect(items.nth(3).locator('a')).toHaveClass(/disabled-link/);
      await expect(items.nth(3).locator('a')).toHaveAttribute(
        'href',
        `/repository/${orgName}/${repoName}/tag/${tagName}`,
      );
    });
  });

  test.describe('Team breadcrumbs', () => {
    let orgName: string;
    let teamName: string;

    test.beforeEach(async ({authenticatedRequest}) => {
      orgName = uniqueName('breadcrumborg');
      teamName = uniqueName('breadcrumbteam');
      await createOrganization(authenticatedRequest, orgName);
      await createTeam(authenticatedRequest, orgName, teamName);
    });

    test.afterEach(async ({authenticatedRequest}) => {
      try {
        await deleteTeam(authenticatedRequest, orgName, teamName);
      } catch {
        // Already deleted
      }
      try {
        await deleteOrganization(authenticatedRequest, orgName);
      } catch {
        // Already deleted
      }
    });

    test('team page shows correct breadcrumbs', async ({authenticatedPage}) => {
      await authenticatedPage.goto(
        `/organization/${orgName}/teams/${teamName}?tab=Teamsandmembership`,
      );

      const breadcrumbNav = authenticatedPage.getByTestId(
        'page-breadcrumbs-list',
      );
      await expect(breadcrumbNav).toBeVisible();

      const items = breadcrumbNav.locator('li');
      await expect(items).toHaveCount(3);

      // First item: Organization
      await expect(items.nth(0)).toHaveText('Organization');
      await expect(items.nth(0).locator('a')).toHaveAttribute(
        'href',
        '/organization',
      );

      // Second item: org name
      await expect(items.nth(1)).toHaveText(orgName);
      await expect(items.nth(1).locator('a')).toHaveAttribute(
        'href',
        `/organization/${orgName}`,
      );

      // Third item: team name (disabled link)
      await expect(items.nth(2)).toHaveText(teamName);
      await expect(items.nth(2).locator('a')).toHaveClass(/disabled-link/);
      await expect(items.nth(2).locator('a')).toHaveAttribute(
        'href',
        `/organization/${orgName}/teams/${teamName}`,
      );
    });
  });

  test.describe('Same name edge cases', () => {
    let sameName: string;

    test.beforeEach(async ({authenticatedRequest}) => {
      sameName = uniqueName('samename');
      await createOrganization(authenticatedRequest, sameName);
      await createRepository(authenticatedRequest, sameName, sameName);
      await createTeam(authenticatedRequest, sameName, sameName);
    });

    test.afterEach(async ({authenticatedRequest}) => {
      try {
        await deleteTeam(authenticatedRequest, sameName, sameName);
      } catch {
        // Already deleted
      }
      try {
        await deleteRepository(authenticatedRequest, sameName, sameName);
      } catch {
        // Already deleted
      }
      try {
        await deleteOrganization(authenticatedRequest, sameName);
      } catch {
        // Already deleted
      }
    });

    test('org and team with same name shows correct breadcrumbs', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(
        `/organization/${sameName}/teams/${sameName}?tab=Teamsandmembership`,
      );

      const breadcrumbNav = authenticatedPage.getByTestId(
        'page-breadcrumbs-list',
      );
      await expect(breadcrumbNav).toBeVisible();

      const items = breadcrumbNav.locator('li');
      await expect(items).toHaveCount(3);

      // First item: Organization
      await expect(items.nth(0)).toHaveText('Organization');
      await expect(items.nth(0).locator('a')).toHaveAttribute(
        'href',
        '/organization',
      );

      // Second item: org name (same as team name)
      await expect(items.nth(1)).toHaveText(sameName);
      await expect(items.nth(1).locator('a')).toHaveAttribute(
        'href',
        `/organization/${sameName}`,
      );

      // Third item: team name (same as org name, disabled link)
      await expect(items.nth(2)).toHaveText(sameName);
      await expect(items.nth(2).locator('a')).toHaveClass(/disabled-link/);
      await expect(items.nth(2).locator('a')).toHaveAttribute(
        'href',
        `/organization/${sameName}/teams/${sameName}`,
      );
    });

    test('org and repo with same name shows correct breadcrumbs', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/repository/${sameName}/${sameName}`);

      const breadcrumbNav = authenticatedPage.getByTestId(
        'page-breadcrumbs-list',
      );
      await expect(breadcrumbNav).toBeVisible();

      const items = breadcrumbNav.locator('li');
      await expect(items).toHaveCount(3);

      // First item: Repository
      await expect(items.nth(0)).toHaveText('Repository');
      await expect(items.nth(0).locator('a')).toHaveAttribute(
        'href',
        '/repository',
      );

      // Second item: org name (same as repo name)
      await expect(items.nth(1)).toHaveText(sameName);
      await expect(items.nth(1).locator('a')).toHaveAttribute(
        'href',
        `/organization/${sameName}`,
      );

      // Third item: repo name (same as org name, disabled link)
      await expect(items.nth(2)).toHaveText(sameName);
      await expect(items.nth(2).locator('a')).toHaveClass(/disabled-link/);
      await expect(items.nth(2).locator('a')).toHaveAttribute(
        'href',
        `/repository/${sameName}/${sameName}`,
      );
    });
  });
});
