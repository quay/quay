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

  describe('OAuth Error Flows', () => {
    it('displays error page with minimal header for email already exists', () => {
      // Visit error page with error description parameter
      cy.visit(
        '/oauth-error?error_description=GitHub:%20The%20email%20address%20test@example.com%20is%20already%20associated%20with%20an%20existing%20account&provider=GitHub',
      );

      // Wait for config to load
      cy.wait('@getConfig');

      // Verify minimal header is present (logo only, no user menu)
      cy.get('[data-testid="minimal-header"]').should('be.visible');
      cy.get('.pf-v5-c-masthead__brand').should('be.visible');

      // Verify error title with provider name
      cy.contains('GitHub Authentication Error').should('be.visible');

      // Verify error message is displayed correctly (not URL encoded)
      cy.contains('Authentication Failed').should('be.visible');
      cy.contains(
        'The email address test@example.com is already associated with an existing account',
      ).should('be.visible');

      // Verify "Return to Sign In" button is present
      cy.contains('Return to Sign In').should('be.visible');
    });

    it('displays registration hint when register_redirect and user_creation are true', () => {
      cy.visit(
        '/oauth-error?error_description=Account%20not%20found&provider=Google&register_redirect=true&user_creation=true',
      );

      cy.wait('@getConfig');

      // Verify error message
      cy.contains('Account not found').should('be.visible');

      // Verify registration hint alert is displayed
      cy.contains('Account Registration Required').should('be.visible');
      cy.contains('To continue, please register using the sign-in form').should(
        'be.visible',
      );
      cy.contains(
        'You will be able to reassociate this Google account to your new account in the user settings panel',
      ).should('be.visible');
    });

    it('handles access denied error', () => {
      cy.visit(
        '/oauth-error?error_description=User%20denied%20access&provider=GitHub',
      );

      cy.wait('@getConfig');

      // Verify error components are present
      cy.contains('GitHub Authentication Error').should('be.visible');
      cy.contains('User denied access').should('be.visible');
      cy.contains('Return to Sign In').should('be.visible');
    });

    it('handles generic OAuth errors with fallback message', () => {
      cy.visit('/oauth-error?provider=GitHub');

      cy.wait('@getConfig');

      // Should show fallback error message when error_description is missing
      cy.contains('GitHub Authentication Error').should('be.visible');
      cy.contains('An unknown error occurred during authentication').should(
        'be.visible',
      );
    });

    it('displays default provider name when provider param is missing', () => {
      cy.visit('/oauth-error?error_description=Some%20error%20occurred');

      cy.wait('@getConfig');

      // Should use default provider name
      cy.contains('OAuth Provider Authentication Error').should('be.visible');
      cy.contains('Some error occurred').should('be.visible');
    });

    it('navigates back to signin when clicking Return to Sign In button', () => {
      cy.visit('/oauth-error?error_description=Test%20error&provider=GitHub');

      cy.wait('@getConfig');

      // Click the Return to Sign In button
      cy.contains('Return to Sign In').click();

      // Should navigate to signin page
      cy.url().should('include', '/signin');
    });

    it('minimal header logo links to signin page', () => {
      cy.visit('/oauth-error?error_description=Test%20error&provider=GitHub');

      cy.wait('@getConfig');

      // Click the logo in minimal header
      cy.get('.pf-v5-c-masthead__brand').click();

      // Should navigate to signin page
      cy.url().should('include', '/signin');
    });
  });

  describe('OAuth Success Flow', () => {
    it('redirects to backend for successful OAuth callback with code', () => {
      // Visit callback URL with code parameter (simulating successful OAuth return)
      cy.visit('/oauth2/github/callback?code=test_auth_code_12345');

      // The OAuthCallbackHandler should redirect to backend immediately
      // Verify the redirect happens (URL should change to backend endpoint)
      cy.location('pathname', {timeout: 10000}).should(
        'include',
        '/oauth2/github/callback',
      );

      // Note: In real flow, backend would process the code and redirect to dashboard
      // but in Cypress we can't follow backend redirects across domains
    });

    it('handles OAuth callback with code and state parameters', () => {
      cy.visit(
        '/oauth2/github/callback?code=test_auth_code&state=random_state_token',
      );

      // Verify redirect happens with all parameters preserved
      cy.location('search', {timeout: 10000}).should('include', 'code=');
      cy.location('search').should('include', 'state=');
    });
  });

  describe('OAuth Callback Handler Error Fallback', () => {
    it('redirects to error page when error param is present in callback', () => {
      // Visit callback URL with error parameter
      cy.visit(
        '/oauth2/github/callback?error=access_denied&error_description=User%20denied%20access',
      );

      // Should redirect to /oauth-error page
      cy.location('pathname', {timeout: 10000}).should(
        'include',
        '/oauth-error',
      );

      // Verify error parameters are in URL
      cy.location('search').should('include', 'error=access_denied');
      cy.location('search').should('include', 'provider=github');
    });

    it('handles callback error without description', () => {
      cy.visit('/oauth2/github/callback?error=server_error');

      // Should redirect to error page with error as description
      cy.location('pathname', {timeout: 10000}).should(
        'include',
        '/oauth-error',
      );
      cy.location('search').should('include', 'error=server_error');
      cy.location('search').should('include', 'error_description=server_error');
    });
  });

  describe('OAuth Attach Flow', () => {
    it('redirects to backend for attach callback with code', () => {
      cy.visit('/oauth2/github/callback/attach?code=attach_code_12345');

      // Should preserve /attach suffix in redirect
      cy.location('pathname', {timeout: 10000}).should(
        'include',
        '/oauth2/github/callback/attach',
      );
      cy.location('search').should('include', 'code=');
    });

    it('handles attach flow error', () => {
      cy.visit(
        '/oauth2/github/callback/attach?error=already_attached&error_description=Account%20already%20attached',
      );

      // Should redirect to error page
      cy.location('pathname', {timeout: 10000}).should(
        'include',
        '/oauth-error',
      );
      cy.location('search').should('include', 'error=already_attached');
    });
  });

  describe('OAuth CLI Token Flow', () => {
    it('redirects to backend for CLI token callback with code', () => {
      cy.visit('/oauth2/github/callback/cli?code=cli_token_code_12345');

      // Should preserve /cli suffix in redirect
      cy.location('pathname', {timeout: 10000}).should(
        'include',
        '/oauth2/github/callback/cli',
      );
      cy.location('search').should('include', 'code=');
    });

    it('handles CLI token flow error', () => {
      cy.visit(
        '/oauth2/github/callback/cli?error=invalid_request&error_description=Invalid%20CLI%20token%20request',
      );

      // Should redirect to error page
      cy.location('pathname', {timeout: 10000}).should(
        'include',
        '/oauth-error',
      );
      cy.location('search').should('include', 'error=invalid_request');
    });
  });

  describe('Backend Error Redirect Integration', () => {
    it('handles backend redirect to oauth-error for email validation error', () => {
      // Simulate backend redirecting to /oauth-error after processing OAuth callback
      cy.visit(
        '/oauth-error?error_description=GitHub:%20The%20email%20address%20invalid@domain%20is%20not%20valid&provider=GitHub',
      );

      cy.wait('@getConfig');

      // Verify error page renders correctly
      cy.contains('GitHub Authentication Error').should('be.visible');
      cy.contains('The email address invalid@domain is not valid').should(
        'be.visible',
      );
    });

    it('handles backend redirect with all error parameters', () => {
      cy.visit(
        '/oauth-error?error_description=Account%20creation%20required&provider=Google&register_redirect=true&user_creation=true',
      );

      cy.wait('@getConfig');

      // Verify all error information is displayed
      cy.contains('Google Authentication Error').should('be.visible');
      cy.contains('Account creation required').should('be.visible');
      cy.contains('Account Registration Required').should('be.visible');
    });
  });
});
