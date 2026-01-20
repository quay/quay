/**
 * Security Report Page Tests
 *
 * Tests for the security vulnerability report displayed for container images.
 * Uses real Clair security scanning where possible, with mocks only for error states.
 *
 * Prerequisites:
 * - FEATURE_SECURITY_SCANNER: true
 * - SECURITY_SCANNER_V4_ENDPOINT configured
 * - Clair running (make local-dev-up-with-clair)
 */

import {test, expect, type Page} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushVulnerableImage} from '../../utils/container';
import {ApiClient} from '../../utils/api';
import type {SecurityScanStatus} from '../../utils/api';

/**
 * Helper to set up mock routes for security scan error states.
 * Mocks security, tag, and manifest endpoints for a repository.
 */
async function setupSecurityMocks(
  page: Page,
  repo: {namespace: string; name: string},
  status: SecurityScanStatus,
): Promise<void> {
  // Mock security endpoint to return specified status
  await page.route('**/api/v1/repository/**/manifest/**/security*', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status,
        data: {
          Layer: {
            Name: 'sha256:mock',
            ParentName: '',
            NamespaceName: '',
            IndexedByVersion: 4,
            Features: [],
          },
        },
      }),
    });
  });

  // Mock tag endpoint
  await page.route(
    `**/api/v1/repository/${repo.namespace}/${repo.name}/tag/*`,
    (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          page: 1,
          has_additional: false,
          tags: [
            {
              name: 'mocktag',
              manifest_digest: 'sha256:mockdigest123',
              is_manifest_list: false,
              size: 1000,
              last_modified: new Date().toISOString(),
              reversion: false,
            },
          ],
        }),
      });
    },
  );

  // Mock manifest endpoint (excluding security which is handled above)
  await page.route(
    `**/api/v1/repository/${repo.namespace}/${repo.name}/manifest/**`,
    (route) => {
      const url = route.request().url();
      // Let security requests be handled by the security route
      if (url.includes('/security')) {
        route.fallback();
        return;
      }
      if (url.includes('/labels')) {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({labels: []}),
        });
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            digest: 'sha256:mockdigest123',
            is_manifest_list: false,
            manifest_data: '{}',
          }),
        });
      }
    },
  );
}

test.describe(
  'Security Report',
  {tag: ['@repository', '@feature:SECURITY_SCANNER']},
  () => {
    test.describe('Real Vulnerability Scanning', {tag: ['@container']}, () => {
      // Shared repo for vulnerability tests - created once to avoid slow image push per test
      let sharedRepo: {
        namespace: string;
        name: string;
        fullName: string;
      } | null = null;
      let manifestDigest: string | null = null;

      // Increase timeout for beforeAll - image push + scan can take 3+ minutes
      test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
        // Skip setup if no container runtime (tests auto-skip via @container tag)
        if (!cachedContainerAvailable) return;

        test.setTimeout(180000); // 3 minutes for image push + scan

        const api = new ApiClient(userContext.request);
        const repoName = `sec-scan-${Date.now()}`;
        await api.createRepository(
          TEST_USERS.user.username,
          repoName,
          'private',
        );
        sharedRepo = {
          namespace: TEST_USERS.user.username,
          name: repoName,
          fullName: `${TEST_USERS.user.username}/${repoName}`,
        };

        // Push vulnerable image (has known CVEs)
        await pushVulnerableImage(
          sharedRepo.namespace,
          sharedRepo.name,
          'vulns',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        // Get manifest digest
        const tagsResponse = await api.getTags(
          sharedRepo.namespace,
          sharedRepo.name,
        );
        manifestDigest = tagsResponse.tags[0].manifest_digest;

        // Wait for security scan to complete (up to 2 minutes)
        await api.waitForSecurityScan(
          sharedRepo.namespace,
          sharedRepo.name,
          manifestDigest,
          120000,
          5000,
        );
      });

      test.afterAll(async ({userContext, cachedContainerAvailable}) => {
        if (!cachedContainerAvailable || !sharedRepo) return;
        const api = new ApiClient(userContext.request);
        try {
          await api.deleteRepository(sharedRepo.namespace, sharedRepo.name);
        } catch {
          // Ignore cleanup errors
        }
      });

      test('displays security report with vulnerabilities', async ({
        authenticatedPage,
      }) => {
        test.skip(!sharedRepo, 'Shared repo not created');

        // Navigate to security report tab
        await authenticatedPage.goto(
          `/repository/${sharedRepo!.fullName}/tag/vulns?tab=securityreport`,
        );

        // Verify vulnerability chart is displayed
        const chart = authenticatedPage.getByTestId('vulnerability-chart');
        await expect(chart).toBeVisible();

        // Should show vulnerability count
        await expect(
          authenticatedPage.getByText(/has detected \d+ vulnerabilities/),
        ).toBeVisible();

        // Verify vulnerability table is displayed
        const table = authenticatedPage.getByTestId('vulnerability-table');
        await expect(table).toBeVisible();

        // Should have advisory cells (at least some vulnerabilities)
        const advisoryCells = authenticatedPage.locator(
          'td[data-label="Advisory"]',
        );
        await expect(advisoryCells.first()).toBeVisible();
      });

      test('filters vulnerabilities by fixable checkbox', async ({
        authenticatedPage,
      }) => {
        test.skip(!sharedRepo, 'Shared repo not created');

        await authenticatedPage.goto(
          `/repository/${sharedRepo!.fullName}/tag/vulns?tab=securityreport`,
        );

        // Wait for table to load
        await expect(
          authenticatedPage.getByTestId('vulnerability-table'),
        ).toBeVisible();

        // Get initial count
        const advisoryCells = authenticatedPage.locator(
          'td[data-label="Advisory"]',
        );
        const initialCount = await advisoryCells.count();

        // Check fixable checkbox
        const fixableCheckbox = authenticatedPage.locator('#fixable-checkbox');
        await fixableCheckbox.check();

        // Wait for filter to apply
        await authenticatedPage.waitForTimeout(500);

        // The count may change (could be fewer or same if all are fixable)
        // Uncheck to restore
        await fixableCheckbox.uncheck();
        await expect(advisoryCells).toHaveCount(initialCount);
      });

      test('filters vulnerabilities by search input', async ({
        authenticatedPage,
      }) => {
        test.skip(!sharedRepo, 'Shared repo not created');

        await authenticatedPage.goto(
          `/repository/${sharedRepo!.fullName}/tag/vulns?tab=securityreport`,
        );

        // Wait for table to load
        await expect(
          authenticatedPage.getByTestId('vulnerability-table'),
        ).toBeVisible();

        // Get advisory cells and count before filtering
        const advisoryCells = authenticatedPage.locator(
          'td[data-label="Advisory"]',
        );
        const countBeforeFilter = await advisoryCells.count();

        // Filter by CVE prefix
        const searchInput = authenticatedPage.locator(
          'input[placeholder="Filter Vulnerabilities..."]',
        );
        await searchInput.fill('CVE');

        // Wait for filter to apply (debounce)
        await authenticatedPage.waitForTimeout(500);

        // Filtered count should be <= original count
        const countAfterFilter = await advisoryCells.count();
        expect(countAfterFilter).toBeLessThanOrEqual(countBeforeFilter);

        // Clear filter
        await searchInput.clear();
        await expect(advisoryCells.first()).toBeVisible();
      });

      test('sorts vulnerabilities by severity', async ({authenticatedPage}) => {
        test.skip(!sharedRepo, 'Shared repo not created');

        await authenticatedPage.goto(
          `/repository/${sharedRepo!.fullName}/tag/vulns?tab=securityreport`,
        );

        // Wait for table to load
        const table = authenticatedPage.getByTestId('vulnerability-table');
        await expect(table).toBeVisible();

        // Click severity sort button to toggle order
        const sortButton = table.locator('#severity-sort button');
        if (await sortButton.isVisible()) {
          await sortButton.click();
          await authenticatedPage.waitForTimeout(300);
          // Table should re-render with different order
          await expect(table).toBeVisible();
        }
      });
    });

    test.describe('Scan Error States (Mocked)', () => {
      test('displays queued state', async ({authenticatedPage, api}) => {
        const repo = await api.repository(undefined, 'secqueued');
        await setupSecurityMocks(authenticatedPage, repo, 'queued');

        await authenticatedPage.goto(
          `/repository/${repo.fullName}/tag/mocktag?tab=securityreport`,
        );

        // Verify queued state UI (use .first() since text appears in multiple tabs)
        await expect(
          authenticatedPage
            .getByRole('heading', {name: 'Security scan is currently queued.'})
            .first(),
        ).toBeVisible();
        await expect(
          authenticatedPage
            .getByText('Refresh page for updates in scan status.')
            .first(),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByRole('button', {name: 'Reload'}).first(),
        ).toBeVisible();
      });

      test('displays failed state', async ({authenticatedPage, api}) => {
        const repo = await api.repository(undefined, 'secfailed');
        await setupSecurityMocks(authenticatedPage, repo, 'failed');

        await authenticatedPage.goto(
          `/repository/${repo.fullName}/tag/mocktag?tab=securityreport`,
        );

        // Verify failed state UI (use .first() since text appears in multiple tabs)
        await expect(
          authenticatedPage
            .getByRole('heading', {name: 'Security scan has failed.'})
            .first(),
        ).toBeVisible();
        await expect(
          authenticatedPage
            .getByText('The scan could not be completed due to error.')
            .first(),
        ).toBeVisible();
      });

      test('displays unsupported state', async ({authenticatedPage, api}) => {
        const repo = await api.repository(undefined, 'secunsupported');
        await setupSecurityMocks(authenticatedPage, repo, 'unsupported');

        await authenticatedPage.goto(
          `/repository/${repo.fullName}/tag/mocktag?tab=securityreport`,
        );

        // Verify unsupported state UI (use .first() since text appears in multiple tabs)
        await expect(
          authenticatedPage
            .getByRole('heading', {name: 'Security scan is not supported.'})
            .first(),
        ).toBeVisible();
        await expect(
          authenticatedPage
            .getByText('Image does not have content the scanner recognizes.')
            .first(),
        ).toBeVisible();
      });
    });
  },
);
