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
    await expect(authenticatedPage.getByTestId('creation')).not.toBeEmpty();
    await expect(authenticatedPage.getByTestId('repository')).toContainText(
      testRepo.name,
    );
    await expect(authenticatedPage.getByTestId('modified')).not.toBeEmpty();
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
    const archSelector = authenticatedPage.getByText(/linux on amd64/i);
    await expect(archSelector).toBeVisible();

    // Capture initial digest
    const initialDigest =
      (await authenticatedPage
        .getByTestId('digest-clipboardcopy')
        .textContent()) ?? '';

    // Switch to arm64
    await archSelector.click();
    await authenticatedPage.getByText(/linux on arm64/i).click();

    // Verify digest changed
    await expect(
      authenticatedPage.getByTestId('digest-clipboardcopy'),
    ).not.toHaveText(initialDigest);
  });
});

test.describe(
  'Tag Details - Vulnerability Badge',
  {tag: ['@tags', '@container', '@feature:SECURITY_SCANNER']},
  () => {
    let testRepo: {namespace: string; name: string; fullName: string};

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
      const tags = await api.getTags(testRepo.namespace, testRepo.name);
      const digest = tags.tags[0].manifest_digest;
      const deadline = Date.now() + 120000;
      while (Date.now() < deadline) {
        try {
          const sec = await api.getManifestSecurity(
            testRepo.namespace,
            testRepo.name,
            digest,
          );
          if (sec.status !== 'queued') break;
        } catch (e: unknown) {
          // 404 expected until Clair indexes the manifest; rethrow others
          if (e instanceof Error && !e.message.includes('404')) throw e;
        }
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

    test('vulnerability badge navigates to security report tab', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(
        `/repository/${testRepo.fullName}/tag/latest`,
      );

      // Verify vulnerability badge shows a severity count and navigates
      const vulnBadge = authenticatedPage.getByTestId('vulnerabilities');
      await expect(vulnBadge).toContainText(
        /\d+\s+(Critical|High|Medium|Low|Unknown)/i,
        {timeout: 15000},
      );

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
