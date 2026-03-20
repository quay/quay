import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {pushImage} from '../../utils/container';

test.describe(
  'Security Scan',
  {tag: ['@tags', '@container', '@feature:SECURITY_SCANNER']},
  () => {
    let testRepo: {namespace: string; name: string; fullName: string};

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      if (!cachedContainerAvailable) return;

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

      // Wait for Clair to scan the image (poll until status != queued)
      const tags = await api.getTags(testRepo.namespace, testRepo.name);
      const digest = tags.tags[0].manifest_digest;
      const deadline = Date.now() + 120000;
      while (Date.now() < deadline) {
        const sec = await api.getManifestSecurity(
          testRepo.namespace,
          testRepo.name,
          digest,
        );
        if (sec.status !== 'queued') break;
        await new Promise((r) => setTimeout(r, 5000));
      }
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
      // Should show either vulnerabilities detected or no vulnerabilities
      await expect(
        authenticatedPage.getByText(
          /detected \d+ vulnerabilit|detected no vulnerabilit/,
        ),
      ).toBeVisible({timeout: 10000});

      // Click Packages tab - verify packages are listed
      await authenticatedPage.getByRole('tab', {name: 'Packages'}).click();
      await expect(authenticatedPage).toHaveURL(/tab=packages/);
    });
  },
);
