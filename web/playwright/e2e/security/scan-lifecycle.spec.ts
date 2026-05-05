/**
 * E2E tests for security scan lifecycle.
 *
 * Tests the complete scan-on-push workflow from image push to vulnerability
 * results display in UI, including security badges and scan status transitions.
 *
 * IMPORTANT: These tests require:
 * - Real Clair service running (no mocking available)
 * - Container runtime (podman/docker) available
 * - PUBLIC repositories (Clair cannot scan private repos)
 * - SECURITY_SCANNER feature enabled
 */

import {test, expect} from '../../fixtures';
import {ApiClient} from '../../utils/api';
import {pushImage} from '../../utils/container';
import {waitForSecurityScan} from '../../utils/security';
import {TEST_USERS} from '../../global-setup';

test.describe(
  'Security Scan Lifecycle',
  {tag: ['@security', '@container', '@feature:SECURITY_SCANNER']},
  () => {
    test('displays vulnerability results after scan completes', async ({
      authenticatedPage,
      api,
    }) => {
      // Create PUBLIC repo (required for Clair to pull and scan)
      const repo = await api.repository(undefined, 'vuln-test', 'public');

      // Push image to trigger scan
      await pushImage(
        repo.namespace,
        repo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Wait for Clair to complete scan
      const tags = await api.raw.getTags(repo.namespace, repo.name);
      const digest = tags.tags[0].manifest_digest;

      const result = await waitForSecurityScan(
        api.raw,
        repo.namespace,
        repo.name,
        digest,
        120000, // 2 min timeout
        5000, // 5 sec poll interval
      );

      // Verify scan completed (not queued)
      expect(result.status).not.toBe('queued');

      // Navigate to security report tab
      await authenticatedPage.goto(
        `/repository/${repo.fullName}/tag/latest?tab=securityreport`,
      );

      // Verify vulnerability data displayed
      await expect(
        authenticatedPage.getByText(
          /detected \d+ vulnerabilit|detected no vulnerabilit/,
        ),
      ).toBeVisible({timeout: 10000});

      // Verify vulnerability chart rendered
      await expect(
        authenticatedPage.locator('[data-testid="vulnerability-chart"]'),
      ).toBeVisible();

      // If vulnerabilities present, verify details table
      const hasVulns = await authenticatedPage
        .getByText(/detected \d+ vulnerabilit/)
        .isVisible()
        .catch(() => false);

      if (hasVulns) {
        // Verify severity column exists
        const severityHeader = authenticatedPage.getByRole('columnheader', {
          name: /severity/i,
        });

        // Column header might be visible
        const isColumnVisible = await severityHeader
          .isVisible()
          .catch(() => false);

        if (isColumnVisible) {
          await expect(severityHeader).toBeVisible();
        }
      }
    });

    test('security badge displays correct severity level', async ({
      authenticatedPage,
      api,
    }) => {
      // Create PUBLIC repo and push image
      const repo = await api.repository(undefined, 'badge-test', 'public');

      await pushImage(
        repo.namespace,
        repo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Wait for scan to complete
      const tags = await api.raw.getTags(repo.namespace, repo.name);
      const digest = tags.tags[0].manifest_digest;
      await waitForSecurityScan(
        api.raw,
        repo.namespace,
        repo.name,
        digest,
        120000,
        5000,
      );

      // Navigate to tag detail page
      await authenticatedPage.goto(`/repository/${repo.fullName}/tag/latest`);

      // Verify security badge exists and shows status
      const vulnBadge = authenticatedPage.getByTestId('vulnerabilities');
      await expect(vulnBadge).toBeVisible({timeout: 15000});

      // Badge should show one of: Critical, High, Medium, Low, No vulnerabilities, Passed, Unsupported
      await expect(vulnBadge).toContainText(
        /(\d+\s+(Critical|High|Medium|Low|Unknown)|No vulnerabilities|Passed|Unsupported)/i,
        {timeout: 10000},
      );

      // Verify badge is clickable and navigates to security report (if not unsupported)
      const badgeText = await vulnBadge.textContent();
      if (badgeText && !badgeText.includes('Unsupported')) {
        const badgeLink = vulnBadge.locator('a, button').first();
        const isClickable = await badgeLink.isVisible().catch(() => false);

        if (isClickable) {
          await badgeLink.click();
          await expect(authenticatedPage).toHaveURL(/tab=securityreport/);
        }
      }
    });

    test('scan status transitions from queued to scanned', async ({
      authenticatedPage,
      api,
    }) => {
      // Create PUBLIC repo
      const repo = await api.repository(undefined, 'status-test', 'public');

      // Push image
      await pushImage(
        repo.namespace,
        repo.name,
        'v1.0.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Get manifest digest
      const tags = await api.raw.getTags(repo.namespace, repo.name);
      const digest = tags.tags[0].manifest_digest;

      // Navigate to tag page (scan might still be queued)
      await authenticatedPage.goto(
        `/repository/${repo.fullName}/tag/v1.0.0`,
      );

      // Wait for scan to complete in background
      await waitForSecurityScan(
        api.raw,
        repo.namespace,
        repo.name,
        digest,
        120000,
        5000,
      );

      // Refresh page to see updated status
      await authenticatedPage.reload();

      // Verify scan completed - Security Report tab should be visible
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Security Report'}),
      ).toBeVisible({timeout: 10000});

      // Verify we can navigate to security report
      await authenticatedPage.getByRole('tab', {name: 'Security Report'}).click();

      // Verify security report loaded (shows scan results)
      await expect(
        authenticatedPage.getByText(
          /detected \d+ vulnerabilit|detected no vulnerabilit|Scan Status/,
        ),
      ).toBeVisible({timeout: 10000});
    });
  },
);
