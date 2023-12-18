/// <reference types="cypress" />

describe('Org Settings Page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.visit('/signin');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.intercept('GET', '/api/v1/plans/', {fixture: 'plans.json'}).as(
      'getPlans',
    );
  });

  it('General Settings', () => {
    cy.visit('/organization/projectquay?tab=Settings');

    // Type a bad e-mail
    cy.get('#org-settings-email').clear();
    cy.get('#org-settings-email').type('this is not a good e-mail');
    cy.contains('Please enter a valid email address');

    // Leave empty
    cy.get('#org-settings-email').clear();
    cy.contains('Please enter email associate with namespace');

    // check is disabled
    cy.get('#save-org-settings').should('be.disabled');
    cy.get('#org-settings-email').clear();

    // Type a good e-mail and save
    cy.get('#org-settings-email').type('good-email@redhat.com');
    cy.get('#save-org-settings').click();

    // refresh page and check if email is saved
    cy.reload();
    cy.get('#org-settings-email').should('have.value', 'good-email@redhat.com');
  });

  it('Billing Information', () => {
    cy.visit('/organization/projectquay?tab=Settings');

    // navigate to billing tab
    cy.get('#pf-tab-1-billinginformation').click();

    // Type a bad e-mail
    cy.get('#billing-settings-invoice-email').clear();
    cy.get('#billing-settings-invoice-email').type('this is not a good e-mail');

    // check is disabled
    cy.get('#save-billing-settings').should('be.disabled');
    cy.get('#billing-settings-invoice-email').clear();

    // Type a good e-mail and save
    cy.get('#billing-settings-invoice-email').type('invoice-email@redhat.com');

    // check save receipts
    cy.get('#checkbox').should('not.be.checked');
    cy.get('#checkbox').click();

    // Save
    cy.get('#save-billing-settings').click();

    // refresh page, navigate to billing tab and check if email is saved
    cy.reload();
    cy.get('#pf-tab-1-billinginformation').click();
    cy.get('#billing-settings-invoice-email').should(
      'have.value',
      'invoice-email@redhat.com',
    );
    cy.get('#checkbox').should('be.checked');
  });

  it('Cli Token Invisible', () => {
    cy.visit('/organization/projectquay?tab=Settings');

    // ensure cli token tab is not on page
    cy.get('#pf-tab-2-cliconfig').should('not.exist');
  });

  it('View and update suppressions', () => {
    cy.visit('/organization/projectquay?tab=Settings');

    cy.contains('Vulnerability Reporting').click();
    cy.get('.tags-input').should('exist');
    cy.get('[id="save-suppressions-button"]').should('be.disabled');
    cy.get('[id="tags-input"]').type('CVE-2014-6271{enter}');
    cy.get('[id="save-suppressions-button"]').should('be.enabled');

    cy.intercept('PUT', '/api/v1/organization/projectquay').as(
      'updateOrgSuppressions',
    );

    cy.get('[id="save-suppressions-button"]').click();
    cy.wait('@updateOrgSuppressions');

    cy.reload();
    cy.contains('Vulnerability Reporting').click();
    cy.get('.tags-input').contains('CVE-2014-627');
  });

  it('Should not be visible without FEATURE_SECURITY_VULNERABILITY_SUPPRESSION', () => {
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['UI_V2_REPO_SETTINGS'] = true;
        res.body.features['SECURITY_VULNERABILITY_SUPPRESSION'] = false;
        return res;
      }),
    ).as('getConfigNoVulnSuppression');
    cy.visit('/organization/projectquay?tab=Settings');
    cy.contains('Vulnerability Reporting').should('not.exist');
  });
});
