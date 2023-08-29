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

  it('Can update team role in Team View', () => {
    const teamToBeUpdated = 'arsenal';
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Teams').click();

    // Search for a single team
    cy.get('#teams-view-search').type(`${teamToBeUpdated}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${teamToBeUpdated}-team-dropdown"]`)
      .contains('Member')
      .click();
    cy.get(`[data-testid="${teamToBeUpdated}-Creator"]`).click();

    // verify success alert
    cy.get('.pf-c-alert.pf-m-success')
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

    // verify success alert
    cy.get('.pf-c-alert.pf-m-success')
      .contains(`Successfully deleted team`)
      .should('exist');
  });

  it('Can delete a member from Collaborator view', () => {
    const collaboratorName = 'collaborator1';
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Collaborators').click();

    // delete collaborator
    cy.get(`[data-testid="${collaboratorName}-del-icon"]`).click();
    cy.get(`[data-testid="${collaboratorName}-del-btn"]`).click();

    // verify success alert
    cy.get('.pf-c-alert.pf-m-success')
      .contains(`Successfully deleted collaborator`)
      .should('exist');
  });

  it('Can open manage team members', () => {
    const team = 'owners';
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Teams').click();

    // Search for a single team
    cy.get('#teams-view-search').type(`${team}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${team}-toggle-kebab"]`).click();
    cy.get(`[data-testid="${team}-manage-team-member-option"]`)
      .contains('Manage team members')
      .click();

    // verify manage members view is shown
    cy.url().should('contain', `teams/${team}?tab=Teamsandmembership`);
    cy.get(`[data-label="Team member"]`).contains('user1');
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
    cy.get(`[data-testid="${repo}-role-dropdown"]`).contains('None').click();
    cy.get(`[data-testid="${repo}-Write"]`).click();
    cy.get('#update-team-repo-permissions').click();

    // verify success alert
    cy.get('.pf-c-alert.pf-m-success')
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
    cy.get('#add-repository-bulk-select').click();
    cy.get('#toggle-bulk-perms-kebab').click();
    cy.get('[role="menuitem"]').contains('Write').click();
    cy.get('#update-team-repo-permissions').click();

    // verify success alert
    cy.get('.pf-c-alert.pf-m-success')
      .contains(`Updated repo perm for team: ${team} successfully`)
      .should('exist');
  });

  it('Can delete a robot account from Manage team members view', () => {
    const team = 'chelsea';
    const robotAccntToBeDeleted = 'testorg+testrobot';
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Teams').click();

    // Search for a single team
    cy.get('#teams-view-search').type(`${team}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${team}-toggle-kebab"]`).click();
    cy.get(`[data-testid="${team}-manage-team-member-option"]`)
      .contains('Manage team members')
      .click();

    // delete robot account
    cy.get(`[data-testid="${robotAccntToBeDeleted}-delete-icon"]`).click();

    // verify success alert
    cy.get('.pf-c-alert.pf-m-success')
      .contains(`Successfully deleted team member`)
      .should('exist');
  });
});
