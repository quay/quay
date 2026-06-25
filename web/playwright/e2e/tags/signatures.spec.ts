import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {pushImage} from '../../utils/container';

test.describe(
  'Tags - Show/Hide Signatures',
  {tag: ['@tags', '@container']},
  () => {
    let testRepo: {namespace: string; name: string; fullName: string};
    let sigTagPrefix: string;

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      if (!cachedContainerAvailable) return;

      const api = new ApiClient(userContext.request);
      const repoName = `signatures-${Date.now()}`;
      await api.createRepository(TEST_USERS.user.username, repoName, 'private');

      testRepo = {
        namespace: TEST_USERS.user.username,
        name: repoName,
        fullName: `${TEST_USERS.user.username}/${repoName}`,
      };

      // Push an image to get a manifest with a known digest
      await pushImage(
        testRepo.namespace,
        testRepo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Poll for the tag to be indexed (push is sync but indexing may lag)
      let digest: string | undefined;
      for (let attempt = 0; attempt < 10; attempt++) {
        const tags = await api.getTags(testRepo.namespace, testRepo.name, {
          specificTag: 'latest',
        });
        if (tags.tags.length > 0) {
          digest = tags.tags[0].manifest_digest;
          break;
        }
        await new Promise((r) => setTimeout(r, 1000));
      }
      if (!digest) {
        throw new Error('Pushed tag was not indexed after 10 attempts');
      }

      // Build cosign-style signature tag prefix: sha256-<hex>
      // Digest format: "sha256:<hex>" → tag prefix: "sha256-<hex>"
      sigTagPrefix = digest.replace(':', '-');

      // Create signature tags pointing to the same manifest
      // These are just regular tags with cosign-convention names
      for (const suffix of ['.sig', '.sbom', '.att']) {
        await api.createTag(
          testRepo.namespace,
          testRepo.name,
          `${sigTagPrefix}${suffix}`,
          digest,
        );
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

    test('hides signature tags by default, shows when toggled, hides again when toggled off', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);

      // Wait for regular tags to load
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();

      // Verify signature tags are hidden by default
      await expect(
        authenticatedPage.getByRole('link', {name: `${sigTagPrefix}.sig`}),
      ).not.toBeAttached();
      await expect(
        authenticatedPage.getByRole('link', {name: `${sigTagPrefix}.sbom`}),
      ).not.toBeAttached();
      await expect(
        authenticatedPage.getByRole('link', {name: `${sigTagPrefix}.att`}),
      ).not.toBeAttached();

      // Open settings and toggle "Show Signatures" on
      const settingsToggle = authenticatedPage.locator('#tags-settings-toggle');
      await settingsToggle.click();
      const sigMenuItem = authenticatedPage.getByRole('menuitem', {
        name: /Show Signatures/,
      });
      await sigMenuItem.click();
      await settingsToggle.click();

      // Verify signature tags are now visible
      await expect(
        authenticatedPage.getByRole('link', {name: `${sigTagPrefix}.sig`}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: `${sigTagPrefix}.sbom`}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: `${sigTagPrefix}.att`}),
      ).toBeVisible();

      // Regular tags should still be visible
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();

      // Verify checkbox is checked
      await settingsToggle.click();
      await expect(sigMenuItem.getByRole('checkbox')).toBeChecked();

      // Toggle "Show Signatures" off
      await sigMenuItem.click();
      await settingsToggle.click();

      // Verify signature tags are hidden again
      await expect(
        authenticatedPage.getByRole('link', {name: `${sigTagPrefix}.sig`}),
      ).not.toBeAttached();
      await expect(
        authenticatedPage.getByRole('link', {name: `${sigTagPrefix}.sbom`}),
      ).not.toBeAttached();
      await expect(
        authenticatedPage.getByRole('link', {name: `${sigTagPrefix}.att`}),
      ).not.toBeAttached();

      // Regular tags should still be visible
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();

      // Verify checkbox is unchecked
      await settingsToggle.click();
      await expect(sigMenuItem.getByRole('checkbox')).not.toBeChecked();
      await settingsToggle.click();
    });
  },
);
