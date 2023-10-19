/// <reference types="cypress" />

describe('Manage team members page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('Can search for member in Manage team members view', () => {
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

  it('Search Filter for Team member toggle view', () => {
    const team = 'chelsea';
    const robotAccnt = 'testorg+testrobot';
    const user = 'user1';
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Teams').click();

    // Search for a single team
    cy.get('#teams-view-search').type(`${team}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${team}-toggle-kebab"]`).click();
    cy.get(`[data-testid="${team}-manage-team-member-option"]`)
      .contains('Manage team members')
      .click();
    cy.get(`[data-testid="Team Member"]`).click();

    // verify team member is shown
    cy.get('#team-member-search-input').type(`${user}`);
    cy.contains('1 - 1 of 1');
    cy.get('#team-member-search-input').clear();

    // verify robot account is not shown
    cy.get('#team-member-search-input').type(`${robotAccnt}`);
    cy.contains('0 - 0 of 0');
  });

  it('Search Filter for Robot accounts toggle view', () => {
    const team = 'chelsea';
    const robotAccnt = 'testorg+testrobot';
    const user = 'user1';
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Teams').click();

    // Search for a single team
    cy.get('#teams-view-search').type(`${team}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${team}-toggle-kebab"]`).click();
    cy.get(`[data-testid="${team}-manage-team-member-option"]`)
      .contains('Manage team members')
      .click();
    cy.get(`[data-testid="Robot Accounts"]`).click();

    // verify robot account is shown
    cy.get('#team-member-search-input').type(`${robotAccnt}`);
    cy.contains('1 - 1 of 1');
    cy.get('#team-member-search-input').clear();

    // verify team member is not shown
    cy.get('#team-member-search-input').type(`${user}`);
    cy.contains('0 - 0 of 0');
  });

  it('Can update team description from Manage team members view', () => {
    const team = 'chelsea';
    const teamDescription = 'Chelsea team needs a new manager';
    cy.visit('/organization/testorg?tab=Teamsandmembership');
    cy.get('#Teams').click();

    // Search for a single team
    cy.get('#teams-view-search').type(`${team}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${team}-toggle-kebab"]`).click();
    cy.get(`[data-testid="${team}-manage-team-member-option"]`)
      .contains('Manage team members')
      .click();

    cy.get(`[data-testid="edit-team-description-btn"]`).click();
    cy.get(`[data-testid="team-description-text-area"]`).type(
      `${teamDescription}`,
    );
    cy.get(`[data-testid="save-team-description-btn"]`).click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(`Successfully updated team:${team} description`)
      .should('exist');
    cy.get(`[data-testid="team-description-text"]`).contains(
      `${teamDescription}`,
    );
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
    cy.get(`[data-testid="${robotAccntToBeDeleted}-del-btn"]`).click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(`Successfully deleted team member: ${robotAccntToBeDeleted}`)
      .should('exist');
  });

  it('Can add a new robot account to team', () => {
    const orgName = 'testorg';
    const team = 'arsenal';
    const addToRepo = 'premierleague';
    const newRobotName = 'klopprobot';
    const newRobotDescription = 'premier league manager';

    cy.visit('/organization/testorg?tab=Teamsandmembership');

    // Search for a single team
    cy.get('#teams-view-search').type(`${team}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${team}-toggle-kebab"]`).click();
    cy.get(`[data-testid="${team}-manage-team-member-option"]`)
      .contains('Manage team members')
      .click();

    cy.get('[data-testid="add-new-member-button"]').click();

    cy.get('#repository-creator-dropdown').click();
    cy.get(`[data-testid="create-new-robot-accnt-btn"]`).click();

    // create robot account wizard
    // step - Name & Description
    cy.get('[data-testid="new-robot-name-input"]').type(`${newRobotName}`);
    cy.get('[data-testid="new-robot-description-input"]').type(
      `${newRobotDescription}`,
    );
    cy.get('[data-testid="next-btn"]').click();

    // step - Add to team (optional)
    cy.get('[data-testid="next-btn"]').click();

    // step - Add to repository
    cy.get(`[data-testid="checkbox-row-${addToRepo}"]`).click();
    cy.get('[data-testid="next-btn"]').click();

    // step - Default permissions (optional)
    cy.get('[data-testid="applied-to-input"]').should(
      'have.value',
      `${newRobotName}`,
    );
    cy.get('[data-testid="next-btn"]').click();

    // step - Review and Finish
    cy.get('[data-testid="review-and-finish-btn"]').click();

    // verify newly created robot account is shown in the dropdown
    cy.get('#repository-creator-dropdown input').should(
      'have.value',
      `${orgName}+${newRobotName}`,
    );
    // submit add member from drawer
    cy.get('[data-testid="add-new-member-submit-btn"]').click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(`Successfully added "${orgName}+${newRobotName}" to team`)
      .should('exist');
    // verify table entry exists
    cy.get(`[data-testid="${orgName}+${newRobotName}"]`).contains(
      `${orgName}+${newRobotName}`,
    );
  });

  it('Can add a new user to the team', () => {
    const orgName = 'testorg';
    const team = 'arsenal';
    const user = 'user1';

    cy.visit('/organization/testorg?tab=Teamsandmembership');

    // Search for a single team
    cy.get('#teams-view-search').type(`${team}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${team}-toggle-kebab"]`).click();
    cy.get(`[data-testid="${team}-manage-team-member-option"]`)
      .contains('Manage team members')
      .click();

    cy.get('[data-testid="add-new-member-button"]').click();
    cy.get('#repository-creator-dropdown').type(`${user}`);
    cy.get(`[data-testid="${user}"]`).click();

    // verify selected user is shown in the dropdown
    cy.get('#repository-creator-dropdown input').should(
      'have.value',
      `${user}`,
    );
    // submit add member from drawer
    cy.get('[data-testid="add-new-member-submit-btn"]').click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(`Successfully added "${user}" to team`)
      .should('exist');
    // verify table entry exists
    cy.get(`[data-testid="${user}"]`).contains(`${user}`);
  });
});
