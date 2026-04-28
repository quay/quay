import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {API_URL} from '../../utils/config';
import {pushImage} from '../../utils/container';

test.describe(
  'Superuser Repository and Tag Actions',
  {tag: ['@superuser', '@feature:SUPERUSERS_FULL_ACCESS']},
  () => {
    test("superuser can create a repository in another user's organization", async ({
      superuserPage,
      superuserRequest,
      api,
    }) => {
      const org = await api.organization('sucreateorg');

      await superuserPage.goto(`/organization/${org.name}`);

      // Click create repository
      await superuserPage
        .getByRole('button', {name: 'Create Repository'})
        .click();

      // Fill in repository name
      const repoNameInput = superuserPage.getByTestId('repository-name-input');
      await expect(repoNameInput).toBeVisible();
      await repoNameInput.fill('sucreatedrepo');

      // Select private visibility
      await superuserPage.getByTestId('visibility-private-radio').click();

      // Submit
      await superuserPage.getByTestId('create-repository-submit-btn').click();

      // Verify success alert appears
      await expect(
        superuserPage.getByText(/[Ss]uccessfully created repository/).first(),
      ).toBeVisible({timeout: 10000});

      // Verify repo exists via API
      const response = await superuserRequest.get(
        `${API_URL}/api/v1/repository/${org.name}/sucreatedrepo`,
      );
      expect(response.ok()).toBeTruthy();
    });

    test("superuser can view repositories in another user's organization", async ({
      superuserPage,
      api,
    }) => {
      const org = await api.organization('suvieworg');
      await api.repository(org.name, 'viewrepo');

      await superuserPage.goto(`/organization/${org.name}`);

      // Verify repositories tab is visible and shows the repo
      await expect(
        superuserPage.getByRole('tab', {name: 'Repositories'}),
      ).toBeVisible({timeout: 15000});
      await expect(superuserPage.getByText('viewrepo')).toBeVisible();
    });

    test("superuser can delete a repository in another user's organization", async ({
      superuserPage,
      superuserRequest,
      api,
    }) => {
      const org = await api.organization('sudelorg');
      const repo = await api.repository(org.name, 'delrepo');

      // Navigate to repo settings > delete tab
      await superuserPage.goto(
        `/repository/${org.name}/${repo.name}?tab=settings`,
      );
      await superuserPage.getByTestId('settings-tab-deleterepository').click();

      await expect(
        superuserPage.getByText('Deleting a repository cannot be undone'),
      ).toBeVisible();

      await superuserPage.getByTestId('delete-repository-btn').click();

      // Fill confirmation input
      await superuserPage
        .getByTestId('delete-repository-confirm-input')
        .fill(`${org.name}/${repo.name}`);
      await superuserPage.getByTestId('delete-repository-confirm-btn').click();

      // Wait for navigation away from the repo page
      await superuserPage.waitForURL(/\/repository$|\/organization/, {
        timeout: 15000,
      });

      // Verify repo is gone via API
      await expect
        .poll(
          async () => {
            const resp = await superuserRequest.get(
              `${API_URL}/api/v1/repository/${org.name}/${repo.name}`,
            );
            return resp.status();
          },
          {timeout: 10000},
        )
        .toBe(404);
    });

    test(
      "superuser can view and delete tags in another user's repository",
      {tag: ['@container']},
      async ({superuserPage, api}) => {
        const org = await api.organization('sutagorg');
        const repo = await api.repository(org.name, 'tagrepo');

        // Push an image to create a tag
        await pushImage(
          org.name,
          repo.name,
          'testtag',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );

        // Navigate to repo tags as superuser
        await superuserPage.goto(
          `/repository/${org.name}/${repo.name}?tab=tags`,
        );

        // Verify tag is visible
        await expect(
          superuserPage.getByRole('link', {name: 'testtag'}),
        ).toBeVisible({timeout: 15000});

        // Delete the tag via row kebab
        const tagRow = superuserPage.getByTestId('table-entry').filter({
          has: superuserPage.getByRole('link', {name: 'testtag'}),
        });
        await tagRow.locator('#tag-actions-kebab').click();
        await superuserPage.getByText('Remove').click();

        // Confirm deletion in modal
        await expect(
          superuserPage.getByText('Delete the following tag(s)?'),
        ).toBeVisible();
        await superuserPage.getByRole('button', {name: 'Delete'}).click();

        // Verify tag is gone
        await expect(
          superuserPage.getByText('There are no viewable tags'),
        ).toBeVisible({timeout: 15000});
      },
    );
  },
);
