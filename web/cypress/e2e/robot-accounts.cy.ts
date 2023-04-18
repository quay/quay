/// <reference types="cypress" />

describe('Robot Accounts Page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('Search Filter', () => {
    cy.visit('/organization/testorg?tab=Robot+accounts');

    // Filter for a single robot account
    cy.get('#robot-account-search').type('testrobot2');
    cy.contains('1 - 1 of 1');
    cy.get('#robot-account-search').clear();

    // Filter for a non-existent robot account
    cy.get('#robot-account-search').type('somethingrandome');
    cy.contains('0 - 0 of 0');
    cy.get('#robot-account-search').clear();
  });

  it('Robot Account Toolbar Items', () => {
    cy.visit('/organization/testorg?tab=Robot+accounts');

    // Open and cancel modal
    cy.get('#create-robot-account-btn').click();
    cy.get('#create-robot-cancel').click();

    // Expand-Collapse Tab
    cy.get('#expand-tab').should('have.text', 'Expand');
    cy.get('#collapse-tab').should('have.text', 'Collapse');
  });

  it('Create Robot', () => {
    cy.visit('/organization/testorg?tab=Robot+accounts');

    cy.get('#create-robot-account-btn').click();
    cy.get('#robot-wizard-form-name').type('newtestrob');
    cy.get('#robot-wizard-form-description').type(
      "This is newtestrob's description",
    );
    cy.get('#create-robot-submit').click();

    cy.wait(3000);
    cy.get('#robot-account-search').type('newtestrob');
    cy.contains('1 - 1 of 1');
  });

  it('Delete Robot', () => {
    cy.visit('/organization/testorg?tab=Robot+accounts');

    // Delete robot account
    cy.get('#robot-account-search').type('testrobot2');
    cy.contains('1 - 1 of 1');
    cy.get('button[id="testorg+testrobot2-toggle-kebab"]').click();
    cy.get('li[id="testorg+testrobot2-del-btn"]').contains('Delete').click();

    cy.get('#delete-confirmation-input').type('confirm');
    cy.get('[id="bulk-delete-modal"]').within(() =>
      cy.get('button:contains("Delete")').click(),
    );

    // Validate org was deleted
    cy.wait(9000);
    cy.get('#robot-account-search').type('testrobot2');
    cy.contains('0 - 0 of 0');
  });
});
