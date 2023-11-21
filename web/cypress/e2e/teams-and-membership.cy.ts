/// <reference types="cypress" />

describe('Teams and membership page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('Search Filter for Team View', () => {
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Teams').click();

    // Filter for a single team
    cy.get('#teams-view-search').type('arsenal');
    cy.contains('1 - 1 of 1');
    cy.get('#teams-view-search').clear();
  });

  it('Search Filter for Members View', () => {
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Members').click();

    // Filter for a single member
    cy.get('#members-view-search').type('user1');
    cy.contains('1 - 1 of 1');
    cy.get('#members-view-search').clear();
  });

  it('Search Filter for Collaborators View', () => {
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Collaborators').click();

    // Filter for a single collaborator
    cy.get('#collaborators-view-search').type('collaborator1');
    cy.contains('1 - 1 of 1');
    cy.get('#collaborators-view-search').clear();
  });

  it('Can create a new team', () => {
    const newTeam = 'qpr';
    const teamDescription = 'premierleague club';
    const repository = 'premierleague';

    cy.visit('/organization/testorg?tab=Teamsandmembership');

    // create new team button
    cy.get(`[data-testid="create-new-team-button"]`).click();

    // create team modal
    cy.get('[data-testid="new-team-name-input"]').type(`${newTeam}`);
    cy.get('[data-testid="new-team-description-input"]').type(
      `${teamDescription}`,
    );
    cy.get('[data-testid="create-team-confirm"]').click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(`Successfully created new team: ${newTeam}`)
      .should('exist');

    // create team wizard
    // step - Name & Description
    cy.get('[data-testid="create-team-wizard-form-name"]').should(
      'have.value',
      `${newTeam}`,
    );
    cy.get('[data-testid="create-team-wizard-form-description"]').should(
      'have.value',
      `${teamDescription}`,
    );
    cy.get('[data-testid="next-btn"]').click();

    // step - Add to repository
    cy.get(`[data-testid="checkbox-row-${repository}"]`).click();
    cy.get(`[data-testid="${repository}-permission-dropdown-toggle"]`).contains(
      'Read',
    );
    cy.get('[data-testid="next-btn"]').click();

    // step - Add team member
    cy.get('#search-member-dropdown').click();
    cy.get('#search-member-dropdown-input').type('user1');
    cy.get(`[data-testid="user1"]`).click();
    cy.get('[data-testid="next-btn"]').click();

    // step - Review and Finish
    cy.get(`[data-testid="${newTeam}-team-name-review"]`).should(
      'have.value',
      `${newTeam}`,
    );
    cy.get(`[data-testid="${teamDescription}-team-descr-review"]`).should(
      'have.value',
      `${teamDescription}`,
    );
    cy.get('[data-testid="selected-repos-review"]').should(
      'have.value',
      `${repository}`,
    );
    cy.get('[data-testid="review-and-finish-wizard-btn"]').click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains('Successfully added members to team')
      .should('exist');

    // verify newly created team is shown under teams view
    cy.get('#teams-view-search').type(`${newTeam}`);
    cy.contains('1 - 1 of 1');
  });

  it('Can update team role in Team View', () => {
    const teamToBeUpdated = 'arsenal';
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Teams').click();

    // Search for a single team
    cy.get('#teams-view-search').type(`${teamToBeUpdated}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${teamToBeUpdated}-team-dropdown-toggle"]`)
      .contains('Member')
      .click();
    cy.get(`[data-testid="${teamToBeUpdated}-Creator"]`).click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(`Team role updated successfully for: ${teamToBeUpdated}`)
      .should('exist');
  });

  it('Can delete team from Team View', () => {
    const teamToBeDeleted = 'liverpool';
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Teams').click();

    // Search for a single team
    cy.get('#teams-view-search').type(`${teamToBeDeleted}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${teamToBeDeleted}-toggle-kebab"]`).click();
    cy.get(`[data-testid="${teamToBeDeleted}-del-option"]`)
      .contains('Delete')
      .click();
    cy.get(`[data-testid="${teamToBeDeleted}-del-btn"]`).click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success').contains(
      `Successfully deleted team: ${teamToBeDeleted}`,
    );
  });

  it('Can delete a member from Collaborator view', () => {
    const collaboratorName = 'collaborator1';
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Collaborators').click();

    // delete collaborator
    cy.get(`[data-testid="${collaboratorName}-del-icon"]`).click();
    cy.get(`[data-testid="${collaboratorName}-del-btn"]`).click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(`Successfully deleted collaborator`)
      .should('exist');
  });

  it('Can set repository permissions for a team', () => {
    const team = 'chelsea';
    const repo = 'premierleague';
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Teams').click();

    // Search for a single team
    cy.get('#teams-view-search').type(`${team}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${team}-toggle-kebab"]`).click();
    cy.get(`[data-testid="${team}-set-repo-perms-option"]`)
      .contains('Set repository permissions')
      .click();

    // search for repo perm inside the modal
    cy.get('#set-repo-perm-for-team-search').type(`${repo}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${repo}-role-dropdown-toggle"]`)
      .contains('None')
      .click();
    cy.get(`[data-testid="${repo}-Write"]`).click();
    cy.get('#update-team-repo-permissions').click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(`Updated repo perm for team: ${team} successfully`)
      .should('exist');
  });

  it('Can perform a bulk update of repo permissions for a team', () => {
    const team = 'chelsea';
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Teams').click();

    // Search for a single team
    cy.get('#teams-view-search').type(`${team}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${team}-toggle-kebab"]`).click();
    cy.get(`[data-testid="${team}-set-repo-perms-option"]`)
      .contains('Set repository permissions')
      .click();

    // bulk select entries and change role from kebab
    cy.get('[name="add-repository-bulk-select"]').click();
    cy.get('#toggle-bulk-perms-kebab').click();
    cy.get('[role="menuitem"]').contains('Write').click();
    cy.get('#update-team-repo-permissions').click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(`Updated repo perm for team: ${team} successfully`)
      .should('exist');
  });

  it("A user(member or creator) in the team can view teams info but can't edit without admin role", () => {
    const team = 'teamforreadonly';
    const organization = 'user2org1';
    const user = 'user1';
    cy.visit(`/organization/${organization}?tab=Teamsandmembership`);
    cy.get('#Teams').click();

    // Search for a single team
    cy.get('#teams-view-search').type(`${team}`);
    cy.contains('1 - 1 of 1');

    // verify create new team button not visible
    cy.get(`[data-testid="create-new-team-button"]`).should('not.exist');

    // verify create team role dropdown is disabled
    cy.get(`[data-testid="${team}-team-dropdown-toggle"]`).should(
      'be.disabled',
    );
    // verify kebab option is not seen
    cy.get(`[data-testid="${team}-toggle-kebab"]`).should('not.exist');

    // verify editable options in manage members view cannot be seen
    cy.get(`[data-testid="member-count-for-${team}"]`).contains('1').click();
    cy.url().should('include', `teams/${team}`);
    cy.get('[data-testid="add-new-member-button"]').should('not.exist');
    cy.get(`[data-testid="edit-team-description-btn"]`).should('not.exist');
    cy.get(`[data-testid="${user}-delete-icon"]`).should('not.exist');
  });
});
