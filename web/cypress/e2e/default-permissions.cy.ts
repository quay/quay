/// <reference types="cypress" />

describe('Default permissions page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('Search Filter', () => {
    cy.visit('/organization/testorg?tab=Defaultpermissions');

    // Filter for a single default permission
    cy.get('#default-permissions-search').type('testorg+testrobot');
    cy.contains('1 - 1 of 1');
    cy.get('#default-permissions-search').clear();

    // Filter for a non-existent default permission
    cy.get('#default-permissions-search').type('somethingrandome');
    cy.contains('0 - 0 of 0');
    cy.get('#default-permissions-search').clear();
  });

  it('Can update permission for default permission', () => {
    const createdBy = 'testorg+testrobot';
    cy.visit('/organization/testorg?tab=Defaultpermissions');

    // Search for creator
    cy.get('#default-permissions-search').type(`${createdBy}`);
    cy.contains('1 - 1 of 1');
    cy.get(`[data-testid="${createdBy}-permission-dropdown-toggle"]`)
      .contains('Read')
      .click();
    cy.get(`[data-testid="${createdBy}-WRITE"]`).click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(`Permission updated successfully to: owners`)
      .should('exist');
  });

  it('Can delete default permission', () => {
    const permissionToBeDeleted = 'testorg+testrobot';
    cy.visit('/organization/testorg?tab=Defaultpermissions');

    // Search for creator
    cy.get('#default-permissions-search').type(`${permissionToBeDeleted}`);
    cy.contains('1 - 1 of 1');
    cy.get('[data-testid="default-permissions-table"]').within(() => {
      cy.get(`[data-testid="${permissionToBeDeleted}-toggle-kebab"]`).click();

      cy.get(`[data-testid="${permissionToBeDeleted}-del-option"]`)
        .contains('Delete')
        .click();
    });

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(
        `Permission created by: ${permissionToBeDeleted} successfully deleted`,
      )
      .should('exist');
  });

  it('Can create default permission for a specific user', () => {
    const createdBy = 'testorg+testrobot2';
    const appliedTo = 'arsenal';
    cy.visit('/organization/testorg?tab=Defaultpermissions');

    cy.get('[data-testid="create-default-permissions-btn"]').click();
    cy.get(`[data-testid="Specific user"]`).click();

    cy.get('#repository-creator-dropdown').click();
    cy.get(`[data-testid="${createdBy}-robot-accnt"]`).click();

    cy.get('#applied-to-dropdown').click();
    cy.get(`[data-testid="${appliedTo}-team"]`).click();

    cy.get('[data-testid="create-default-permission-dropdown-toggle"]').click();
    cy.get('[data-testid="create-default-permission-dropdown"]')
      .contains('Write')
      .click();

    cy.get('[data-testid="create-permission-button"]').click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(
        `Successfully created default permission for creator: ${createdBy}`,
      )
      .should('exist');
  });

  it('Can create default permission for anyone', () => {
    const appliedTo = 'liverpool';
    cy.visit('/organization/testorg?tab=Defaultpermissions');

    cy.get('[data-testid="create-default-permissions-btn"]').click();
    cy.get(`[data-testid="Anyone"]`).click();

    cy.get('#applied-to-dropdown').click();
    cy.get(`[data-testid="${appliedTo}-team"]`).click();

    cy.get('[data-testid="create-default-permission-dropdown-toggle"]').click();
    cy.get('[data-testid="create-default-permission-dropdown"]')
      .contains('Write')
      .click();

    cy.get('[data-testid="create-permission-button"]').click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(`Successfully applied default permission to: ${appliedTo}`)
      .should('exist');
  });

  it('Can create default permission applied to a new team along with selecting existing robot account', () => {
    const newTeam = 'burnley';
    const teamDescription = 'underdog club';
    const repository = 'premierleague';
    const robotAccnt = 'testorg+testrobot2';

    cy.visit('/organization/testorg?tab=Defaultpermissions');

    // create default permission drawer
    cy.get('[data-testid="create-default-permissions-btn"]').click();
    cy.get(`[data-testid="Anyone"]`).click();

    cy.get('#applied-to-dropdown').click();
    cy.get(`[data-testid="create-new-team-btn"]`).click();

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
    cy.get(`[data-testid="${robotAccnt}-robot-accnt"]`).click();
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
    cy.get('[data-testid="selected-team-members-review"]').should(
      'have.value',
      `${robotAccnt}`,
    );
    cy.get('[data-testid="review-and-finish-wizard-btn"]').click();

    // verify newly created team is shown in the dropdown
    cy.get('#applied-to-dropdown input').should('have.value', `${newTeam}`);

    // permission dropdown
    cy.get('[data-testid="create-default-permission-dropdown-toggle"]').click();
    cy.get('[data-testid="create-default-permission-dropdown"]')
      .contains('Write')
      .click();

    cy.get('[data-testid="create-permission-button"]').click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success').should('exist');
  });

  it('Can create default permission applied to a new team along with creating new robot account from the drawer', () => {
    const orgName = 'testorg';
    const newTeam = 'fulham';
    const teamDescription = 'relegation club';
    const repository = 'premierleague';
    const newRobotName = 'wengerrobot';
    const newRobotDescription = 'premier league manager';

    cy.visit(`/organization/${orgName}?tab=Defaultpermissions`);

    // create default permission drawer
    cy.get('[data-testid="create-default-permissions-btn"]').click();
    cy.get(`[data-testid="Anyone"]`).click();

    cy.get('#applied-to-dropdown').click();
    cy.get(`[data-testid="create-new-team-btn"]`).click();

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

    // step - Add team member from the drawer
    cy.get('#search-member-dropdown').click();
    cy.get(`[data-testid="create-new-robot-accnt-btn"]`).click();
    cy.get('[data-testid="new-robot-name-input"]').type(`${newRobotName}`);
    cy.get('[data-testid="new-robot-description-input"]').type(
      `${newRobotDescription}`,
    );
    cy.get('[data-testid="create-robot-accnt-drawer-btn"]').click();
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
    cy.get('[data-testid="selected-team-members-review"]').should(
      'have.value',
      `${orgName}+${newRobotName}`,
    );
    cy.get('[data-testid="review-and-finish-wizard-btn"]').click();

    // verify newly created team is shown in the dropdown
    cy.get('#applied-to-dropdown input').should('have.value', `${newTeam}`);

    // permission dropdown
    cy.get('[data-testid="create-default-permission-dropdown-toggle"]').click();
    cy.get('[data-testid="create-default-permission-dropdown"]')
      .contains('Write')
      .click();

    cy.get('[data-testid="create-permission-button"]').click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success').should('exist');
  });

  it('Can create default permission for repository creator with new robot account', () => {
    const orgName = 'testorg';
    const newRobotName = 'klopprobot';
    const newRobotDescription = 'premier league manager';
    const addToTeam = 'arsenal';
    const addToRepo = 'premierleague';
    const appliedTo = 'liverpool';

    cy.visit(`/organization/${orgName}?tab=Defaultpermissions`);

    // create default permission drawer
    cy.get('[data-testid="create-default-permissions-btn"]').click();
    cy.get(`[data-testid="Specific user"]`).click();

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
    cy.get(`[data-testid="checkbox-row-${addToTeam}"]`).click();
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
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(
        `Successfully created robot account with robot name: ${orgName}+${newRobotName}`,
      )
      .should('exist');

    // verify newly created robot account is shown in the dropdown
    cy.get('#repository-creator-dropdown input').should(
      'have.value',
      `${orgName}+${newRobotName}`,
    );

    // Applied to dropdown
    cy.get('#applied-to-dropdown').click();
    cy.get(`[data-testid="${appliedTo}-team"]`).click();

    // permission dropdown
    cy.get('[data-testid="create-default-permission-dropdown-toggle"]').click();
    cy.get('[data-testid="create-default-permission-dropdown"]')
      .contains('Write')
      .click();

    cy.get('[data-testid="create-permission-button"]').click();

    // verify success alert
    cy.get('.pf-v5-c-alert.pf-m-success')
      .contains(
        `Successfully created default permission for creator: ${orgName}+${newRobotName}`,
      )
      .should('exist');
  });

  it('Can bulk delete default permissions', () => {
    const permissionsToBeDeleted = 'organization';
    cy.visit(`/organization/orgforpermission?tab=Defaultpermissions`);

    // Search for default permissions
    cy.get('#default-permissions-search').type(`${permissionsToBeDeleted}`);
    cy.contains('1 - 2 of 2');
    cy.get('[name="default-perm-bulk-select"]').click();
    cy.get(`[data-testid="default-perm-bulk-delete-icon"]`).click();

    // bulk delete modal
    cy.get('#delete-confirmation-input').type('confirm');
    cy.get('[data-testid="bulk-delete-confirm-btn"]')
      .click()
      .then(() => {
        cy.get('#default-permissions-search')
          .clear()
          .type(`${permissionsToBeDeleted}`);
        cy.contains('0 - 0 of 0');
      });
  });
});
