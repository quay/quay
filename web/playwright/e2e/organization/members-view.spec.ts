import {test, expect} from '../../fixtures';

test.describe(
  'Organization Members and Collaborators Views',
  {tag: ['@organization']},
  () => {
    test('members view shows org members with correct columns', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('memview');
      const team = await api.team(org.name, 'testteam');
      await api.teamMember(org.name, team.name, 'testuser');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Teamsandmembership`,
      );

      // Switch to Members View
      await authenticatedPage
        .getByRole('button', {name: 'Members View'})
        .click();

      // Verify column headers
      await expect(
        authenticatedPage.getByRole('columnheader', {name: 'User name'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('columnheader', {name: 'Teams'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('columnheader', {
          name: 'Direct repository permissions',
        }),
      ).toBeVisible();
    });

    test('view toggle switches between Teams, Members, and Collaborators', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('memtoggle');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Teamsandmembership`,
      );

      // Default is Team View
      const teamBtn = authenticatedPage.getByRole('button', {
        name: 'Team View',
      });
      await expect(teamBtn).toHaveAttribute('aria-pressed', 'true');

      // Switch to Members View
      await authenticatedPage
        .getByRole('button', {name: 'Members View'})
        .click();
      await expect(
        authenticatedPage.getByRole('button', {name: 'Members View'}),
      ).toHaveAttribute('aria-pressed', 'true');

      // Switch to Collaborators View
      await authenticatedPage
        .getByRole('button', {name: 'Collaborators View'})
        .click();
      await expect(
        authenticatedPage.getByRole('button', {name: 'Collaborators View'}),
      ).toHaveAttribute('aria-pressed', 'true');
    });

    test('teams view shows teams with correct columns', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('memteamcol');
      const team = await api.team(org.name, 'viewteam');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Teamsandmembership`,
      );

      await expect(
        authenticatedPage.getByRole('columnheader', {name: 'Team name'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('columnheader', {name: 'Members'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('columnheader', {name: 'Repositories'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('columnheader', {name: 'Team role'}),
      ).toBeVisible();

      // Created team should be listed (rendered as a link)
      await expect(
        authenticatedPage.getByRole('link', {name: team.name}),
      ).toBeVisible();
    });

    test('collaborators view shows empty state or collaborators', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('memcollab');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Teamsandmembership`,
      );

      await authenticatedPage
        .getByRole('button', {name: 'Collaborators View'})
        .click();

      // Should show either collaborator list or empty message
      await expect(
        authenticatedPage
          .getByText('No collaborators found')
          .or(authenticatedPage.getByRole('columnheader', {name: 'User name'})),
      ).toBeVisible();
    });

    test('create team button opens modal from teams view', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('memcrteam');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Teamsandmembership`,
      );

      await authenticatedPage
        .getByRole('button', {name: 'Create New Team'})
        .click();

      await expect(
        authenticatedPage.getByText('Provide a name for your new team:'),
      ).toBeVisible();
    });
  },
);
