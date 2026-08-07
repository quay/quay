import {test, expect} from '../../fixtures';

test.describe(
  'Global Readonly Superuser — Write Action Guards (PROJQUAY-12394)',
  {tag: ['@organization', '@feature:GLOBAL_READONLY_SUPERUSER']},
  () => {
    // Positive tests: org admin sees write-action buttons
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

    // Negative tests: readonly superuser does NOT see write-action buttons
    test('readonly superuser does not see create button on OAuth Applications tab', async ({
      readonlyPage,
      api,
    }) => {
      const org = await api.organization('roguardoauth');

      await readonlyPage.goto(
        `/organization/${org.name}?tab=OauthApplications`,
      );

      await expect(
        readonlyPage.getByText('Create OAuth Application'),
      ).not.toBeVisible();
    });

    test('readonly superuser does not see create button on Teams tab', async ({
      readonlyPage,
      api,
    }) => {
      const org = await api.organization('roguardteams');

      await readonlyPage.goto(
        `/organization/${org.name}?tab=TeamsAndMembership`,
      );

      await expect(
        readonlyPage.getByText('Create new team'),
      ).not.toBeVisible();
    });

    test('readonly superuser does not see create button on Default Permissions tab', async ({
      readonlyPage,
      api,
    }) => {
      const org = await api.organization('roguardperms');

      await readonlyPage.goto(
        `/organization/${org.name}?tab=DefaultPermissions`,
      );

      await expect(
        readonlyPage.getByText('Create default permission'),
      ).not.toBeVisible();
    });
  },
);
