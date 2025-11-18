/// <reference types="cypress" />

describe('Session Timeout Modal', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');

    // Mock config endpoint
    cy.intercept('GET', '/config', {
      body: {
        features: {
          DIRECT_LOGIN: true,
        },
        config: {
          AUTHENTICATION_TYPE: 'Database',
        },
        external_login: [],
      },
    }).as('getConfig');

    // Mock CSRF token endpoint
    cy.intercept('GET', '/csrf_token', {
      body: {csrf_token: 'test-token'},
    }).as('getCsrfToken');
  });

  it('Shows session expired modal when API returns 401', () => {
    // Mock the user API to return 401 to simulate session timeout
    // This needs to be set up BEFORE visiting the page
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 401,
      body: {
        detail: 'Unauthorized',
        error_message: 'Unauthorized',
        error_type: 'unauthorized',
        title: 'unauthorized',
      },
    }).as('getUser401');

    // Visit any authenticated page (organizations list)
    cy.visit('/organization');

    // Wait for the 401 response
    cy.wait('@getUser401');

    // Verify that the Session Expired modal appears
    cy.get('[role="dialog"]').should('be.visible');
    cy.contains('Session Expired').should('be.visible');
    cy.contains(
      'Your user session has expired. Please sign in to continue.',
    ).should('be.visible');

    // Verify the Sign In button is present
    cy.contains('button', 'Sign In').should('be.visible');
  });

  it('Redirects to signin page when Sign In button is clicked', () => {
    // Mock API to return 401
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 401,
      body: {
        detail: 'Unauthorized',
        error_message: 'Unauthorized',
        error_type: 'unauthorized',
        title: 'unauthorized',
      },
    }).as('getUser401');

    // Visit any authenticated page
    cy.visit('/organization');

    // Wait for the 401 response
    cy.wait('@getUser401');

    // Click the Sign In button in the modal
    cy.contains('button', 'Sign In').click();

    // Verify redirect to signin page
    cy.url().should('include', '/signin');

    // Verify no CSRF error message appears
    cy.contains('CSRF token expired').should('not.exist');
  });

  it('Does not show modal for fresh_login_required 401', () => {
    // Mock API to return 401 with fresh_login_required error type
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 401,
      body: {
        detail: 'Fresh login required',
        error_message: 'Fresh login required',
        error_type: 'fresh_login_required',
        title: 'fresh_login_required',
      },
    }).as('getUserFreshLogin');

    // Visit any authenticated page
    cy.visit('/organization');

    // Wait for the 401 response
    cy.wait('@getUserFreshLogin');

    // Verify that the Session Expired modal does NOT appear
    cy.contains('Session Expired').should('not.exist');

    // The Fresh Login modal should appear instead (if implemented)
    // This test confirms the session expired modal doesn't incorrectly trigger
  });

  it('Modal only appears once even with multiple 401 errors', () => {
    // Mock multiple endpoints to return 401
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 401,
      body: {
        detail: 'Unauthorized',
        error_type: 'unauthorized',
      },
    }).as('getUser401');

    cy.intercept('GET', '/api/v1/superuser/organizations/', {
      statusCode: 401,
      body: {
        detail: 'Unauthorized',
        error_type: 'unauthorized',
      },
    }).as('getOrganizations401');

    // Visit any authenticated page
    cy.visit('/organization');

    // Wait for the 401 responses
    cy.wait('@getUser401');

    // Verify only one Session Expired modal appears
    cy.get('[role="dialog"]').should('have.length', 1);
    cy.contains('Session Expired').should('be.visible');
  });

  it('Sign in works correctly after session timeout redirect', () => {
    // Mock API to return 401
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 401,
      body: {
        detail: 'Unauthorized',
        error_type: 'unauthorized',
      },
    }).as('getUser401');

    // Visit authenticated page
    cy.visit('/organization');

    // Wait for 401
    cy.wait('@getUser401');

    // Click Sign In in modal
    cy.contains('button', 'Sign In').click();

    // Should be on signin page
    cy.url().should('include', '/signin');

    // Mock successful signin
    cy.intercept('POST', '/api/v1/signin', {
      statusCode: 200,
      body: {success: true},
    }).as('signinSuccess');

    // Mock user API for successful login
    cy.intercept('GET', '/api/v1/user/', {
      statusCode: 200,
      body: {
        anonymous: false,
        username: 'user1',
        email: 'user1@example.com',
        verified: true,
        prompts: [],
        organizations: [],
        logins: [],
      },
    }).as('getUser');

    // Fill and submit login form
    cy.get('#pf-login-username-id').type('user1');
    cy.get('#pf-login-password-id').type('password');
    cy.get('button[type=submit]').click();

    // Should successfully sign in and redirect
    cy.wait('@signinSuccess');
    cy.wait('@getCsrfToken');
    cy.wait('@getUser');
    cy.url().should('include', '/organization');
  });
});
