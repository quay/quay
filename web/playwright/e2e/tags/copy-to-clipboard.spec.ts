import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {pushImage} from '../../utils/container';

test.describe(
  'Tags - Copy to Clipboard Functionality',
  {tag: ['@tags', '@copy', '@repository']},
  () => {
    let testRepo: {namespace: string; name: string; fullName: string};

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      // Skip setup if no container runtime
      if (!cachedContainerAvailable) return;

      const api = new ApiClient(userContext.request);
      const repoName = `copy-test-${Date.now()}`;
      await api.createRepository(TEST_USERS.user.username, repoName, 'private');

      testRepo = {
        namespace: TEST_USERS.user.username,
        name: repoName,
        fullName: `${TEST_USERS.user.username}/${repoName}`,
      };

      // Push two test images to verify persistence and state switching
      await pushImage(
        testRepo.namespace,
        testRepo.name,
        'tag1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await pushImage(
        testRepo.namespace,
        testRepo.name,
        'tag2',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
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

    test('verifies copy to clipboard behavior, tooltip persistence, and state switching', async ({
      authenticatedPage,
    }) => {
      // Grant clipboard permissions on the actual browser context used by authenticatedPage
      await authenticatedPage
        .context()
        .grantPermissions(['clipboard-read', 'clipboard-write']);
      // Navigate to the repository tags page
      await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);

      // Wait for table to load
      await expect(authenticatedPage.getByText('tag2')).toBeVisible();

      // --- SETUP: Identify Rows and Cells ---
      const tag1Row = authenticatedPage.locator('tr').filter({
        has: authenticatedPage.getByRole('link', {name: 'tag1', exact: true}),
      });
      const tag1NameCell = tag1Row.locator('td').filter({
        has: authenticatedPage.getByRole('link', {name: 'tag1', exact: true}),
      });
      const tag2Row = authenticatedPage.locator('tr').filter({
        has: authenticatedPage.getByRole('link', {name: 'tag2', exact: true}),
      });
      const tag2NameCell = tag2Row.locator('td').filter({
        has: authenticatedPage.getByRole('link', {name: 'tag2', exact: true}),
      });

      // --- STEP 1: Verify Default Tooltips ---
      // Hover Tag 1 Name -> "Copy pull spec"
      await tag1NameCell.hover();
      const tag1CopyButton = tag1NameCell.getByLabel(
        'Copy pull spec to clipboard',
      );
      await expect(tag1CopyButton).toBeVisible();
      await tag1CopyButton.hover();
      await expect(authenticatedPage.getByText('Copy pull spec')).toBeVisible();

      // Hover Tag 2 Name -> "Copy pull spec"
      await tag2NameCell.hover();
      const tag2CopyButton = tag2NameCell.getByLabel(
        'Copy pull spec to clipboard',
      );
      await expect(tag2CopyButton).toBeVisible();
      await tag2CopyButton.hover();
      await expect(authenticatedPage.getByText('Copy pull spec')).toBeVisible();

      // --- STEP 2: Copy Tag 1 and Verify Persistence ---
      await tag1NameCell.hover();
      await tag1CopyButton.click();

      // Verify Tag 1 tooltip changes to "Copied to clipboard!"
      await expect(
        authenticatedPage.getByText('Copied to clipboard!'),
      ).toBeVisible();

      // Verify clipboard content
      let clipboardContent = await authenticatedPage.evaluate(() =>
        navigator.clipboard.readText(),
      );
      expect(clipboardContent).toContain(`${testRepo.fullName}:tag1`);

      // Verify persistence: Wait 3 seconds, verify tooltip is STILL "Copied to clipboard!"
      // We move mouse slightly to ensure it's not re-triggering hover logic freshly,
      // but purely waiting for timeout (which shouldn't exist).
      await authenticatedPage.waitForTimeout(3000);
      await expect(
        authenticatedPage.getByText('Copied to clipboard!'),
      ).toBeVisible();

      // --- STEP 3: Verify Tag 2 is UNCHANGED ---
      await tag2NameCell.hover();
      await tag2CopyButton.hover();
      await expect(authenticatedPage.getByText('Copy pull spec')).toBeVisible();

      // --- STEP 4: Copy Tag 2 and Verify State Switch ---
      await tag2CopyButton.click();

      // Verify Tag 2 is now Copied
      await expect(
        authenticatedPage.getByText('Copied to clipboard!'),
      ).toBeVisible();
      clipboardContent = await authenticatedPage.evaluate(() =>
        navigator.clipboard.readText(),
      );
      expect(clipboardContent).toContain(`${testRepo.fullName}:tag2`);

      // --- STEP 5: Verify Tag 1 REVERTED to Default ---
      await tag1NameCell.hover();
      await tag1CopyButton.hover();
      await expect(authenticatedPage.getByText('Copy pull spec')).toBeVisible();

      // --- STEP 6: Verify Digest Copy and State Switch ---
      const tag1DigestCell = tag1Row
        .locator('td')
        .filter({has: authenticatedPage.getByText('sha256:')});
      await tag1DigestCell.hover();
      const tag1DigestButton = tag1DigestCell.getByLabel(
        'Copy manifest digest to clipboard',
      );

      // Check default digest tooltip
      await tag1DigestButton.hover();
      await expect(authenticatedPage.getByText('Copy digest')).toBeVisible();

      // Click digest copy
      await tag1DigestButton.click();

      // Verify Copied state
      await expect(
        authenticatedPage.getByText('Copied to clipboard!'),
      ).toBeVisible();

      // Verify clipboard
      clipboardContent = await authenticatedPage.evaluate(() =>
        navigator.clipboard.readText(),
      );
      expect(clipboardContent).toMatch(/^sha256:[a-f0-9]{64}$/);

      // Verify Tag 2 (previous active copy) REVERTED
      await tag2NameCell.hover();
      // We need to re-hover button to trigger tooltip
      await tag2CopyButton.hover();
      await expect(authenticatedPage.getByText('Copy pull spec')).toBeVisible();
    });
  },
);
