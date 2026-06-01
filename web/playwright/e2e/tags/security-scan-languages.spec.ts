import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {pushExternalImage} from '../../utils/container';
import type {Page} from '@playwright/test';

/**
 * Language/distro-specific Clair vulnerability scanning tests.
 *
 * Migrated from Cypress OCP-71140 through OCP-73428 in quay-tests.
 * Each test pushes a known-vulnerable image for a specific ecosystem,
 * waits for Clair to scan it, then verifies expected CVEs appear in
 * the Security Report UI.
 */

// Maximum time to wait for Clair to finish scanning an image.
const SCAN_TIMEOUT_MS = 180_000;

// Poll interval when waiting for scan completion.
const SCAN_POLL_MS = 5_000;

type Vulnerability = [advisory: string, pkg: string, severity: string];

interface EcosystemConfig {
  name: string;
  ocpId: string;
  sourceImage: string;
  tag: string;
  copyAll?: boolean;
  arch?: string;
  vulnerabilities: Vulnerability[];
}

const ECOSYSTEMS: EcosystemConfig[] = [
  {
    name: 'Golang',
    ocpId: 'OCP-71140',
    sourceImage: 'quay.io/quay-qetest/golang-migrate',
    tag: 'v4.15.2',
    vulnerabilities: [
      ['CVE-2023-24538', 'stdlib', 'Critical'],
      ['CVE-2024-34156', 'stdlib', 'High'],
    ],
  },
  {
    name: 'NodeJS',
    ocpId: 'OCP-71146',
    sourceImage: 'quay.io/quay-qetest/nodejs-test-image',
    tag: 'latest',
    vulnerabilities: [
      ['CVE-2016-7099', 'nodejs010-nodejs', 'High'],
      ['CVE-2015-0278', 'nodejs010-libuv', 'Medium'],
    ],
  },
  {
    name: 'Ruby',
    ocpId: 'OCP-71191',
    sourceImage: 'quay.io/quay-qetest/ruby',
    tag: '3.3.5-bullseye',
    vulnerabilities: [
      ['GHSA-2rxp-v6pw-ch6m', 'rexml', 'High'],
      ['CVE-2024-49761', 'rexml', 'High'],
    ],
  },
  {
    name: 'Java',
    ocpId: 'OCP-71211',
    sourceImage: 'quay.io/quay-qetest/clair-java-test',
    tag: 'latest',
    vulnerabilities: [['GHSA-2qrg-x229-3v8q', 'log4j:log4j', 'Critical']],
  },
  {
    name: 'Python',
    ocpId: 'OCP-71217',
    sourceImage: 'quay.io/quay-qetest/python3-test-image',
    tag: 'latest',
    vulnerabilities: [
      ['CVE-2024-9287', 'python3.10-minimal', 'Medium'],
      ['CVE-2024-0450', 'libpython3.10-stdlib', 'Medium'],
    ],
  },
  {
    name: 'Alpine Edge',
    ocpId: 'OCP-71256',
    sourceImage: 'quay.io/quay-qetest/alpine',
    tag: 'edge',
    vulnerabilities: [
      ['CVE-2023-42363', 'busybox', 'Medium'],
      ['CVE-2023-42364', 'busybox-binsh', 'Medium'],
    ],
  },
  {
    name: 'Dotnet',
    ocpId: 'OCP-71487',
    sourceImage: 'quay.io/quay-qetest/clair-dotnet-test',
    tag: 'latest',
    vulnerabilities: [['CVE-2024-43485', 'System.Text.Json', 'High']],
  },
  {
    name: 'Oracle Linux',
    ocpId: 'OCP-73423',
    sourceImage: 'quay.io/quay-qetest/oraclelinux',
    tag: 'latest',
    vulnerabilities: [
      ['ELSA-2021-1989', 'bind-export-libs', 'High'],
      ['ELSA-2023-5455', 'glibc-common', 'High'],
      ['ELSA-2023-5455', 'glibc-all-langpacks', 'High'],
      ['ELSA-2023-1405', 'openssl-libs', 'High'],
      ['ELSA-2023-3591', 'python3-libs', 'High'],
    ],
  },
  {
    name: 'Amazon Linux',
    ocpId: 'OCP-73424',
    sourceImage: 'quay.io/quay-qetest/amazonlinux',
    tag: 'latest',
    vulnerabilities: [
      ['ALAS2-2022-1764', 'expat', 'Critical'],
      ['ALAS2-2024-2521', 'libcrypt', 'High'],
      ['ALAS2-2023-1980', 'python-libs', 'High'],
      ['ALAS2-2023-1935', 'openssl-libs', 'High'],
      ['ALAS2-2023-1980', 'python', 'High'],
    ],
  },
  {
    name: 'Ubuntu',
    ocpId: 'OCP-73426',
    sourceImage: 'quay.io/quay-qetest/ubuntu',
    tag: 'latest',
    copyAll: true,
    arch: 'linux on amd64',
    vulnerabilities: [
      ['CVE-2023-4911', 'libc-bin', 'High'],
      ['CVE-2023-4911', 'libc6', 'High'],
      ['CVE-2022-3602', 'libssl3', 'High'],
      ['CVE-2022-3786', 'libssl3', 'High'],
    ],
  },
  {
    name: 'Debian',
    ocpId: 'OCP-73427',
    sourceImage: 'quay.io/quay-qetest/debian',
    tag: 'latest',
    copyAll: true,
    arch: 'linux on amd64',
    vulnerabilities: [
      ['CVE-2016-2781', 'coreutils', 'Medium'],
      ['CVE-2024-26461', 'libkrb5-3', 'Low'],
      ['TEMP-0841856-B18BAF', 'bash', 'Low'],
    ],
  },
  {
    name: 'Alpine',
    ocpId: 'OCP-73428',
    sourceImage: 'quay.io/quay-qetest/alpine',
    tag: 'latest',
    copyAll: true,
    arch: 'linux on 386',
    vulnerabilities: [
      ['CVE-2022-37434', 'zlib', 'Critical'],
      ['CVE-2023-0286', 'libssl1.1', 'High'],
      ['CVE-2023-0286', 'libcrypto1.1', 'High'],
      ['CVE-2022-30065', 'busybox', 'High'],
      ['CVE-2022-30065', 'ssl_client', 'High'],
    ],
  },
];

async function waitForScan(
  api: ApiClient,
  namespace: string,
  repo: string,
  digest: string,
): Promise<void> {
  const deadline = Date.now() + SCAN_TIMEOUT_MS;
  while (Date.now() < deadline) {
    try {
      const sec = await api.getManifestSecurity(namespace, repo, digest);
      if (sec.status !== 'queued') return;
    } catch (e: unknown) {
      if (e instanceof Error && !e.message.includes('404')) throw e;
    }
    await new Promise((r) => setTimeout(r, SCAN_POLL_MS));
  }
}

async function selectArchitecture(page: Page, arch: string): Promise<void> {
  const archSelect = page.getByTestId('arch-select');
  await archSelect.click();
  await page.getByTestId('arch-option').filter({hasText: arch}).click();
}

async function verifyVulnerability(
  page: Page,
  advisory: string,
  pkg: string,
  severity: string,
): Promise<void> {
  const filterInput = page.locator(
    'input[placeholder="Filter Vulnerabilities..."]',
  );
  await filterInput.fill(advisory);

  const row = page
    .locator('tbody tr')
    .filter({hasText: advisory})
    .filter({hasText: pkg});
  await expect(row).toBeVisible({timeout: 10_000});
  await expect(row.locator('td[data-label="Severity"]')).toContainText(
    severity,
  );

  await filterInput.clear();
}

for (const ecosystem of ECOSYSTEMS) {
  test.describe(
    `${ecosystem.name} Security Scan (${ecosystem.ocpId})`,
    {
      tag: [
        '@tags',
        '@container',
        '@feature:SECURITY_SCANNER',
        '@slow',
        `@${ecosystem.ocpId}`,
        '@PROJQUAY-11630',
      ],
    },
    () => {
      let testRepo: {namespace: string; name: string; fullName: string};

      test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
        test.setTimeout(300_000);
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
          ecosystem.copyAll,
        );

        const tags = await api.getTags(testRepo.namespace, testRepo.name);
        const tag = tags.tags.find((t) => t.name === ecosystem.tag);
        if (!tag) throw new Error(`Tag ${ecosystem.tag} not found after push`);

        await waitForScan(
          api,
          testRepo.namespace,
          testRepo.name,
          tag.manifest_digest,
        );
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

      test(`Clair reports expected CVEs for ${ecosystem.name}`, async ({
        authenticatedPage,
      }) => {
        test.setTimeout(120_000);

        await authenticatedPage.goto(
          `/repository/${testRepo.fullName}/tag/${ecosystem.tag}?tab=securityreport`,
        );

        if (ecosystem.arch) {
          await selectArchitecture(authenticatedPage, ecosystem.arch);
        }

        const scanned = authenticatedPage.getByText(
          /detected \d+ vulnerabilit|detected no vulnerabilit/,
        );
        const deadline = Date.now() + 90_000;
        while (Date.now() < deadline) {
          if (await scanned.isVisible().catch(() => false)) break;
          await authenticatedPage.waitForTimeout(5_000);
          await authenticatedPage.reload();
          await authenticatedPage
            .getByRole('tab', {name: 'Security Report'})
            .click();
          if (ecosystem.arch) {
            await selectArchitecture(authenticatedPage, ecosystem.arch);
          }
        }
        await expect(scanned).toBeVisible({timeout: 5_000});

        await expect(
          authenticatedPage.locator('[data-testid="vulnerability-chart"]'),
        ).toBeVisible();

        for (const [advisory, pkg, severity] of ecosystem.vulnerabilities) {
          await verifyVulnerability(authenticatedPage, advisory, pkg, severity);
        }
      });
    },
  );
}

test.describe(
  'Oracle Linux Generic Scan (OCP-73425)',
  {
    tag: [
      '@tags',
      '@container',
      '@feature:SECURITY_SCANNER',
      '@slow',
      '@OCP-73425',
      '@PROJQUAY-11630',
    ],
  },
  () => {
    let testRepo: {namespace: string; name: string; fullName: string};

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      test.setTimeout(300_000);
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
        'quay.io/quay-qetest/oraclelinux:latest',
        testRepo.namespace,
        testRepo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const tags = await api.getTags(testRepo.namespace, testRepo.name);
      const digest = tags.tags[0].manifest_digest;
      await waitForScan(api, testRepo.namespace, testRepo.name, digest);
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
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();

      const securityCell = authenticatedPage
        .locator('tr')
        .filter({hasText: 'latest'})
        .locator('td')
        .nth(3);

      await expect(securityCell).toHaveText(
        /None Detected|Critical|High|Medium|Low|Unknown/,
        {timeout: 30_000},
      );
    });
  },
);
