import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe(
  'Bug Discovery: Team Wizard Race Condition',
  {tag: ['@bug-discovery']},
  () => {
    test(
      'team wizard closes before async member operations complete',
      {
        tag: ['@organization'],
      },
      async ({authenticatedPage, api}) => {
        // Bug: CreateTeamWizard.tsx:95-123
        // The `onSubmitTeamWizard` function uses `.map(async ...)` without
        // `Promise.all()` to add repo permissions, add members, and delete members.
        // This means the wizard calls `handleWizardToggle()` (closes the modal)
        // BEFORE any of the async operations complete.
        //
        // The `.map()` returns an array of promises but those promises are never
        // awaited. The function continues to line 121 immediately, closing the wizard.
        // If any operation fails, the error is silently swallowed.
        //
        // Expected behavior: Wizard should wait for all operations to complete
        // before closing, and surface any errors.

        // Set up: Create org with team and a repo
        const org = await api.organization('bugwiz');
        const team = await api.team(org.name, 'wizteam', 'admin');
        const repo = await api.repository(org.name, 'wizrepo');

        // Navigate to the teams page
        await authenticatedPage.goto(
          `/organization/${org.name}?tab=Teamsandmembership`,
        );
        await authenticatedPage.locator('#Teams').click();

        // Open the team's manage members via kebab menu
        await authenticatedPage
          .getByTestId(`${team.name}-toggle-kebab`)
          .click();
        await authenticatedPage
          .getByTestId(`${team.name}-manage-team-member-option`)
          .click();

        // Wait for the wizard to render in the manage team page
        await expect(authenticatedPage).toHaveURL(
          new RegExp(`teams/${team.name}`),
        );

        // Navigate back to verify the team exists and operations didn't fail
        await authenticatedPage.goto(
          `/organization/${org.name}?tab=Teamsandmembership`,
        );
        await authenticatedPage.locator('#Teams').click();

        // The team should still be listed
        await expect(
          authenticatedPage.getByText(team.name),
        ).toBeVisible();
      },
    );
  },
);
