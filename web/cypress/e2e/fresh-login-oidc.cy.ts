/// <reference types="cypress" />

describe('Fresh Login - OIDC Authentication', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  describe('OIDC Authentication - Fresh Login', () => {
    beforeEach(() => {
      // Use fixture and modify for OIDC
      cy.fixture('config.json').then((config) => {
        config.config.AUTHENTICATION_TYPE = 'OIDC';
        config.features.DIRECT_LOGIN = false;
        config.features.SUPER_USERS = true;
        config.external_login = [
          {
            id: 'oidc',
            title: 'Azure AD',
            icon: '/static/img/azure.png',
          },
        ];
        cy.intercept('GET', '/config', config).as('getConfigOIDC');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });
    });

    it('should redirect to signin when fresh_login_required occurs for OIDC users', () => {
      // Mock fresh_login_required error from superuser endpoint
      cy.intercept('GET', '/api/v1/superuser/logs*', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_type: 'fresh_login_required',
          detail: 'The action requires a fresh login to succeed.',
        },
      }).as('freshLoginRequired');

      cy.visit('/usage-logs');
      cy.wait('@getConfigOIDC');
      cy.wait('@getSuperUser');

      // Wait for fresh login error and redirect
      cy.wait('@freshLoginRequired');

      // Should redirect to signin page with redirect_url parameter
      cy.url().should('include', '/signin?redirect_url=');
      cy.url().should('include', 'usage-logs');

      // Password modal should NOT appear
      cy.contains('Please Verify').should('not.exist');
      cy.contains('Current Password').should('not.exist');
    });

    it('should preserve query parameters in redirect URL for OIDC users', () => {
      cy.intercept('GET', '/api/v1/superuser/logs*', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_type: 'fresh_login_required',
          detail: 'The action requires a fresh login to succeed.',
        },
      }).as('freshLoginRequired');

      // Visit superuser page with query parameters
      cy.visit('/usage-logs?starttime=01/01/2025&endtime=01/31/2025');
      cy.wait('@getConfigOIDC');
      cy.wait('@getSuperUser');
      cy.wait('@freshLoginRequired');

      // Should encode the entire URL including query parameters
      cy.url().should('include', '/signin?redirect_url=');
      cy.url().should('include', 'usage-logs');
      cy.url().should('include', 'starttime');
      cy.url().should('include', 'endtime');
    });
  });

  describe('Database Authentication - Fresh Login', () => {
    beforeEach(() => {
      // Use fixture with Database authentication (default)
      cy.fixture('config.json').then((config) => {
        config.config.AUTHENTICATION_TYPE = 'Database';
        config.features.DIRECT_LOGIN = true;
        config.features.SUPER_USERS = true;
        config.external_login = [];
        cy.intercept('GET', '/config', config).as('getConfigDatabase');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });
    });

    it('should show password modal for Database users (not redirect)', () => {
      // Mock fresh_login_required error from superuser endpoint
      cy.intercept('GET', '/api/v1/superuser/logs*', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_type: 'fresh_login_required',
          detail: 'The action requires a fresh login to succeed.',
        },
      }).as('freshLoginRequired');

      cy.visit('/usage-logs');
      cy.wait('@getConfigDatabase');
      cy.wait('@getSuperUser');
      cy.wait('@freshLoginRequired');

      // Password modal SHOULD appear for Database auth
      cy.contains('Please Verify').should('be.visible');
      cy.contains('Current Password').should('be.visible');

      // Should NOT redirect to signin
      cy.url().should('include', '/usage-logs');
      cy.url().should('not.include', '/signin');
    });
  });
});
