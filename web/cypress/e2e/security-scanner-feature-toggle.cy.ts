/// <reference types="cypress" />

describe('Security Scanner Feature Toggle', () => {
  beforeEach(() => {
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  describe('When SECURITY_SCANNER is enabled', () => {
    before(() => {
      // Enable security scanner feature
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.features['SECURITY_SCANNER'] = true;
          return res;
        }),
      ).as('getConfig');
    });

    it('displays Security column in tags table', () => {
      cy.visit('/repository/user1/hello-world?tab=tags');

      // Verify Security column header exists
      cy.get('th').contains('Security').should('be.visible');
    });

    it('displays Security Report tab in tag details', () => {
      cy.visit('/repository/user1/hello-world/tag/latest');

      // Verify Security Report tab exists and is visible
      cy.contains('[role="tab"]', 'Security Report').should('be.visible');
    });

    it('displays Packages tab in tag details', () => {
      cy.visit('/repository/user1/hello-world/tag/latest');

      // Verify Packages tab exists and is visible
      cy.contains('[role="tab"]', 'Packages').should('be.visible');
    });

    it('allows navigation to Security Report tab', () => {
      cy.visit('/repository/user1/hello-world/tag/latest');

      // Click Security Report tab
      cy.contains('[role="tab"]', 'Security Report').click();

      // Verify we're on the security report tab
      cy.url().should('include', 'tab=securityreport');
    });

    it('allows navigation to Packages tab', () => {
      cy.visit('/repository/user1/hello-world/tag/latest');

      // Click Packages tab
      cy.contains('[role="tab"]', 'Packages').click();

      // Verify we're on the packages tab
      cy.url().should('include', 'tab=packages');
    });

    it('displays Vulnerabilities section in Details tab', () => {
      cy.visit('/repository/user1/hello-world/tag/latest');

      // Verify Vulnerabilities section exists
      cy.get('[data-testid="vulnerabilities"]').should('be.visible');
      cy.get('[data-testid="vulnerabilities"]').within(() => {
        cy.contains('Vulnerabilities').should('exist');
      });
    });
  });

  describe('When SECURITY_SCANNER is disabled', () => {
    before(() => {
      // Disable security scanner feature
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.features['SECURITY_SCANNER'] = false;
          return res;
        }),
      ).as('getConfig');
    });

    it('does not display Security column in tags table', () => {
      cy.visit('/repository/user1/hello-world?tab=tags');

      // Verify Security column header does not exist
      cy.get('th').contains('Security').should('not.exist');
    });

    it('does not display Security Report tab in tag details', () => {
      cy.visit('/repository/user1/hello-world/tag/latest');

      // Verify Security Report tab is hidden
      cy.contains('[role="tab"]', 'Security Report').should('not.exist');
    });

    it('does not display Packages tab in tag details', () => {
      cy.visit('/repository/user1/hello-world/tag/latest');

      // Verify Packages tab is hidden
      cy.contains('[role="tab"]', 'Packages').should('not.exist');
    });

    it('does not display Vulnerabilities section in Details tab', () => {
      cy.visit('/repository/user1/hello-world/tag/latest');

      // Verify Vulnerabilities section is hidden
      cy.get('[data-testid="vulnerabilities"]').should('not.exist');
    });
  });
});
