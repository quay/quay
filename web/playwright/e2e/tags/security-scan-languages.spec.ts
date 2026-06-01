import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {pushExternalImage} from '../../utils/container';

/**
 * Language/distro-specific Clair vulnerability scanning tests.
 *
 * Migrated from Cypress quay-tests. Each test pushes a known-vulnerable
 * image for a specific ecosystem, waits for Clair to scan it, then
 * verifies the Security Report UI shows vulnerabilities were detected.
 */

interface EcosystemConfig {
  name: string;
  sourceImage: string;
  tag: string;
}

const ECOSYSTEMS: EcosystemConfig[] = [
  {
    name: 'Golang',
    sourceImage: 'quay.io/projectquay/golang',
    tag: '1.17',
  },
  {
    name: 'NodeJS',
    sourceImage: 'quay.io/centos7/nodejs-10-centos7',
    tag: '10',
  },
  {
    name: 'Ruby',
    sourceImage: 'quay.io/centos7/ruby-25-centos7',
    tag: '2.5',
  },
  {
    name: 'Java',
    sourceImage: 'quay.io/wildfly/wildfly-centos7',
    tag: '24.0',
  },
  {
    name: 'Python',
    sourceImage: 'quay.io/centos7/python-38-centos7',
    tag: 'centos7',
  },
  {
    name: 'Dotnet',
    sourceImage: 'quay.io/contrast/agent-dotnet-core',
    tag: '5.0.5',
  },
  {
    name: 'Oracle Linux',
    sourceImage: 'quay.io/nvlab/oraclelinux',
    tag: '7.8',
  },
  {
    name: 'Amazon Linux',
    sourceImage: 'quay.io/toolbx-images/amazonlinux-toolbox',
    tag: '2',
  },
  {
    name: 'Ubuntu',
    sourceImage: 'quay.io/toolbx/ubuntu-toolbox',
    tag: '20.04',
  },
  {
    name: 'Debian',
    sourceImage: 'quay.io/toolbx-images/debian-toolbox',
    tag: '12',
  },
  {
    name: 'Alpine',
    sourceImage: 'quay.io/libpod/alpine',
    tag: '3.2',
  },
];

for (const ecosystem of ECOSYSTEMS) {
  test.describe(
    `${ecosystem.name} Security Scan`,
    {
      tag: [
        '@tags',
        '@container',
        '@feature:SECURITY_SCANNER',
        '@slow',
        '@PROJQUAY-11630',
      ],
    },
    () => {
      let testRepo: {namespace: string; name: string; fullName: string};
      let scanOk: boolean;

      test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
        test.setTimeout(600_000);
        test.skip(!cachedContainerAvailable, 'No container runtime available');

        const api = new ApiClient(userContext.request);
        const repoName = `secscan-${ecosystem.name
          .toLowerCase()
          .replace(/\s+/g, '-')}-${Date.now()}`;
        await api.createRepository(
          TEST_USERS.user.username,
          repoName,
          'public',
        );

        testRepo = {
          namespace: TEST_USERS.user.username,
          name: repoName,
          fullName: `${TEST_USERS.user.username}/${repoName}`,
        };

        await pushExternalImage(
          `${ecosystem.sourceImage}:${ecosystem.tag}`,
          testRepo.namespace,
          testRepo.name,
          ecosystem.tag,
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        const tags = await api.getTags(testRepo.namespace, testRepo.name);
        const tag = tags.tags.find((t) => t.name === ecosystem.tag);
        if (!tag) throw new Error(`Tag ${ecosystem.tag} not found after push`);

        const scanResult = await api.waitForScan(
          testRepo.namespace,
          testRepo.name,
          tag.manifest_digest,
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

      test(`Clair detects vulnerabilities in ${ecosystem.name}`, async ({
        authenticatedPage,
      }) => {
        test.setTimeout(120_000);

        expect(scanOk, 'Clair scan must complete successfully').toBeTruthy();

        await authenticatedPage.goto(
          `/repository/${testRepo.fullName}/tag/${ecosystem.tag}?tab=securityreport`,
        );

        const scanned = authenticatedPage.getByText(
          /detected \d+ vulnerabilit/,
        );
        const noVulns = authenticatedPage.getByText(
          'detected no vulnerabilities',
        );
        const scanFailed = authenticatedPage.getByText(
          'Security scan has failed',
        );
        const scanUnsupported = authenticatedPage.getByText(
          'Security scan is not supported',
        );

        const deadline = Date.now() + 90_000;
        while (Date.now() < deadline) {
          if (await scanned.isVisible().catch(() => false)) break;
          if (await noVulns.isVisible().catch(() => false)) {
            expect(false, 'Clair detected no vulnerabilities').toBeTruthy();
          }
          if (await scanFailed.isVisible().catch(() => false)) {
            expect(false, 'Security scan has failed').toBeTruthy();
          }
          if (await scanUnsupported.isVisible().catch(() => false)) {
            expect(false, 'Security scan is not supported').toBeTruthy();
          }
          await authenticatedPage.waitForTimeout(5_000);
          await authenticatedPage.reload();
          await authenticatedPage
            .getByRole('tab', {name: 'Security Report'})
            .click();
        }

        await expect(scanned).toBeVisible({timeout: 5_000});

        await expect(
          authenticatedPage.locator('[data-testid="vulnerability-chart"]'),
        ).toBeVisible();
      });
    },
  );
}

test.describe(
  'Oracle Linux Generic Scan',
  {
    tag: [
      '@tags',
      '@container',
      '@feature:SECURITY_SCANNER',
      '@slow',
      '@PROJQUAY-11630',
    ],
  },
  () => {
    let testRepo: {namespace: string; name: string; fullName: string};

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      test.setTimeout(600_000);
      if (!cachedContainerAvailable) return;

      const api = new ApiClient(userContext.request);
      const repoName = `secscan-oraclelinux-generic-${Date.now()}`;
      await api.createRepository(TEST_USERS.user.username, repoName, 'public');

      testRepo = {
        namespace: TEST_USERS.user.username,
        name: repoName,
        fullName: `${TEST_USERS.user.username}/${repoName}`,
      };

      await pushExternalImage(
        'quay.io/nvlab/oraclelinux:7.8',
        testRepo.namespace,
        testRepo.name,
        '7.8',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const tags = await api.getTags(testRepo.namespace, testRepo.name);
      const digest = tags.tags[0].manifest_digest;
      await api.waitForScan(testRepo.namespace, testRepo.name, digest);
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

    test('Clair scans Oracle Linux and reports a security status', async ({
      authenticatedPage,
    }) => {
      test.setTimeout(120_000);

      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {name: '7.8'}),
      ).toBeVisible();

      const securityCell = authenticatedPage
        .locator('tr')
        .filter({hasText: '7.8'})
        .locator('td')
        .nth(3);

      await expect(securityCell).toHaveText(
        /None Detected|Critical|High|Medium|Low|Unknown/,
        {timeout: 30_000},
      );
    });
  },
);
