/**
 * Breadcrumbs navigation tests
 *
 * Verifies breadcrumb navigation is displayed correctly across different pages.
 */

import {test, expect} from '../../fixtures';
import {pushImage} from '../../utils/container';
import {TEST_USERS} from '../../global-setup';

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
    test('organization page shows correct breadcrumbs', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('breadcrumborg');

      await authenticatedPage.goto(`/organization/${org.name}`);

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
      await expect(items.nth(1)).toHaveText(org.name);
      await expect(items.nth(1).locator('a')).toHaveClass(/disabled-link/);
      await expect(items.nth(1).locator('a')).toHaveAttribute(
        'href',
        `/organization/${org.name}`,
      );
    });
  });

  test.describe('Repository breadcrumbs', () => {
    test('repository page shows correct breadcrumbs', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('breadcrumborg');
      const repo = await api.repository(org.name, 'breadcrumbrepo');

      await authenticatedPage.goto(`/repository/${org.name}/${repo.name}`);

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
      await expect(items.nth(1)).toHaveText(org.name);
      await expect(items.nth(1).locator('a')).toHaveAttribute(
        'href',
        `/organization/${org.name}`,
      );

      // Third item: repo name (disabled link)
      await expect(items.nth(2)).toHaveText(repo.name);
      await expect(items.nth(2).locator('a')).toHaveClass(/disabled-link/);
      await expect(items.nth(2).locator('a')).toHaveAttribute(
        'href',
        `/repository/${org.name}/${repo.name}`,
      );
    });
  });

  test.describe('Tag breadcrumbs', {tag: ['@container']}, () => {
    test('tag page shows correct breadcrumbs', async ({
      authenticatedPage,
      api,
    }) => {
      const tagName = 'latest';
      const org = await api.organization('breadcrumborg');
      const repo = await api.repository(org.name, 'breadcrumbrepo');

      // Push an image with a tag
      await pushImage(
        org.name,
        repo.name,
        tagName,
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}/tag/${tagName}`,
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
      await expect(items.nth(1)).toHaveText(org.name);
      await expect(items.nth(1).locator('a')).toHaveAttribute(
        'href',
        `/organization/${org.name}`,
      );

      // Third item: repo name
      await expect(items.nth(2)).toHaveText(repo.name);
      await expect(items.nth(2).locator('a')).toHaveAttribute(
        'href',
        `/repository/${org.name}/${repo.name}`,
      );

      // Fourth item: tag name (disabled link)
      await expect(items.nth(3)).toHaveText(tagName);
      await expect(items.nth(3).locator('a')).toHaveClass(/disabled-link/);
      await expect(items.nth(3).locator('a')).toHaveAttribute(
        'href',
        `/repository/${org.name}/${repo.name}/tag/${tagName}`,
      );
    });
  });

  test.describe('Team breadcrumbs', () => {
    test('team page shows correct breadcrumbs', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('breadcrumborg');
      const team = await api.team(org.name, 'breadcrumbteam');

      await authenticatedPage.goto(
        `/organization/${org.name}/teams/${team.name}?tab=Teamsandmembership`,
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
      await expect(items.nth(1)).toHaveText(org.name);
      await expect(items.nth(1).locator('a')).toHaveAttribute(
        'href',
        `/organization/${org.name}`,
      );

      // Third item: team name (disabled link)
      await expect(items.nth(2)).toHaveText(team.name);
      await expect(items.nth(2).locator('a')).toHaveClass(/disabled-link/);
      await expect(items.nth(2).locator('a')).toHaveAttribute(
        'href',
        `/organization/${org.name}/teams/${team.name}`,
      );
    });
  });

  test.describe('Same name edge cases', () => {
    test('org and team with same name shows correct breadcrumbs', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('samename');
      // Create team with same name as org
      await api.team(org.name, org.name);

      await authenticatedPage.goto(
        `/organization/${org.name}/teams/${org.name}?tab=Teamsandmembership`,
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
      await expect(items.nth(1)).toHaveText(org.name);
      await expect(items.nth(1).locator('a')).toHaveAttribute(
        'href',
        `/organization/${org.name}`,
      );

      // Third item: team name (same as org name, disabled link)
      await expect(items.nth(2)).toHaveText(org.name);
      await expect(items.nth(2).locator('a')).toHaveClass(/disabled-link/);
      await expect(items.nth(2).locator('a')).toHaveAttribute(
        'href',
        `/organization/${org.name}/teams/${org.name}`,
      );
    });

    test('org and repo with same name shows correct breadcrumbs', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('samename');
      // Create repo with same name as org
      await api.repository(org.name, org.name);

      await authenticatedPage.goto(`/repository/${org.name}/${org.name}`);

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
      await expect(items.nth(1)).toHaveText(org.name);
      await expect(items.nth(1).locator('a')).toHaveAttribute(
        'href',
        `/organization/${org.name}`,
      );

      // Third item: repo name (same as org name, disabled link)
      await expect(items.nth(2)).toHaveText(org.name);
      await expect(items.nth(2).locator('a')).toHaveClass(/disabled-link/);
      await expect(items.nth(2).locator('a')).toHaveAttribute(
        'href',
        `/repository/${org.name}/${org.name}`,
      );
    });
  });
});
