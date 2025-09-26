/// <reference types="cypress" />

describe('External Login Authentication', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');

    // Mock common API calls to prevent uncaught exceptions
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 401,
      body: {message: 'Unauthorized'}
    }).as('getUser');

    cy.intercept('GET', '/csrf_token', {
      body: {csrf_token: 'test-csrf-token'}
    }).as('getCsrfToken');
  });

  it('displays external login providers when configured', () => {
    cy.intercept('GET', '/config', {
      fixture: 'config-with-external-login.json',
    }).as('getConfig');

    cy.visit('/signin');
    cy.wait('@getConfig');

    // Should display external login buttons
    cy.get('[data-testid="external-login-github"]').should('be.visible');
    cy.get('[data-testid="external-login-google"]').should('be.visible');

    // Should display "or" divider when both external and direct login are available
    cy.get('.login-divider').should('be.visible');
    cy.get('.login-divider span').should('contain.text', 'or');

    // Should still show database login form
    cy.get('#pf-login-username-id').should('be.visible');
    cy.get('#pf-login-password-id').should('be.visible');
  });

  it('hides database login when DIRECT_LOGIN is false', () => {
    cy.intercept('GET', '/config', {
      fixture: 'config-external-only.json',
    }).as('getConfig');

    cy.visit('/signin');
    cy.wait('@getConfig');

    // Should display external login buttons
    cy.get('[data-testid="external-login-github"]').should('be.visible');
    cy.get('[data-testid="external-login-google"]').should('be.visible');

    // Should NOT display database login form
    cy.get('#pf-login-username-id').should('not.exist');
    cy.get('#pf-login-password-id').should('not.exist');

    // Should NOT display "or" divider
    cy.get('.login-divider').should('not.exist');
  });

  it('auto-redirects to SSO when single provider and DIRECT_LOGIN disabled', () => {
    cy.intercept('GET', '/config', {
      fixture: 'config-single-sso.json',
    }).as('getConfig');

    cy.intercept('POST', '/api/v1/externallogin/github', {
      statusCode: 200,
      body: {
        auth_url: 'https://github.com/login/oauth/authorize?client_id=test',
      },
    }).as('getAuthUrl');

    cy.visit('/signin');
    cy.wait('@getConfig');

    // Should automatically make external login request
    cy.wait('@getAuthUrl');

    // Should store redirect URL in localStorage - check immediately after API call
    cy.wait(100); // Brief wait to ensure localStorage is set
    cy.window()
      .its('localStorage')
      .invoke('getItem', 'quay.redirectAfterLoad')
      .should('exist');
  });

  it('handles external login button click', () => {
    cy.intercept('GET', '/config', {
      fixture: 'config-with-external-login.json',
    }).as('getConfig');

    cy.intercept('POST', '/api/v1/externallogin/github', {
      statusCode: 200,
      body: {
        auth_url:
          'https://github.com/login/oauth/authorize?client_id=test&redirect_uri=http://localhost/signin',
      },
    }).as('getAuthUrl');

    cy.visit('/signin');
    cy.wait('@getConfig');

    // Click external login button
    cy.get('[data-testid="external-login-github"]').click();

    // Should call external login API
    cy.wait('@getAuthUrl').then((interception) => {
      expect(interception.request.body).to.deep.equal({
        kind: 'login',
      });
    });

    // Should store redirect URL in localStorage before redirect happens
    cy.wait(100); // Brief wait to ensure localStorage is set
    cy.window()
      .its('localStorage')
      .invoke('getItem', 'quay.redirectAfterLoad')
      .should('exist');
  });

  it('displays message when no login options are available', () => {
    cy.intercept('GET', '/config', {
      fixture: 'config-no-login-options.json',
    }).as('getConfig');

    cy.visit('/signin');
    cy.wait('@getConfig');

    // Should display info message
    cy.get('[data-testid="no-login-options-alert"]', {timeout: 10000}).should('be.visible');
    cy.get('[data-testid="no-login-options-alert"]').should(
      'contain.text',
      'Direct login is disabled',
    );
    cy.get('[data-testid="no-login-options-alert"]').should(
      'contain.text',
      'Please contact your administrator for login instructions',
    );
  });

  it('handles redirect URL parameter correctly', () => {
    cy.intercept('GET', '/config', {
      fixture: 'config-with-external-login.json',
    }).as('getConfig');

    cy.intercept('POST', '/api/v1/externallogin/github', {
      statusCode: 200,
      body: {
        auth_url: 'https://github.com/login/oauth/authorize?client_id=test',
      },
    }).as('getAuthUrl');

    // Visit signin with redirect URL
    cy.visit('/signin?redirect_url=/repository/test/repo');
    cy.wait('@getConfig');

    // Click external login button
    cy.get('[data-testid="external-login-github"]').click();

    cy.wait('@getAuthUrl');

    // Should store redirect URL in localStorage
    cy.window()
      .its('localStorage')
      .invoke('getItem', 'quay.redirectAfterLoad')
      .should('include', '/repository/test/repo');
  });
});
