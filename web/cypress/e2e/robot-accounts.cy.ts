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
        cy.get('.pf-c-alert.pf-m-success')
          .contains(
            'Successfully created robot account with robot name: newtestrob',
          )
          .should('exist');
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
        cy.get('.pf-c-alert.pf-m-success')
          .contains('Successfully deleted robot account')
          .should('exist');
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
        cy.get('.pf-c-alert.pf-m-success')
          .contains('Successfully updated repository permission')
          .should('exist');
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
        cy.get('.pf-c-alert.pf-m-success')
          .contains('Successfully updated repository permission')
          .should('exist');
        cy.get('[data-label="Permissions"]').each(($item) => {
          cy.wrap($item).contains('Write');
        });
      });
  });

  it('Create Robot Acct Wizard For Org', () => {
    cy.visit('/organization/testorg');
    cy.get('.pf-c-tabs').get('ul').contains('Robot accounts');
    cy.get('.pf-c-tabs').get('ul').contains('Robot accounts').click();
    cy.get('#create-robot-account-btn').click();
    cy.get('#create-robot-account-modal')
      .get('.pf-c-wizard__nav')
      .get('.pf-c-wizard__nav-item')
      .should('have.length', 5);
    cy.get('#create-robot-account-modal')
      .get('.pf-c-wizard__nav')
      .get('.pf-c-wizard__nav-item')
      .should((items) => {
        expect(items[0]).to.contain.text('Robot name and description');
        expect(items[1]).to.contain.text('Add to team (optional)');
        expect(items[2]).to.contain.text('Add to repository (optional)');
        expect(items[3]).to.contain.text('Default permissions (optional)');
        expect(items[4]).to.contain.text('Review and Finish');
      });
    cy.get('#create-robot-account-modal')
      .get('.pf-c-wizard__nav')
      .get('.pf-c-wizard__nav-item')
      .contains('Review and Finish')
      .click();
    cy.get('.pf-c-wizard__main-body')
      .find('form')
      .find('.pf-c-toggle-group')
      .find('button')
      .should('have.length', 3);
    cy.get('.pf-c-wizard__main-body')
      .find('form')
      .find('.pf-c-toggle-group__item')
      .should((items) => {
        expect(items[0]).to.contain.text('Teams');
        expect(items[1]).to.contain.text('Repositories');
        expect(items[2]).to.contain.text('Default permissions');
      });
  });

  it('Create Robot Acct Wizard For User Namespace', () => {
    cy.visit('/organization/user1');
    cy.get('.pf-c-tabs').get('ul').contains('Robot accounts');
    cy.get('.pf-c-tabs').get('ul').contains('Robot accounts').click();
    cy.contains('button', 'Create robot account').click();
    cy.get('#create-robot-account-modal')
      .get('.pf-c-wizard__nav')
      .get('.pf-c-wizard__nav-item')
      .should('have.length', 3);
    cy.get('#create-robot-account-modal')
      .get('.pf-c-wizard__nav')
      .get('.pf-c-wizard__nav-item')
      .should((items) => {
        expect(items[0]).to.contain.text('Robot name and description');
        expect(items[1]).to.contain.text('Add to repository (optional)');
        expect(items[2]).to.contain.text('Review and Finish');
      });
    cy.get('#create-robot-account-modal')
      .get('.pf-c-wizard__nav')
      .get('.pf-c-wizard__nav-item')
      .contains('Review and Finish')
      .click();
    cy.get('.pf-c-wizard__main-body')
      .find('form')
      .find('.pf-c-toggle-group')
      .find('button')
      .should('have.length', 1);
    cy.get('.pf-c-wizard__main-body')
      .find('form')
      .find('.pf-c-toggle-group__item')
      .should((items) => {
        expect(items[0]).to.contain.text('Repositories');
      });
  });

  it('Create Robot Acct For User Namespace', () => {
    cy.visit('/organization/user1?tab=Robotaccounts');
    cy.contains('button', 'Create robot account').click();

    cy.get('#robot-wizard-form-name').type('userrobot');
    cy.get('#robot-wizard-form-description').type(
      "This is userrobot's description",
    );
    cy.get('#create-robot-submit')
      .click()
      .then(() => {
        cy.get('.pf-c-alert.pf-m-success')
          .contains(
            'Successfully created robot account with robot name: userrobot',
          )
          .should('exist');
        cy.get('#robot-account-search').type('userrobot');
        cy.contains('1 - 1 of 1');
      });
  });
});
