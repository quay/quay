/// <reference types="cypress" />

describe('Repository Settings - Vulnerability Reporting', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['UI_V2_REPO_SETTINGS'] = true;
        return res;
      }),
    ).as('getConfig');
  });

  it('View and reset suppressions', () => {
    cy.visit('/repository/user1/hello-world?tab=settings');
    cy.contains('Vulnerability Reporting').click();
    cy.get('.tags-input').contains('PVE-2022-50870');
    cy.get('[id="save-suppressions-button"]').should('be.disabled');
    cy.get('[id="tags-input"]').type('PVE-2022-47833{enter}');
    cy.get('[id="save-suppressions-button"]').should('be.enabled');
    cy.get('[id="reset-suppressions-button"]').click();
    cy.get('[id="save-suppressions-button"]').should('be.disabled');
    cy.get('.tags-input').contains('PVE-2022-50870');
    cy.get('.tags-input').should('not.contain', 'PVE-2022-47833');
  });

  it('Update suppressions', () => {
    cy.visit('/repository/user1/hello-world?tab=settings');
    cy.contains('Vulnerability Reporting').click();
    cy.get('.tags-input').contains('PVE-2022-50870');
    cy.get('[id="save-suppressions-button"]').should('be.disabled');
    cy.get('[id="tags-input"]').type('PVE-2022-47833{enter}');
    cy.get('[id="save-suppressions-button"]').should('be.enabled');
    cy.intercept('PUT', '/api/v1/repository/user1/hello-world').as(
      'updateRepo',
    );
    cy.get('[id="save-suppressions-button"]').click();
    cy.wait('@updateRepo');
    cy.contains('Successfully updated vulnerability suppressions');
  });

  it('Should not be visible without FEATURE_SECURITY_VULNERABILITY_SUPPRESSION', () => {
    cy.intercept('GET', '/config', (req) =>
      req.reply((res) => {
        res.body.features['UI_V2_REPO_SETTINGS'] = true;
        res.body.features['SECURITY_VULNERABILITY_SUPPRESSION'] = false;
        return res;
      }),
    ).as('getConfigNoVulnSuppression');
    cy.visit('/repository/user1/hello-world?tab=settings');
    cy.get('#pf-tab-4-vulnerabilityreporting').should('not.exist');
  });
});
