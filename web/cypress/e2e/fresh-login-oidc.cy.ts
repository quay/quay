/// <reference types="cypress" />

describe('Fresh Login with OIDC Authentication - Superuser', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');

    // Mock CSRF token
    cy.intercept('GET', '/csrf_token', {
      body: {csrf_token: 'test-token'},
    }).as('getCsrfToken');
  });

  describe('OIDC Authentication Type', () => {
    beforeEach(() => {
      // Mock config with OIDC authentication
      cy.intercept('GET', '/config', {
        body: {
          features: {
            DIRECT_LOGIN: false,
            SUPER_USERS: true,
          },
          config: {
            AUTHENTICATION_TYPE: 'OIDC',
          },
          external_login: [
            {
              id: 'oidc',
              title: 'Azure AD',
              icon: '/static/img/azure.png',
            },
          ],
        },
      }).as('getConfigOIDC');
    });

    it('should redirect to signin when fresh_login_required error occurs on superuser endpoint', () => {
      // Mock successful initial authentication
      cy.intercept('GET', '/api/v1/user/', {
        statusCode: 200,
        body: {
          anonymous: false,
          username: 'oidc_user',
          email: 'oidc_user@example.com',
          verified: true,
          prompts: [],
          organizations: [],
          super_user: true,
          logins: [
            {
              service: 'oidc',
              service_identifier: 'oidc_user@example.com',
            },
          ],
        },
      }).as('getUser');

      // Visit superuser usage logs page
      cy.visit('/superuser/usagelogs');
      cy.wait('@getConfigOIDC');
      cy.wait('@getUser');

      // Mock the superuser API call that will return fresh_login_required error
      cy.intercept('GET', '/api/v1/superuserlogs**', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_type: 'fresh_login_required',
          detail: 'The action requires a fresh login to succeed.',
        },
      }).as('freshLoginRequired');

      // Wait for the fresh login error
      cy.wait('@freshLoginRequired');

      // Should redirect to signin page with redirect_url parameter
      cy.url().should('include', '/signin?redirect_url=');
      cy.url().should('include', 'superuser%2Fusagelogs');
    });

    it('should NOT show password modal for OIDC users on superuser pages', () => {
      cy.intercept('GET', '/api/v1/user/', {
        statusCode: 200,
        body: {
          anonymous: false,
          username: 'oidc_user',
          email: 'oidc_user@example.com',
          verified: true,
          prompts: [],
          organizations: [],
          super_user: true,
          logins: [
            {
              service: 'oidc',
              service_identifier: 'oidc_user@example.com',
            },
          ],
        },
      }).as('getUser');

      cy.visit('/superuser/usagelogs');
      cy.wait('@getConfigOIDC');
      cy.wait('@getUser');

      // Mock fresh_login_required error from superuser endpoint
      cy.intercept('GET', '/api/v1/superuserlogs**', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_type: 'fresh_login_required',
          detail: 'The action requires a fresh login to succeed.',
        },
      }).as('freshLoginRequired');

      cy.wait('@freshLoginRequired');

      // Password modal should NOT appear
      cy.contains('Please Verify').should('not.exist');
      cy.contains('Current Password').should('not.exist');

      // Should redirect to signin instead
      cy.url().should('include', '/signin');
    });

    it('should preserve query parameters in redirect URL for superuser pages', () => {
      cy.intercept('GET', '/api/v1/user/', {
        statusCode: 200,
        body: {
          anonymous: false,
          username: 'oidc_user',
          email: 'oidc_user@example.com',
          verified: true,
          prompts: [],
          organizations: [],
          super_user: true,
          logins: [
            {
              service: 'oidc',
              service_identifier: 'oidc_user@example.com',
            },
          ],
        },
      }).as('getUser');

      // Visit superuser page with query parameters
      cy.visit('/superuser/usagelogs?starttime=01/01/2025&endtime=01/31/2025');
      cy.wait('@getConfigOIDC');
      cy.wait('@getUser');

      // Mock fresh_login_required error from superuser endpoint
      cy.intercept('GET', '/api/v1/superuserlogs**', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_type: 'fresh_login_required',
          detail: 'The action requires a fresh login to succeed.',
        },
      }).as('freshLoginRequired');

      cy.wait('@freshLoginRequired');

      // Should encode the entire URL including query parameters
      cy.url().should('include', '/signin?redirect_url=');
      cy.url().should('include', 'superuser%2Fusagelogs');
      cy.url().should('include', 'starttime');
      cy.url().should('include', 'endtime');
    });
  });

  describe('Database Authentication Type', () => {
    beforeEach(() => {
      // Mock config with Database authentication
      cy.intercept('GET', '/config', {
        body: {
          features: {
            DIRECT_LOGIN: true,
            SUPER_USERS: true,
          },
          config: {
            AUTHENTICATION_TYPE: 'Database',
          },
          external_login: [],
        },
      }).as('getConfigDatabase');
    });

    it('should show password modal for Database users on superuser pages', () => {
      cy.intercept('GET', '/api/v1/user/', {
        statusCode: 200,
        body: {
          anonymous: false,
          username: 'user1',
          email: 'user1@example.com',
          verified: true,
          prompts: [],
          organizations: [],
          super_user: true,
          logins: [],
        },
      }).as('getUser');

      cy.visit('/superuser/usagelogs');
      cy.wait('@getConfigDatabase');
      cy.wait('@getUser');

      // Mock fresh_login_required error from superuser endpoint
      cy.intercept('GET', '/api/v1/superuserlogs**', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_type: 'fresh_login_required',
          detail: 'The action requires a fresh login to succeed.',
        },
      }).as('freshLoginRequired');

      cy.wait('@freshLoginRequired');

      // Password modal SHOULD appear for Database auth
      cy.contains('Please Verify').should('be.visible');
      cy.contains('Current Password').should('be.visible');
      cy.contains(
        'It has been more than a few minutes since you last logged in',
      ).should('be.visible');

      // Should NOT redirect to signin
      cy.url().should('include', '/superuser/usagelogs');
      cy.url().should('not.include', '/signin');
    });

    it('should verify password and retry superuser API call after successful verification', () => {
      cy.intercept('GET', '/api/v1/user/', {
        statusCode: 200,
        body: {
          anonymous: false,
          username: 'user1',
          email: 'user1@example.com',
          verified: true,
          prompts: [],
          organizations: [],
          super_user: true,
          logins: [],
        },
      }).as('getUser');

      cy.visit('/superuser/usagelogs');
      cy.wait('@getConfigDatabase');
      cy.wait('@getUser');

      // Mock fresh_login_required error from superuser endpoint
      cy.intercept('GET', '/api/v1/superuserlogs**', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_type: 'fresh_login_required',
          detail: 'The action requires a fresh login to succeed.',
        },
      }).as('freshLoginRequired');

      cy.wait('@freshLoginRequired');

      // Modal should appear
      cy.contains('Please Verify').should('be.visible');

      // Mock successful password verification
      cy.intercept('POST', '/api/v1/signin/verify', {
        statusCode: 200,
        body: {success: true},
      }).as('verifyPassword');

      // Mock successful retry of superuser API call
      cy.intercept('GET', '/api/v1/superuserlogs**', {
        statusCode: 200,
        body: {
          logs: [],
          aggregated: true,
        },
      }).as('getSuperuserLogsSuccess');

      // Enter password and verify
      cy.get('#fresh-password').type('password');
      cy.contains('button', 'Verify').click();

      // Should verify password
      cy.wait('@verifyPassword').then((interception) => {
        expect(interception.request.body).to.deep.equal({
          password: 'password',
        });
      });

      // Should retry the original superuser API request
      cy.wait('@getSuperuserLogsSuccess');

      // Modal should close
      cy.contains('Please Verify').should('not.exist');
    });

    it('should handle incorrect password on superuser page', () => {
      cy.intercept('GET', '/api/v1/user/', {
        statusCode: 200,
        body: {
          anonymous: false,
          username: 'user1',
          email: 'user1@example.com',
          verified: true,
          prompts: [],
          organizations: [],
          super_user: true,
          logins: [],
        },
      }).as('getUser');

      cy.visit('/superuser/usagelogs');
      cy.wait('@getConfigDatabase');
      cy.wait('@getUser');

      // Mock fresh_login_required error from superuser endpoint
      cy.intercept('GET', '/api/v1/superuserlogs**', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_type: 'fresh_login_required',
          detail: 'The action requires a fresh login to succeed.',
        },
      }).as('freshLoginRequired');

      cy.wait('@freshLoginRequired');

      // Mock failed password verification
      cy.intercept('POST', '/api/v1/signin/verify', {
        statusCode: 403,
        body: {
          message: 'Invalid verification credentials',
          invalidCredentials: true,
        },
      }).as('verifyPasswordFail');

      // Enter wrong password
      cy.get('#fresh-password').type('wrongpassword');
      cy.contains('button', 'Verify').click();

      cy.wait('@verifyPasswordFail');

      // Should show error alert
      cy.contains('Invalid verification credentials').should('be.visible');

      // Modal should close
      cy.contains('Please Verify').should('not.exist');
    });
  });

  describe('LDAP Authentication Type', () => {
    beforeEach(() => {
      // Mock config with LDAP authentication
      cy.intercept('GET', '/config', {
        body: {
          features: {
            DIRECT_LOGIN: true,
            SUPER_USERS: true,
          },
          config: {
            AUTHENTICATION_TYPE: 'LDAP',
          },
          external_login: [],
        },
      }).as('getConfigLDAP');
    });

    it('should show password modal for LDAP users on superuser pages', () => {
      cy.intercept('GET', '/api/v1/user/', {
        statusCode: 200,
        body: {
          anonymous: false,
          username: 'ldap_user',
          email: 'ldap_user@example.com',
          verified: true,
          prompts: [],
          organizations: [],
          super_user: true,
          logins: [
            {
              service: 'ldap',
              service_identifier: 'ldap_user',
            },
          ],
        },
      }).as('getUser');

      cy.visit('/superuser/usagelogs');
      cy.wait('@getConfigLDAP');
      cy.wait('@getUser');

      // Mock fresh_login_required error from superuser endpoint
      cy.intercept('GET', '/api/v1/superuserlogs**', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_type: 'fresh_login_required',
          detail: 'The action requires a fresh login to succeed.',
        },
      }).as('freshLoginRequired');

      cy.wait('@freshLoginRequired');

      // Password modal SHOULD appear for LDAP (not OIDC)
      cy.contains('Please Verify').should('be.visible');
      cy.contains('Current Password').should('be.visible');

      // Should NOT redirect to signin
      cy.url().should('include', '/superuser/usagelogs');
      cy.url().should('not.include', '/signin');
    });
  });
});
