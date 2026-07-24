import {test, expect} from '../../fixtures';

test.describe(
  'Global Readonly Superuser — Write Action Guards (PROJQUAY-12394)',
  {tag: ['@organization', '@feature:GLOBAL_READONLY_SUPERUSER']},
  () => {
    test('org admin sees create buttons on OAuth Applications tab', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('roguardoauth');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=OauthApplications`,
      );

      await expect(
        authenticatedPage.getByText('Create OAuth Application'),
      ).toBeVisible();
    });

    test('org admin sees create button on Teams tab', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('roguardteams');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=TeamsAndMembership`,
      );

      await expect(
        authenticatedPage.getByText('Create new team'),
      ).toBeVisible();
    });

    test('org admin sees create button on Default Permissions tab', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('roguardperms');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=DefaultPermissions`,
      );

      await expect(
        authenticatedPage.getByText('Create default permission'),
      ).toBeVisible();
    });
  },
);
