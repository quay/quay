import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {pushImage, pushMultiArchImage} from '../../utils/container';

test.describe(
  'Repository Details - Tag CRUD, Labels & Navigation',
  {tag: ['@tags', '@repository', '@container']},
  () => {
    // Shared repo for read-only tests (rendering, navigation, popover, labels)
    let sharedRepo: {namespace: string; name: string; fullName: string};

    test.beforeAll(async ({userContext, cachedContainerAvailable}) => {
      test.setTimeout(180000);
      if (!cachedContainerAvailable) return;

      const api = new ApiClient(userContext.request);
      const repoName = `tag-crud-${Date.now()}`;
      await api.createRepository(TEST_USERS.user.username, repoName, 'private');

      sharedRepo = {
        namespace: TEST_USERS.user.username,
        name: repoName,
        fullName: `${TEST_USERS.user.username}/${repoName}`,
      };

      await pushImage(
        sharedRepo.namespace,
        sharedRepo.name,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await pushMultiArchImage(
        sharedRepo.namespace,
        sharedRepo.name,
        'manifestlist',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
    });

    test.afterAll(async ({userContext}) => {
      if (!sharedRepo) return;
      const api = new ApiClient(userContext.request);
      try {
        await api.deleteRepository(sharedRepo.namespace, sharedRepo.name);
      } catch {
        // Ignore cleanup errors
      }
    });

    // --- Read-only tests against shared repo ---

    test('renders tag columns', async ({authenticatedPage}) => {
      await authenticatedPage.goto(
        `/repository/${sharedRepo.fullName}?tab=tags`,
      );
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();

      const latestRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'latest'}),
      });

      await expect(latestRow.locator('[data-label="Tag"]')).toContainText(
        'latest',
      );
      await expect(latestRow.locator('[data-label="Size"]')).toBeVisible();
      await expect(
        latestRow.locator('[data-label="Last Modified"]'),
      ).toBeVisible();
      await expect(latestRow.locator('[data-label="Expires"]')).toHaveText(
        'Never',
      );
      await expect(latestRow.locator('[data-label="Digest"]')).toContainText(
        'sha256:',
      );
    });

    test('renders manifest list with child platforms', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(
        `/repository/${sharedRepo.fullName}?tab=tags`,
      );
      await expect(
        authenticatedPage.getByRole('link', {name: 'manifestlist'}),
      ).toBeVisible();

      const manifestRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'manifestlist'}),
      });

      await expect(manifestRow.locator('[data-label="Tag"]')).toContainText(
        'manifestlist',
      );
      await expect(manifestRow.locator('[data-label="Digest"]')).toContainText(
        'sha256:',
      );

      // Expand child platforms
      await manifestRow.getByRole('button', {name: 'Details'}).first().click();

      // Verify at least one child platform row appears
      const childRow = manifestRow.locator('tr').filter({
        has: authenticatedPage.locator('[data-label="platform"]'),
      });
      await expect(childRow.first()).toBeVisible();
      await expect(
        childRow.first().locator('[data-label="platform"]'),
      ).toBeVisible();
      await expect(
        childRow.first().locator('[data-label="size"]'),
      ).toBeVisible();
      await expect(
        childRow.first().locator('[data-label="digest"]'),
      ).toContainText('sha256:');
    });

    test('pull popover shows correct commands', async ({authenticatedPage}) => {
      await authenticatedPage.goto(
        `/repository/${sharedRepo.fullName}?tab=tags`,
      );
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();

      const latestRow = authenticatedPage.locator('tr').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'latest',
          exact: true,
        }),
      });
      await latestRow.locator('td[data-label="Pull"] svg').hover();

      const popover = authenticatedPage.getByTestId('pull-popover');
      await expect(popover).toBeVisible({timeout: 10000});
      await expect(popover).toContainText('Fetch Tag');
      await expect(popover).toContainText('Podman Pull (By Tag)');
      await expect(popover).toContainText('Docker Pull (By Tag)');
      await expect(popover).toContainText('Podman Pull (By Digest)');
      await expect(popover).toContainText('Docker Pull (By Digest)');

      const inputs = popover.locator('input');
      await expect(inputs.first()).toHaveValue(
        new RegExp(`${sharedRepo.fullName}:latest`),
      );
    });

    test('clicking tag name navigates to tag details', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(
        `/repository/${sharedRepo.fullName}?tab=tags`,
      );
      await authenticatedPage.getByRole('link', {name: 'latest'}).click();

      await expect(authenticatedPage).toHaveURL(
        new RegExp(`/repository/${sharedRepo.fullName}/tag/latest`),
      );
      const tagDetails = authenticatedPage.getByTestId('tag-details').first();
      await expect(tagDetails).toContainText('latest');
      await expect(tagDetails).toContainText('sha256:');
    });

    test('clicking platform navigates to tag details', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(
        `/repository/${sharedRepo.fullName}?tab=tags`,
      );
      await expect(
        authenticatedPage.getByRole('link', {name: 'manifestlist'}),
      ).toBeVisible();

      const manifestRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'manifestlist'}),
      });

      await manifestRow.getByRole('button', {name: 'Details'}).first().click();

      const platformLink = manifestRow
        .locator('[data-label="platform"] a')
        .first();
      const platformText = await platformLink.textContent();
      await platformLink.click();

      await expect(authenticatedPage).toHaveURL(
        new RegExp(
          `/repository/${sharedRepo.fullName}/tag/manifestlist\\?.*digest=sha256:`,
        ),
      );
      // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
      await expect(authenticatedPage.getByText(platformText!)).toBeVisible();
    });

    // --- Mutating tests with individual repos ---

    test('delete tag via toolbar selection', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'v1'}),
      ).toBeVisible();

      // Select tag checkbox
      const tagRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'v1'}),
      });
      await tagRow.getByRole('checkbox').click();

      // Open Actions dropdown and click Remove
      await authenticatedPage.getByTestId('bulk-actions-kebab').click();
      await authenticatedPage.getByTestId('bulk-remove-action').click();

      await expect(
        authenticatedPage.getByText('Delete the following tag(s)?'),
      ).toBeVisible();
      const modal = authenticatedPage
        .locator('[id="tag-deletion-modal"]')
        .first();
      await modal.getByRole('button', {name: 'Delete'}).click();
      await expect(
        authenticatedPage.getByText('Deleted tag v1 successfully'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'v1'}),
      ).not.toBeAttached();
    });

    test('delete tag via row kebab', async ({authenticatedPage, api}) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'v1'}),
      ).toBeVisible();

      const tagRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'v1'}),
      });
      await tagRow.getByRole('button', {name: 'Tag actions kebab'}).click();
      await authenticatedPage.getByText('Remove').click();

      await expect(
        authenticatedPage.getByText('Delete the following tag(s)?'),
      ).toBeVisible();
      const modal = authenticatedPage
        .locator('[id="tag-deletion-modal"]')
        .first();
      await modal.getByRole('button', {name: 'Delete'}).click();
      await expect(
        authenticatedPage.getByText('Deleted tag v1 successfully'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'v1'}),
      ).not.toBeAttached();
    });

    test('force delete tag via toolbar', async ({
      authenticatedPage,
      api,
      quayConfig,
    }) => {
      test.skip(
        !quayConfig.config?.PERMANENTLY_DELETE_TAGS,
        'PERMANENTLY_DELETE_TAGS not enabled',
      );
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'v1'}),
      ).toBeVisible();

      // Select tag and use toolbar Actions > Permanently delete
      const tagRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'v1'}),
      });
      await tagRow.getByRole('checkbox').click();
      await authenticatedPage.getByTestId('bulk-actions-kebab').click();
      await authenticatedPage.getByText('Permanently delete').click();

      await expect(
        authenticatedPage.getByText('Permanently delete the following tag(s)?'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(
          'Tags deleted cannot be restored within the time machine window',
        ),
      ).toBeVisible();
      const modal = authenticatedPage
        .locator('[id="tag-deletion-modal"]')
        .first();
      await modal.getByRole('button', {name: 'Delete'}).click();

      await expect(
        authenticatedPage.getByRole('link', {name: 'v1'}),
      ).not.toBeAttached();
    });

    test('bulk delete tags', async ({authenticatedPage, api}) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'tag1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
      await pushImage(
        repo.namespace,
        repo.name,
        'tag2',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'tag1'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'tag2'}),
      ).toBeVisible();

      // Select all via toolbar checkbox dropdown
      await authenticatedPage.locator('#toolbar-dropdown-checkbox').click();
      await authenticatedPage.getByTestId('select-page-items-action').click();

      // Open Actions and remove
      await authenticatedPage.getByTestId('bulk-actions-kebab').click();
      await authenticatedPage.getByTestId('bulk-remove-action').click();

      const modal = authenticatedPage
        .locator('[id="tag-deletion-modal"]')
        .first();
      await expect(modal).toContainText('tag1');
      await expect(modal).toContainText('tag2');
      await modal.getByRole('button', {name: 'Delete'}).click();

      await expect(
        authenticatedPage.getByRole('link', {name: 'tag1'}),
      ).not.toBeAttached();
      await expect(
        authenticatedPage.getByRole('link', {name: 'tag2'}),
      ).not.toBeAttached();
    });

    test('add new tag via kebab', async ({authenticatedPage, api}) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'v1'}),
      ).toBeVisible();

      const tagRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'v1'}),
      });
      await tagRow.getByRole('button', {name: 'Tag actions kebab'}).click();
      await authenticatedPage.getByText('Add new tag').click();

      await expect(
        authenticatedPage.getByText(/Add tag to manifest sha256:/),
      ).toBeVisible();

      const tagTextField = authenticatedPage.getByRole('textbox', {
        name: 'new tag name',
      });

      await tagTextField.fill('newtag');
      await authenticatedPage.getByRole('button', {name: 'Create tag'}).click();

      await expect(
        authenticatedPage.getByText('Successfully created tag newtag'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'newtag'}),
      ).toBeVisible();
    });

    test('add new tag: Create tag button disabled for bad tag names', async ({
      authenticatedPage,
      api,
    }) => {
      // push test image
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      const errorMessage = `Must start with a letter, digit or underscore. Only letters, digits, underscores, hyphens and periods allowed. Max 128 characters.`;

      // verify UI can be rendered
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'v1'}),
      ).toBeVisible();

      // open modal dialog for tag addition
      const tagRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'v1'}),
      });
      await tagRow.getByRole('button', {name: 'Tag actions kebab'}).click();
      await authenticatedPage.getByText('Add new tag').click();
      await expect(
        authenticatedPage.getByText(/Add tag to manifest sha256:/),
      ).toBeVisible();

      const tagTextField = authenticatedPage.getByRole('textbox', {
        name: 'new tag name',
      });
      const createButton = authenticatedPage.getByRole('button', {
        name: 'Create tag',
      });

      // try filling a bad tag
      await tagTextField.fill('*!"387%%%abdac');

      // verify that error message is shown and button is not available
      await expect(authenticatedPage.getByText(errorMessage)).toBeVisible();
      await expect(createButton).toBeDisabled();

      // replace tag with a too long tag name
      await tagTextField.clear();
      await tagTextField.fill('a'.repeat(129));

      // verify that error message is shown and button is not available
      await expect(authenticatedPage.getByText(errorMessage)).toBeVisible();
      await expect(createButton).toBeDisabled();

      // replace tag with a proper tag
      await tagTextField.clear();
      await tagTextField.fill('proper-tag');

      // verify that error message is no longer present and button is enabled
      await expect(authenticatedPage.getByText(errorMessage)).not.toBeVisible();
      await expect(createButton).toBeEnabled();

      // cancel
      await authenticatedPage.getByRole('button', {name: 'Cancel'}).click();
      await expect(
        authenticatedPage.getByRole('dialog', {name: 'Add tag modal'}),
      ).not.toBeVisible();
    });

    test('alert on failure to add tag', async ({authenticatedPage, api}) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.route(
        `**/api/v1/repository/${repo.namespace}/${repo.name}/tag/newtag`,
        async (route) => {
          if (route.request().method() === 'PUT') {
            await route.fulfill({status: 500});
          } else {
            await route.continue();
          }
        },
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'v1'}),
      ).toBeVisible();

      const tagRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'v1'}),
      });
      await tagRow.getByRole('button', {name: 'Tag actions kebab'}).click();
      await authenticatedPage.getByText('Add new tag').click();
      await authenticatedPage
        .locator('input[placeholder="New tag name"]')
        .fill('newtag');
      await authenticatedPage.getByText('Create tag').click();

      await expect(
        authenticatedPage.getByText('Could not create tag newtag'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'newtag'}),
      ).not.toBeAttached();
    });

    test('label lifecycle: create and delete labels', async ({
      authenticatedPage,
      api,
    }) => {
      // Use a fresh repo so label state is clean
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'v1'}),
      ).toBeVisible();

      const tagRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'v1'}),
      });

      // Open labels modal and create labels
      await tagRow.getByRole('button', {name: 'Tag actions kebab'}).click();
      await authenticatedPage.getByText('Edit labels').click();

      const mutableLabels = authenticatedPage
        .locator('#mutable-labels')
        .first();
      await expect(mutableLabels).toBeVisible();

      await authenticatedPage.getByText('Add new label').click();
      await authenticatedPage
        .locator('input[placeholder="key=value"]')
        .fill('testkey=testval');
      await authenticatedPage.getByText('Mutable labels').click();
      await authenticatedPage.getByText('Add new label').click();
      await authenticatedPage
        .locator('input[placeholder="key=value"]')
        .fill('foo=bar');
      await authenticatedPage.getByText('Mutable labels').click();
      await authenticatedPage.getByText('Save Labels').click();

      await expect(
        authenticatedPage.getByText('Created labels successfully'),
      ).toBeVisible();

      // Re-open labels and delete them
      await tagRow.getByRole('button', {name: 'Tag actions kebab'}).click();
      await authenticatedPage.getByText('Edit labels').click();

      const mutableLabels2 = authenticatedPage
        .locator('#mutable-labels')
        .first();
      await expect(mutableLabels2).toContainText('testkey=testval');
      await expect(mutableLabels2).toContainText('foo=bar');

      // Remove all mutable labels
      const removeButtons = mutableLabels2.getByRole('button');
      const count = await removeButtons.count();
      for (let i = 0; i < count; i++) {
        await mutableLabels2.getByRole('button').first().click();
      }
      await authenticatedPage.getByText('Save Labels').click();
      await expect(
        authenticatedPage.getByText('Deleted labels successfully'),
      ).toBeVisible();
    });

    test('alert on failure to create labels', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.route('**/labels', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({status: 500});
        } else {
          await route.continue();
        }
      });

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
      await expect(
        authenticatedPage.getByRole('link', {name: 'v1'}),
      ).toBeVisible();

      const tagRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'v1'}),
      });

      await tagRow.getByRole('button', {name: 'Tag actions kebab'}).click();
      await authenticatedPage.getByText('Edit labels').click();
      await authenticatedPage.getByText('Add new label').click();
      await authenticatedPage
        .locator('input[placeholder="key=value"]')
        .fill('fail=test');
      await authenticatedPage.getByText('Mutable labels').click();

      const mutableLabelContent = authenticatedPage
        .locator('#mutable-labels .label-content')
        .first();
      await expect(mutableLabelContent).toContainText('fail=test');

      const saveLabelsButton = authenticatedPage.getByRole('button', {
        name: 'Save Labels',
      });
      await expect(saveLabelsButton).toBeEnabled();

      await authenticatedPage.getByText('Save Labels').click();

      await expect(
        authenticatedPage.getByText('Could not create labels'),
      ).toBeVisible();
    });

    // --- Search and filter tests against shared repo ---

    test('search and filter tags by name, regex, and digest', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(
        `/repository/${sharedRepo.fullName}?tab=tags`,
      );
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'manifestlist'}),
      ).toBeVisible();

      const searchInput = authenticatedPage.locator(
        '#tagslist-search-input input',
      );

      // Search by name — "test" should match "latest" but not "manifestlist"
      await searchInput.fill('test');
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'manifestlist'}),
      ).not.toBeAttached();

      // Clear search
      await authenticatedPage.locator('[aria-label="Reset search"]').click();
      await expect(
        authenticatedPage.getByRole('link', {name: 'manifestlist'}),
      ).toBeVisible();

      // Enable regex mode
      await authenticatedPage
        .locator('[aria-label="Open advanced search"]')
        .click();
      await authenticatedPage
        .locator('[id="filter-input-regex-checker"]')
        .click();

      // Regex: "test$" matches "latest"
      await searchInput.fill('test$');
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'manifestlist'}),
      ).not.toBeAttached();

      // Regex: "^manifest" matches "manifestlist"
      await authenticatedPage.locator('[aria-label="Reset search"]').click();
      await searchInput.fill('^manifest');
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).not.toBeAttached();
      await expect(
        authenticatedPage.getByRole('link', {name: 'manifestlist'}),
      ).toBeVisible();

      // Switch to digest filter
      await authenticatedPage.locator('[aria-label="Reset search"]').click();
      await authenticatedPage.locator('#toolbar-dropdown-filter').click();
      await authenticatedPage.getByText('Digest').click();

      // Get digest of latest tag
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();
      const latestRow = authenticatedPage.getByTestId('table-entry').filter({
        has: authenticatedPage.getByRole('link', {name: 'latest'}),
      });
      const digestText = await latestRow
        .locator('[data-label="Digest"]')
        .textContent();
      // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
      const shortDigest = digestText!.replace('sha256:', '').slice(0, 12);

      await searchInput.fill(shortDigest);
      await expect(
        authenticatedPage.getByRole('link', {name: 'latest'}),
      ).toBeVisible();
    });
  },
);
