import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {pushImage, pushMultiArchImage} from '../../utils/container';

test.describe('Tag Details Page', {tag: ['@tags', '@container']}, () => {
  let testRepo: {namespace: string; name: string; fullName: string};
  let latestDigest: string;

  test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
    test.setTimeout(120000);
    if (!cachedContainerAvailable) return;

    const api = new ApiClient(userContext.request);
    const repoName = `tag-details-${Date.now()}`;
    await api.createRepository(TEST_USERS.user.username, repoName, 'private');

    testRepo = {
      namespace: TEST_USERS.user.username,
      name: repoName,
      fullName: `${TEST_USERS.user.username}/${repoName}`,
    };

    // Push single-arch and multi-arch images
    await pushImage(
      testRepo.namespace,
      testRepo.name,
      'latest',
      TEST_USERS.user.username,
      TEST_USERS.user.password,
    );
    await pushMultiArchImage(
      testRepo.namespace,
      testRepo.name,
      'manifestlist',
      TEST_USERS.user.username,
      TEST_USERS.user.password,
    );

    // Fetch the latest tag digest for assertions
    const tags = await api.getTags(testRepo.namespace, testRepo.name, {
      specificTag: 'latest',
    });
    expect(tags.tags.length).toBeGreaterThan(0);
    latestDigest = tags.tags[0].manifest_digest;
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

  test('renders tag details with name, digest, size, and pull commands', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto(`/repository/${testRepo.fullName}/tag/latest`);

    // Verify details tab fields
    await expect(authenticatedPage.getByTestId('name')).toContainText('latest');
    await expect(authenticatedPage.getByTestId('creation')).toContainText(
      /\d{4}/,
    );
    await expect(authenticatedPage.getByTestId('repository')).toContainText(
      testRepo.name,
    );
    await expect(authenticatedPage.getByTestId('modified')).toContainText(
      /\d{4}/,
    );
    // digest-clipboardcopy uses variant="inline-compact" which renders a
    // <span>, not an <input> — use toContainText instead of toHaveValue
    await expect(
      authenticatedPage.getByTestId('digest-clipboardcopy'),
    ).toContainText(latestDigest);
    await expect(authenticatedPage.getByTestId('size')).toHaveText(
      /[\d.]+\s*[kKMG]?B/,
    );

    // Verify pull commands section
    const pullCommands = authenticatedPage.getByTestId('copy-pull-commands');
    await expect(pullCommands).toContainText('Podman Pull (by tag)');
    await expect(pullCommands).toContainText('Docker Pull (by tag)');
    await expect(pullCommands).toContainText('Podman Pull (by digest)');
    await expect(pullCommands).toContainText('Docker Pull (by digest)');

    // ClipboardCopy renders text in an <input>, so use toHaveValue on the inner input
    await expect(
      authenticatedPage
        .getByTestId('podman-tag-clipboardcopy')
        .locator('input'),
    ).toHaveValue(new RegExp(`podman pull .+/${testRepo.fullName}:latest`));
    await expect(
      authenticatedPage
        .getByTestId('docker-tag-clipboardcopy')
        .locator('input'),
    ).toHaveValue(new RegExp(`docker pull .+/${testRepo.fullName}:latest`));
    await expect(
      authenticatedPage
        .getByTestId('podman-digest-clipboardcopy')
        .locator('input'),
    ).toHaveValue(
      new RegExp(`podman pull .+/${testRepo.fullName}@${latestDigest}`),
    );
    await expect(
      authenticatedPage
        .getByTestId('docker-digest-clipboardcopy')
        .locator('input'),
    ).toHaveValue(
      new RegExp(`docker pull .+/${testRepo.fullName}@${latestDigest}`),
    );

    // Verify Layers tab exists (Manifest tab was removed from the UI)
    await expect(
      authenticatedPage.getByRole('tab', {name: 'Layers'}),
    ).toBeVisible();
  });

  test('switching architecture updates the displayed digest', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto(
      `/repository/${testRepo.fullName}/tag/manifestlist`,
    );

    // Verify architecture selector is visible
    const archSelector = authenticatedPage.getByRole('button', {
      name: /linux on amd64/i,
    });
    await expect(archSelector).toBeVisible();

    // digest-clipboardcopy uses variant="inline-compact" (no <input>)
    const digestEl = authenticatedPage.getByTestId('digest-clipboardcopy');
    const initialDigest = (await digestEl.textContent()) ?? '';

    // Switch to arm64
    await archSelector.click();
    await authenticatedPage
      .getByRole('option', {name: /linux on arm64/i})
      .click();

    // Verify digest changed
    await expect(digestEl).not.toHaveText(initialDigest);
  });
});

test.describe(
  'Tag Details - Vulnerability Badge',
  {tag: ['@tags', '@container', '@feature:SECURITY_SCANNER']},
  () => {
    let testRepo: {namespace: string; name: string; fullName: string};
    let scanStatus = 'queued';

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      test.setTimeout(180000);
      if (!cachedContainerAvailable) return;

      const api = new ApiClient(userContext.request);
      const repoName = `tag-vuln-badge-${Date.now()}`;
      // Public so Clair can pull and scan the image
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
      const tags = await api.getTags(testRepo.namespace, testRepo.name, {
        specificTag: 'latest',
      });
      expect(tags.tags.length).toBeGreaterThan(0);
      const digest = tags.tags[0].manifest_digest;
      const deadline = Date.now() + 120000;
      while (Date.now() < deadline) {
        try {
          const sec = await api.getManifestSecurity(
            testRepo.namespace,
            testRepo.name,
            digest,
          );
          if (sec.status) {
            scanStatus = sec.status;
            if (scanStatus !== 'queued') break;
          }
        } catch (e: unknown) {
          // 404 expected until Clair indexes the manifest; rethrow others
          if (e instanceof Error && !e.message.includes('404')) throw e;
        }
        await new Promise((r) => setTimeout(r, 5000));
      }

      if (scanStatus === 'queued') {
        throw new Error('Clair scan did not complete within the 120s deadline');
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

    test('vulnerability badge navigates to security report tab', async ({
      authenticatedPage,
    }) => {
      test.skip(
        scanStatus !== 'scanned',
        `Clair scan status is "${scanStatus}", cannot test vulnerability badge`,
      );

      await authenticatedPage.goto(
        `/repository/${testRepo.fullName}/tag/latest`,
      );

      // Wait for vulnerability badge to render
      const vulnBadge = authenticatedPage.getByTestId('vulnerabilities');
      await expect(vulnBadge).toContainText(
        /(\d+\s+(Critical|High|Medium|Low|Unknown)|No vulnerabilities|Passed|Unsupported)/i,
        {timeout: 15000},
      );

      // Unsupported images have no vulnerability data to click through
      const badgeText = await vulnBadge.textContent();
      if (badgeText?.includes('Unsupported')) return;

      await vulnBadge.locator('a, button').first().click();
      await expect(authenticatedPage).toHaveURL(/tab=securityreport/);
      await expect(
        authenticatedPage.getByText(
          /detected \d+ vulnerabilit|detected no vulnerabilit/,
        ),
      ).toBeVisible({timeout: 10000});
    });
  },
);
