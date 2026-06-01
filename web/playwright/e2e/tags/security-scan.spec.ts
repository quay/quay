import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {pushImage, pushOCIImage} from '../../utils/container';

test.describe(
  'Security Scan',
  {tag: ['@tags', '@container', '@feature:SECURITY_SCANNER']},
  () => {
    let testRepo: {namespace: string; name: string; fullName: string};
    let scanOk: boolean;

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      test.skip(!cachedContainerAvailable, 'No container runtime available');

      const api = new ApiClient(userContext.request);
      const repoName = `secscan-${Date.now()}`;
      await api.createRepository(TEST_USERS.user.username, repoName, 'public');

      testRepo = {
        namespace: TEST_USERS.user.username,
        name: repoName,
        fullName: `${TEST_USERS.user.username}/${repoName}`,
      };

      await pushImage(
        testRepo.namespace,
        testRepo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const tags = await api.getTags(testRepo.namespace, testRepo.name);
      const digest = tags.tags[0].manifest_digest;
      const scanResult = await api.waitForScan(
        testRepo.namespace,
        testRepo.name,
        digest,
        120_000,
      );
      scanOk = scanResult.status === 'scanned';
    });

    test.afterAll(async ({userContext}) => {
      if (!testRepo) return;
      const api = new ApiClient(userContext.request);
      try {
        await api.deleteRepository(testRepo.namespace, testRepo.name);
      } catch {
        // Ignore cleanup errors
      }
    });

    test('shows security scan results for a pushed image', async ({
      authenticatedPage,
    }) => {
      expect(scanOk, 'Clair scan must complete successfully').toBeTruthy();

      // Verify Security column visible on tags page
      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.locator('th').filter({hasText: 'Security'}),
      ).toBeVisible();

      // Navigate to tag detail - verify Security Report and Packages tabs exist
      await authenticatedPage.getByRole('link', {name: 'latest'}).click();
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Security Report'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Packages'}),
      ).toBeVisible();

      // Click Security Report tab - verify scan completed (not queued/failed)
      await authenticatedPage
        .getByRole('tab', {name: 'Security Report'})
        .click();
      await expect(authenticatedPage).toHaveURL(/tab=securityreport/);
      await expect(
        authenticatedPage.getByText(
          /detected \d+ vulnerabilit|detected no vulnerabilit/,
        ),
      ).toBeVisible({timeout: 10000});

      // Verify vulnerability chart rendered
      await expect(
        authenticatedPage.locator('[data-testid="vulnerability-chart"]'),
      ).toBeVisible();

      // Click Packages tab - verify packages content rendered
      await authenticatedPage.getByRole('tab', {name: 'Packages'}).click();
      await expect(authenticatedPage).toHaveURL(/tab=packages/);
      await expect(
        authenticatedPage.locator('[data-testid="packages-chart"]'),
      ).toBeVisible();
      // Should show either packages recognized or no packages recognized
      await expect(
        authenticatedPage.getByText(
          /recognized \d+ package|does not recognize any package/,
        ),
      ).toBeVisible();
    });

    test('vulnerability report supports filtering and sorting', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(
        `/repository/${testRepo.fullName}/tag/latest?tab=securityreport`,
      );
      await expect(
        authenticatedPage.getByText(
          /detected \d+ vulnerabilit|detected no vulnerabilit/,
        ),
      ).toBeVisible({timeout: 10000});

      const vulnRows = authenticatedPage.locator('td[data-label="Advisory"]');
      const initialCount = await vulnRows.count();
      if (initialCount === 0) {
        // No vulnerabilities to filter - skip interaction tests
        return;
      }

      // Test fixable-only checkbox
      await authenticatedPage.locator('#fixable-checkbox').check();
      const fixableCount = await vulnRows.count();
      expect(fixableCount).toBeLessThanOrEqual(initialCount);
      await authenticatedPage.locator('#fixable-checkbox').uncheck();
      await expect(vulnRows).toHaveCount(initialCount);

      // Test name filter
      const firstPackage = await authenticatedPage
        .locator('td[data-label="Package"] >> nth=0')
        .innerText();
      const filterTerm = firstPackage.slice(0, 3);
      await authenticatedPage
        .locator('input[placeholder="Filter Vulnerabilities..."]')
        .fill(filterTerm);
      const filteredCount = await vulnRows.count();
      expect(filteredCount).toBeGreaterThan(0);
      expect(filteredCount).toBeLessThanOrEqual(initialCount);
      await authenticatedPage
        .locator('input[placeholder="Filter Vulnerabilities..."]')
        .clear();
      await expect(vulnRows).toHaveCount(initialCount);

      // Test sorting - click severity sort and verify table still renders
      await authenticatedPage.locator('#severity-sort button').click();
      await expect(vulnRows.first()).toBeVisible();
    });

    test('packages tab supports filtering', async ({authenticatedPage}) => {
      await authenticatedPage.goto(
        `/repository/${testRepo.fullName}/tag/latest?tab=packages`,
      );
      await expect(
        authenticatedPage.getByText(
          /recognized \d+ package|does not recognize any package/,
        ),
      ).toBeVisible({timeout: 10000});

      const packageRows = authenticatedPage.locator(
        'td[data-label="Package Name"]',
      );
      const initialCount = await packageRows.count();
      if (initialCount === 0) {
        return;
      }

      // Test name filter
      const firstPackage = await packageRows.first().innerText();
      const filterTerm = firstPackage.slice(0, 3);
      await authenticatedPage
        .locator('input[placeholder="Filter Packages..."]')
        .fill(filterTerm);
      const filteredCount = await packageRows.count();
      expect(filteredCount).toBeGreaterThan(0);
      expect(filteredCount).toBeLessThanOrEqual(initialCount);
      await authenticatedPage
        .locator('input[placeholder="Filter Packages..."]')
        .clear();
      await expect(packageRows).toHaveCount(initialCount);
    });
  },
);

test.describe(
  'OCI Image Security Scan (PROJQUAY-11333)',
  {tag: ['@tags', '@container', '@feature:SECURITY_SCANNER']},
  () => {
    let testRepo: {namespace: string; name: string; fullName: string};
    let scanOk: boolean;

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      test.setTimeout(180000);
      test.skip(!cachedContainerAvailable, 'No container runtime available');

      const api = new ApiClient(userContext.request);
      const repoName = `oci-secscan-${Date.now()}`;
      await api.createRepository(TEST_USERS.user.username, repoName, 'public');

      testRepo = {
        namespace: TEST_USERS.user.username,
        name: repoName,
        fullName: `${TEST_USERS.user.username}/${repoName}`,
      };

      await pushOCIImage(
        testRepo.namespace,
        testRepo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const tags = await api.getTags(testRepo.namespace, testRepo.name);
      const digest = tags.tags[0].manifest_digest;
      const scanResult = await api.waitForScan(
        testRepo.namespace,
        testRepo.name,
        digest,
        120_000,
      );
      scanOk = scanResult.status === 'scanned';
    });

    test.afterAll(async ({userContext}) => {
      if (!testRepo) return;
      const api = new ApiClient(userContext.request);
      try {
        await api.deleteRepository(testRepo.namespace, testRepo.name);
      } catch {
        // Ignore cleanup errors
      }
    });

    test('OCI-format image is scanned successfully, not marked as unsupported', async ({
      authenticatedPage,
    }) => {
      test.setTimeout(120000);
      expect(scanOk, 'Clair scan must complete successfully').toBeTruthy();
      await authenticatedPage.goto(
        `/repository/${testRepo.fullName}/tag/latest?tab=securityreport`,
      );

      // Verify Security Report tab exists and is selected
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Security Report'}),
      ).toBeVisible();

      // The fix ensures OCI images are NOT marked as unsupported
      await expect(
        authenticatedPage.getByText('Security scan is not supported.'),
      ).not.toBeVisible();

      // Wait for scan to complete — reload if still queued
      const scanned = authenticatedPage.getByText(
        /detected \d+ vulnerabilit|detected no vulnerabilit/,
      );
      const deadline = Date.now() + 90000;
      while (Date.now() < deadline) {
        if (await scanned.isVisible().catch(() => false)) break;
        await authenticatedPage.waitForTimeout(5000);
        await authenticatedPage.reload();
        await authenticatedPage
          .getByRole('tab', {name: 'Security Report'})
          .click();
      }
      await expect(scanned).toBeVisible({timeout: 5000});

      await expect(
        authenticatedPage.locator('[data-testid="vulnerability-chart"]'),
      ).toBeVisible();
    });

    test('OCI-format image packages tab renders', async ({
      authenticatedPage,
    }) => {
      test.setTimeout(120000);
      expect(scanOk, 'Clair scan must complete successfully').toBeTruthy();
      await authenticatedPage.goto(
        `/repository/${testRepo.fullName}/tag/latest?tab=packages`,
      );

      const packages = authenticatedPage.getByText(
        /recognized \d+ package|does not recognize any package/,
      );
      const deadline = Date.now() + 90000;
      while (Date.now() < deadline) {
        if (await packages.isVisible().catch(() => false)) break;
        await authenticatedPage.waitForTimeout(5000);
        await authenticatedPage.reload();
      }
      await expect(packages).toBeVisible({timeout: 5000});

      await expect(
        authenticatedPage.locator('[data-testid="packages-chart"]'),
      ).toBeVisible();
    });
  },
);
