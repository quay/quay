import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushImage} from '../../utils/container';

test.describe(
  'Repository Details - Information Tab',
  {tag: ['@repository']},
  () => {
    test('defaults to Information tab', async ({authenticatedPage, api}) => {
      const repo = await api.repository();
      await authenticatedPage.goto(`/repository/${repo.fullName}`);

      // Information tab is active by default
      await expect(
        authenticatedPage.getByRole('tab', {
          name: 'Information',
          selected: true,
        }),
      ).toBeVisible();

      // Verify Information tab content sections
      await expect(
        authenticatedPage.getByText('Repository Activity'),
      ).toBeVisible();
      await expect(authenticatedPage.getByText('Pull Commands')).toBeVisible();
      await expect(
        authenticatedPage.getByText('Description', {exact: true}).first(),
      ).toBeVisible();
    });

    test('description lifecycle: edit, save, cancel', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await authenticatedPage.goto(`/repository/${repo.fullName}`);

      // Edit and save description
      await authenticatedPage.getByText('Edit description').click();
      const textarea = authenticatedPage.locator(
        'textarea[aria-label="Repository description"]',
      );
      await expect(textarea).toBeVisible();
      await textarea.fill('New test description');
      await authenticatedPage.getByRole('button', {name: 'Save'}).click();

      await expect(
        authenticatedPage.getByText(
          'Repository description updated successfully',
        ),
      ).toBeVisible();
      await expect(textarea).not.toBeAttached();
      await expect(
        authenticatedPage.getByText('New test description'),
      ).toBeVisible();

      // Edit and cancel
      await authenticatedPage.getByText('Edit description').click();
      const textarea2 = authenticatedPage.locator(
        'textarea[aria-label="Repository description"]',
      );
      await textarea2.fill('This should be discarded');
      await authenticatedPage.getByRole('button', {name: 'Cancel'}).click();

      await expect(textarea2).not.toBeAttached();
      await expect(
        authenticatedPage.getByText('New test description'),
      ).toBeVisible();
    });

    test('switches to Tags tab when clicked', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await authenticatedPage.goto(`/repository/${repo.fullName}`);

      await authenticatedPage.getByRole('tab', {name: 'Tags'}).click();
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Tags', selected: true}),
      ).toBeVisible();
    });

    test('supports nested repository names', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nestedorg');
      const repo = await api.repositoryWithName(org.name, 'nested/path/myrepo');

      await authenticatedPage.goto(`/repository/${repo.fullName}`);

      // Verify we landed on the correct repo page
      await expect(
        authenticatedPage.getByRole('tab', {
          name: 'Information',
          selected: true,
        }),
      ).toBeVisible();
      await expect(authenticatedPage.getByText('Pull Commands')).toBeVisible();
    });

    test('supports repository name containing "build" keyword', async ({
      authenticatedPage,
      api,
    }) => {
      // "build" as a path segment breaks parseRepoNameFromUrl (treats it as
      // a route suffix like /repo/build/<id>). Use it as a prefix instead.
      const org = await api.organization('buildnameorg');
      const repo = await api.repositoryWithName(
        org.name,
        'build-images/release',
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}`);

      await expect(
        authenticatedPage.getByRole('tab', {
          name: 'Information',
          selected: true,
        }),
      ).toBeVisible();
      await expect(authenticatedPage.getByText('Pull Commands')).toBeVisible();
    });

    test(
      'non-writable repo hides tag actions',
      {tag: ['@container']},
      async ({readonlyPage, api}) => {
        // Create repo as testuser (api runs as testuser)
        const repo = await api.repository();
        await pushImage(
          repo.namespace,
          repo.name,
          'latest',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        // View as readonly user — should not see tag action kebabs
        await readonlyPage.goto(`/repository/${repo.fullName}?tab=tags`);
        await expect(
          readonlyPage.getByRole('link', {name: 'latest'}),
        ).toBeVisible();
        await expect(
          readonlyPage.locator('#tag-actions-kebab'),
        ).not.toBeAttached();
      },
    );
  },
);
