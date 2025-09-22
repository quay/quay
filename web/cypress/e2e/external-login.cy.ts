/// <reference types="cypress" />

describe('External Login Authentication', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
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

  it('shows error message when external login fails', () => {
    cy.intercept('GET', '/config', {
      fixture: 'config-with-external-login.json',
    }).as('getConfig');

    cy.intercept('POST', '/api/v1/externallogin/github', {
      statusCode: 500,
      body: {
        error_message: 'External login service unavailable',
      },
    }).as('getAuthUrlError');

    cy.visit('/signin');
    cy.wait('@getConfig');

    // Click external login button
    cy.get('[data-testid="external-login-github"]').click();

    cy.wait('@getAuthUrlError');

    // Should display error message - check for the actual error text from implementation
    cy.get('body').should(
      'contain.text',
      'Could not load external login service information',
    );
  });

  it('displays message when no login options are available', () => {
    cy.intercept('GET', '/config', {
      fixture: 'config-no-login-options.json',
    }).as('getConfig');

    cy.visit('/signin');
    cy.wait('@getConfig');

    // Should display info message
    cy.get('[data-testid="no-login-options-alert"]').should('be.visible');
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

  describe('External Login Management Tab', () => {
    beforeEach(() => {
      cy.intercept('GET', '/config', {
        fixture: 'config-with-external-login.json',
      }).as('getConfig');

      // Mock user data with external logins
      cy.intercept('GET', '/api/v1/user/', {
        statusCode: 200,
        body: {
          username: 'testuser',
          anonymous: false,
          avatar: {hash: 'test'},
          can_create_repo: true,
          is_me: true,
          verified: true,
          email: 'test@example.com',
          logins: [
            {
              service: 'github',
              service_identifier: 'github_user_123',
              metadata: {
                service_username: 'testuser-github',
              },
            },
          ],
          invoice_email: false,
          invoice_email_address: '',
          preferred_namespace: false,
          tag_expiration_s: 1209600,
          prompts: [],
          super_user: false,
          company: '',
          family_name: '',
          given_name: '',
          location: '',
          is_free_account: true,
          has_password_set: true,
          organizations: [],
        },
      }).as('getUser');

      // Mock organization data
      cy.intercept('GET', '/api/v1/organization/testuser', {
        statusCode: 200,
        body: {
          name: 'testuser',
          is_org_admin: false,
          is_admin: false,
          is_member: true,
          can_create_repo: true,
          preferred_namespace: true,
          tag_expiration_s: 1209600,
          email: 'test@example.com',
        },
      }).as('getOrganization');
    });

    it('displays external login providers in user organization tab', () => {
      cy.visit('/organization/testuser?tab=Externallogins');
      cy.wait(['@getConfig', '@getUser', '@getOrganization']);

      // Should display external logins tab content
      cy.get('[data-testid="external-logins-tab"]').should('be.visible');

      // Should display providers table
      cy.get('[data-testid="external-logins-table"]').should('be.visible');

      // Should show GitHub as attached
      cy.get('[data-testid="external-logins-table"]').should(
        'contain.text',
        'GitHub',
      );
      cy.get('[data-testid="provider-status-github"]').should(
        'contain.text',
        'Attached to GitHub account',
      );
      cy.get('[data-testid="provider-status-github"]').should(
        'contain.text',
        'testuser-github',
      );

      // Should show Google as unattached
      cy.get('[data-testid="provider-status-google"]').should(
        'contain.text',
        'Not attached to Google',
      );
    });

    it('allows attaching external login provider', () => {
      cy.intercept('POST', '/api/v1/externallogin/google', {
        statusCode: 200,
        body: {
          auth_url:
            'https://accounts.google.com/oauth/authorize?client_id=test',
        },
      }).as('attachGoogle');

      cy.visit('/organization/testuser?tab=Externallogins');
      cy.wait(['@getConfig', '@getUser', '@getOrganization']);

      // Click attach button for Google (should be a link button)
      cy.get('[data-testid="attach-google"]').click();

      cy.wait('@attachGoogle').then((interception) => {
        expect(interception.request.body).to.deep.equal({
          kind: 'attach',
        });
      });

      // Should store redirect URL in localStorage before redirect happens
      cy.window()
        .its('localStorage')
        .invoke('getItem', 'quay.redirectAfterLoad')
        .should('exist');
    });

    it('allows detaching external login provider', () => {
      cy.intercept('POST', '/api/v1/detachexternal/github', {
        statusCode: 200,
        body: {
          success: true,
        },
      }).as('detachGithub');

      cy.visit('/organization/testuser?tab=Externallogins');
      cy.wait(['@getConfig', '@getUser', '@getOrganization']);

      // Click detach button for GitHub
      cy.get('[data-testid="detach-github"]').click();

      cy.wait('@detachGithub');

      // Verify the detach request was made
      cy.get('@detachGithub').should('have.been.called');
    });

    it('hides attach/detach column when DIRECT_LOGIN is disabled', () => {
      cy.intercept('GET', '/config', {
        fixture: 'config-external-only.json',
      }).as('getConfigNoDirectLogin');

      cy.visit('/organization/testuser?tab=Externallogins');
      cy.wait(['@getConfigNoDirectLogin', '@getUser', '@getOrganization']);

      // Should not display attach/detach column
      cy.get('[data-testid="external-logins-table"] th').should(
        'have.length',
        2,
      );
      cy.get('[data-testid="external-logins-table"] th').should(
        'not.contain.text',
        'Attach/Detach',
      );
    });

    it('shows info message when no external providers configured', () => {
      cy.intercept('GET', '/config', {
        fixture: 'config-no-external-providers.json',
      }).as('getConfigNoProviders');

      cy.visit('/organization/testuser?tab=Externallogins');
      cy.wait(['@getConfigNoProviders', '@getUser', '@getOrganization']);

      // Should display info alert
      cy.get('[data-testid="no-external-providers-alert"]').should(
        'be.visible',
      );
      cy.get('[data-testid="no-external-providers-alert"]').should(
        'contain.text',
        'No external login providers configured',
      );
    });
  });
});
