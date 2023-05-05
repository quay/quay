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
    cy.visit('/organization/testorg?tab=Robotaccounts');

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
    cy.visit('/organization/testorg?tab=Robotaccounts');

    // Open and cancel modal
    cy.get('#create-robot-account-btn').click();
    cy.get('#create-robot-cancel').click();

    // Expand-Collapse Tab
    cy.get('#expand-tab').should('have.text', 'Expand');
    cy.get('#collapse-tab').should('have.text', 'Collapse');
  });

  it('Create Robot', () => {
    cy.visit('/organization/testorg?tab=Robotaccounts');

    cy.get('#create-robot-account-btn').click();
    cy.get('#robot-wizard-form-name').type('newtestrob');
    cy.get('#robot-wizard-form-description').type(
      "This is newtestrob's description",
    );
    cy.get('#create-robot-submit')
      .click()
      .then(() => {
        cy.get('#robot-account-search').type('newtestrob');
        cy.contains('1 - 1 of 1');
      });

    //  check that states are cleared after creating robot account
    cy.get('#create-robot-account-btn').click();
    cy.get('#robot-wizard-form-name').should('be.empty');
    cy.get('#robot-wizard-form-description').should('be.empty');
    cy.get('button:contains("Add to team (optional)")').click();
    cy.get('#add-team-bulk-select').should('not.be.checked');
    cy.get('button:contains("Add to repository (optional)")').click();
    cy.get('#add-repository-bulk-select').should('not.be.checked');
    cy.get('button:contains("Default permissions (optional)")').click();
    cy.get('#toggle-descriptions').contains('None');
  });

  it('Delete Robot', () => {
    cy.visit('/organization/testorg?tab=Robotaccounts');

    // Delete robot account
    cy.get('#robot-account-search').type('testrobot2');
    cy.contains('1 - 1 of 1');
    cy.get('button[id="testorg+testrobot2-toggle-kebab"]').click();
    cy.get('li[id="testorg+testrobot2-del-btn"]').contains('Delete').click();

    cy.get('#delete-confirmation-input').type('confirm');
    cy.get('[id="bulk-delete-modal"]')
      .within(() => cy.get('button:contains("Delete")').click())
      .then(() => {
        cy.get('#robot-account-search').clear().type('testrobot2');
        cy.contains('0 - 0 of 0');
      });
  });

  it('Update Repo Permissions', () => {
    cy.visit('/organization/testorg?tab=Robotaccounts');
    cy.contains('1 repository').click();
    cy.get('#add-repository-bulk-select-text').contains('1 selected');
    cy.get('#toggle-descriptions').click();
    cy.get('[role="menuitem"]').contains('Admin').click();
    cy.get('footer')
      .find('button:contains("Save")')
      .click()
      .then(() => {
        cy.get('footer').find('button:contains("Save")').should('not.exist');
        cy.get('#toggle-descriptions').contains('Admin');
      });
  });

  it('Bulk Update Repo Permissions', () => {
    const robotAccnt = 'testorg+testrobot2';
    cy.visit('/organization/testorg');
    cy.contains('Create Repository').click();
    cy.get('input[id="repository-name-input"]').type('testrepo1');
    cy.get('[id="create-repository-modal"]').within(() =>
      cy.get('button:contains("Create")').click(),
    );

    cy.visit('/organization/testorg?tab=Robotaccounts');
    cy.get(`[id="${robotAccnt}-toggle-kebab"]`).click();
    cy.get(`[id="${robotAccnt}-set-repo-perms-btn"]`).click();
    cy.get('#add-repository-bulk-select').click();
    cy.get('#toggle-bulk-perms-kebab').click();
    cy.get('[role="menuitem"]').contains('Write').click();
    cy.get('footer')
      .find('button:contains("Save")')
      .click()
      .then(() => {
        cy.get('[data-label="Permissions"]').each(($item) => {
          cy.wrap($item).contains('Write');
        });
      });
  });
});
