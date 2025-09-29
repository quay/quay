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

  // Helper function to setup OAuth error response
  const setupOAuthError = (provider, errorInfo) => {
    cy.intercept('GET', `/oauth2/${provider}/callback*`, {
      statusCode: 400,
      body: {error_info: errorInfo},
    }).as('oauthError');
  };

  it('displays error for account already associated', () => {
    setupOAuthError('github', {
      reason: 'ologinerror',
      service_name: 'GitHub',
      error_message:
        'The e-mail address test@example.com is already associated with an existing account.',
      register_redirect: true,
    });

    cy.visit('/oauth2/github/callback?error=ologinerror');
    cy.wait('@oauthError');

    // Check error message is displayed
    cy.contains('GitHub Authentication Error');
    cy.contains(
      'The e-mail address test@example.com is already associated with an existing account',
    );

    // Check buttons are present
    cy.contains('Sign in with username/password').should('be.visible');
    cy.contains('Try again').should('be.visible');

    // Check account association message
    cy.contains('You can associate your GitHub account after signing in');
  });

  it('displays error for access denied', () => {
    setupOAuthError('github', {
      reason: 'access_denied',
      service_name: 'GitHub',
      error_message: 'Access was denied. Please try again.',
    });

    cy.visit('/oauth2/github/callback?error=access_denied');
    cy.wait('@oauthError');

    cy.contains('GitHub Authentication Error');
    cy.contains('Access was denied. Please try again.');
    cy.contains('Sign in with username/password').should('be.visible');
  });

  it('redirects to signin for invalid provider', () => {
    cy.visit('/oauth2/invalid/callback?error=test');
    cy.url().should('include', '/signin?error=invalid_provider');
  });

  it('handles success callback by redirecting to backend', () => {
    // Visit success callback URL
    cy.visit('/oauth2/github/callback?code=test123&state=xyz789');

    // Should redirect to backend for processing
    // We can't easily test the redirect but can verify the component renders
    cy.contains('Completing github authentication...');
  });

  it('navigates to signin when clicking sign in button', () => {
    setupOAuthError('github', {
      reason: 'ologinerror',
      service_name: 'GitHub',
      error_message: 'Test error message',
    });

    cy.visit('/oauth2/github/callback?error=ologinerror');
    cy.wait('@oauthError');

    cy.contains('Sign in with username/password').click();
    cy.url().should('include', '/signin');
  });
});
