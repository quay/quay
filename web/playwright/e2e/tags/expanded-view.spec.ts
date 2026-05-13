import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {pushMultiArchImage, pushImage} from '../../utils/container';

test.describe('Tags - Expanded View', {tag: ['@tags', '@container']}, () => {
  let testRepo: {namespace: string; name: string; fullName: string};

  test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
    if (!cachedContainerAvailable) return;

    const api = new ApiClient(userContext.request);
    const repoName = `expanded-view-${Date.now()}`;
    await api.createRepository(TEST_USERS.user.username, repoName, 'private');

    testRepo = {
      namespace: TEST_USERS.user.username,
      name: repoName,
      fullName: `${TEST_USERS.user.username}/${repoName}`,
    };

    // Push multi-arch image (creates manifest list tag)
    await pushMultiArchImage(
      testRepo.namespace,
      testRepo.name,
      'manifestlist',
      TEST_USERS.user.username,
      TEST_USERS.user.password,
    );

    // Push single-arch image
    await pushImage(
      testRepo.namespace,
      testRepo.name,
      'latest',
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

  test('compact by default, toggle to expanded shows digest and labels, toggle back to compact', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);
    await expect(
      authenticatedPage.getByRole('link', {name: 'latest'}),
    ).toBeVisible();

    const settingsToggle = authenticatedPage.locator('#tags-settings-toggle');

    // Verify compact view by default — no expanded rows
    await expect(authenticatedPage.locator('.expanded-row')).not.toBeAttached();

    // Verify expanded view checkbox is unchecked
    await settingsToggle.click();
    const expandedMenuItem = authenticatedPage.getByRole('menuitem', {
      name: /Expanded View/,
    });
    await expect(expandedMenuItem.getByRole('checkbox')).not.toBeChecked();

    // Toggle expanded view on
    await expandedMenuItem.click();
    await settingsToggle.click();

    // Verify expanded rows appear
    await expect(
      authenticatedPage.locator('.expanded-row').first(),
    ).toBeVisible();

    // Verify expanded content shows SHA256 digest
    const expandedContent = authenticatedPage.locator('.expanded-row-content');
    await expect(expandedContent.first()).toContainText('SHA256');

    // Verify labels section exists (shows key=value or "No labels found")
    await expect(expandedContent.first()).toBeVisible();

    // Verify expanded view checkbox is checked
    await settingsToggle.click();
    await expect(expandedMenuItem.getByRole('checkbox')).toBeChecked();

    // Toggle back to compact
    await expandedMenuItem.click();
    await settingsToggle.click();

    // Verify expanded rows are gone
    await expect(authenticatedPage.locator('.expanded-row')).not.toBeAttached();

    // Toggle to expanded again (verify toggle works multiple times)
    await settingsToggle.click();
    await expandedMenuItem.click();
    await settingsToggle.click();
    await expect(
      authenticatedPage.locator('.expanded-row').first(),
    ).toBeVisible();
  });

  test('preserves expanded view when switching tabs', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);
    await expect(
      authenticatedPage.getByRole('link', {name: 'latest'}),
    ).toBeVisible();

    // Enable expanded view
    const settingsToggle = authenticatedPage.locator('#tags-settings-toggle');
    await settingsToggle.click();
    await authenticatedPage
      .getByRole('menuitem', {name: /Expanded View/})
      .click();
    await settingsToggle.click();

    await expect(
      authenticatedPage.locator('.expanded-row').first(),
    ).toBeVisible();

    // Navigate to Information tab
    await authenticatedPage.getByRole('tab', {name: 'Information'}).click();

    // Navigate back to Tags tab
    await authenticatedPage.getByRole('tab', {name: 'Tags'}).click();

    // Verify expanded view is still enabled
    await expect(
      authenticatedPage.locator('.expanded-row').first(),
    ).toBeVisible();

    await settingsToggle.click();
    await expect(
      authenticatedPage
        .getByRole('menuitem', {name: /Expanded View/})
        .getByRole('checkbox'),
    ).toBeChecked();
    await settingsToggle.click();
  });

  test('shows expanded content for each visible tag', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);
    await expect(
      authenticatedPage.getByRole('link', {name: 'latest'}),
    ).toBeVisible();

    // Enable expanded view
    const settingsToggle = authenticatedPage.locator('#tags-settings-toggle');
    await settingsToggle.click();
    await authenticatedPage
      .getByRole('menuitem', {name: /Expanded View/})
      .click();
    await settingsToggle.click();

    // Count tag rows and expanded rows — should match
    const tagEntries = authenticatedPage.getByTestId('table-entry');
    const expandedRows = authenticatedPage.locator('.expanded-row');

    const tagCount = await tagEntries.count();
    await expect(expandedRows).toHaveCount(tagCount);
  });

  test('works with manifest list expansion', async ({authenticatedPage}) => {
    await authenticatedPage.goto(`/repository/${testRepo.fullName}?tab=tags`);
    await expect(
      authenticatedPage.getByRole('link', {name: 'manifestlist'}),
    ).toBeVisible();

    // Enable expanded view
    const settingsToggle = authenticatedPage.locator('#tags-settings-toggle');
    await settingsToggle.click();
    await authenticatedPage
      .getByRole('menuitem', {name: /Expanded View/})
      .click();
    await settingsToggle.click();

    // Expanded rows should exist
    await expect(
      authenticatedPage.locator('.expanded-row').first(),
    ).toBeVisible();

    // Expand the manifest list to show child manifests
    const manifestlistRow = authenticatedPage
      .getByTestId('table-entry')
      .filter({
        has: authenticatedPage.getByRole('link', {name: 'manifestlist'}),
      });
    await manifestlistRow
      .getByRole('button', {name: 'Details'})
      .first()
      .click();

    // Both manifest list child manifests and expanded view content should coexist
    await expect(
      authenticatedPage.locator('.expanded-row').first(),
    ).toBeVisible();
    await expect(
      authenticatedPage.locator('.expanded-row-content').first(),
    ).toBeVisible();
  });
});
