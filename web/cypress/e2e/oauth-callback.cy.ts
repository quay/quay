/// <reference types="cypress" />

describe('OAuth Callback', () => {
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
        external_login: [
          {
            id: 'github',
            title: 'GitHub',
            icon: 'github',
          },
        ],
      },
    }).as('getConfig');
  });

  it('displays error for account already associated', () => {
    // Mock the backend error response - only intercept axios requests with JSON accept header
    cy.intercept(
      {
        method: 'GET',
        url: '/oauth2/github/callback*',
        headers: {
          accept: /application\/json/,
        },
      },
      {
        statusCode: 400,
        body: {
          error_info: {
            reason: 'ologinerror',
            service_name: 'GitHub',
            error_message:
              'The e-mail address test@example.com is already associated with an existing account.',
            register_redirect: true,
          },
        },
      },
    ).as('oauthError');

    cy.visit('/oauth2/github/callback?error=ologinerror');
    cy.wait('@oauthError');

    // Check error title and message are displayed
    cy.contains('github Authentication Error');
    cy.contains(
      'The e-mail address test@example.com is already associated with an existing account',
    );

    // Check buttons are present
    cy.contains('Sign in with username/password').should('be.visible');
    cy.contains('Try again').should('be.visible');

    // Check account association message
    cy.contains('You can associate your github account after signing in');
  });

  it('displays error for access denied', () => {
    cy.intercept(
      {
        method: 'GET',
        url: '/oauth2/github/callback*',
        headers: {
          accept: /application\/json/,
        },
      },
      {
        statusCode: 400,
        body: {
          error_info: {
            reason: 'access_denied',
            service_name: 'GitHub',
            error_message: 'Access was denied. Please try again.',
          },
        },
      },
    ).as('oauthError');

    cy.visit('/oauth2/github/callback?error=access_denied');
    cy.wait('@oauthError');

    cy.contains('github Authentication Error');
    cy.contains('Access was denied. Please try again.');
    cy.contains('Sign in with username/password').should('be.visible');
  });

  it('handles invalid provider', () => {
    cy.visit('/oauth2/invalid/callback?error=test');

    // Should show error for invalid provider using fallback message
    cy.contains('Authentication Error');
  });

  it('navigates to signin when clicking sign in button', () => {
    cy.intercept(
      {
        method: 'GET',
        url: '/oauth2/github/callback*',
        headers: {
          accept: /application\/json/,
        },
      },
      {
        statusCode: 400,
        body: {
          error_info: {
            reason: 'ologinerror',
            service_name: 'GitHub',
            error_message: 'Test error message',
          },
        },
      },
    ).as('oauthError');

    cy.visit('/oauth2/github/callback?error=ologinerror');
    cy.wait('@oauthError');

    cy.contains('Sign in with username/password').click();
    cy.url().should('include', '/signin');
  });
});
