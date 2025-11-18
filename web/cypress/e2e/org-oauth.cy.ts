/// <reference types="cypress" />

describe('Organization OAuth Applications', () => {
  beforeEach(() => {
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  describe('OAuth Applications Tab Navigation', () => {
    it('should display OAuth Applications tab for organizations', () => {
      // Mock organization data
      cy.intercept('GET', '/api/v1/organization/testorg', {
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          is_admin: true,
          is_member: true,
        },
      }).as('getOrg');

      // Mock empty OAuth applications list
      cy.intercept('GET', '/api/v1/organization/testorg/applications*', {
        body: {applications: []},
      }).as('getOAuthApplications');

      cy.visit('/organization/testorg');
      cy.wait('@getOrg');

      // Check OAuth Applications tab exists
      cy.contains('OAuth Applications').should('exist');
      cy.contains('OAuth Applications').click();

      cy.wait('@getOAuthApplications');
      cy.url().should('include', '/organization/testorg?tab=OAuthApplications');
    });

    it('should show empty state when no OAuth applications exist', () => {
      cy.intercept('GET', '/api/v1/organization/testorg', {
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          is_admin: true,
          is_member: true,
        },
      }).as('getOrg');

      cy.intercept('GET', '/api/v1/organization/testorg/applications*', {
        body: {applications: []},
      }).as('getOAuthApplications');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      // Check empty state
      cy.contains(
        "This organization doesn't have any OAuth applications defined.",
      ).should('exist');
      cy.contains('Create new application').should('exist');
      cy.get('[data-testid="oauth-applications-table"]').should('not.exist');
    });

    it('should display OAuth applications list when applications exist', () => {
      cy.intercept('GET', '/api/v1/organization/testorg', {
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          is_admin: true,
          is_member: true,
        },
      }).as('getOrg');

      cy.intercept('GET', '/api/v1/organization/testorg/applications*', {
        body: {
          applications: [
            {
              name: 'test-app',
              client_id: 'TEST123',
              application_uri: 'https://example.com',
              description: 'Test OAuth application',
              avatar_email: 'test@example.com',
              client_secret: 'SECRET123',
            },
            {
              name: 'another-app',
              client_id: 'TEST456',
              application_uri: 'https://example2.com',
              description: 'Another test app',
              avatar_email: 'test2@example.com',
              client_secret: 'SECRET456',
            },
          ],
        },
      }).as('getOAuthApplications');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      // Check table exists and shows applications
      cy.get('[data-testid="oauth-applications-table"]').should('exist');
      cy.contains('test-app').should('exist');
      cy.contains('another-app').should('exist');
      cy.contains('https://example.com').should('exist');
      cy.contains('https://example2.com').should('exist');
    });
  });

  describe('Create new application', () => {
    beforeEach(() => {
      cy.intercept('GET', '/api/v1/organization/testorg', {
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          is_admin: true,
          is_member: true,
        },
      }).as('getOrg');

      cy.intercept('GET', '/api/v1/organization/testorg/applications*', {
        body: {applications: []},
      }).as('getOAuthApplications');
    });

    it('should open create modal from empty state', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      // Click create button from empty state
      cy.contains('Create new application').click();

      // Check modal opened
      cy.get('[data-testid="create-oauth-modal"]').should('exist');
      cy.contains('Create new application').should('exist');
    });

    it('should open create modal from toolbar', () => {
      // Mock some existing applications
      cy.intercept('GET', '/api/v1/organization/testorg/applications*', {
        body: {
          applications: [
            {
              name: 'existing-app',
              client_id: 'EXISTING123',
              application_uri: 'https://existing.com',
              description: 'Existing app',
              avatar_email: 'existing@example.com',
              client_secret: 'SECRET123',
            },
          ],
        },
      }).as('getOAuthApplicationsWithData');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplicationsWithData');

      // Click create button from toolbar
      cy.get('[data-testid="create-oauth-application-button"]').click();

      // Check modal opened
      cy.get('[data-testid="create-oauth-modal"]').should('exist');
    });

    it('should validate required fields in create form', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('Create new application').click();

      // Submit button should be disabled initially
      cy.get('[data-testid="create-oauth-submit"]').should('be.disabled');

      // Fill in application name (only required field)
      cy.get('[data-testid="application-name-input"]').type('test-app');

      // Submit button should be enabled after filling required field
      cy.get('[data-testid="create-oauth-submit"]').should('not.be.disabled');
    });

    it('should successfully create OAuth application', () => {
      cy.intercept('POST', '/api/v1/organization/testorg/applications', {
        statusCode: 201,
        body: {
          name: 'new-test-app',
          client_id: 'NEWTEST123',
          application_uri: 'https://newapp.com',
          description: 'New test app',
          avatar_email: 'new@example.com',
          client_secret: 'NEWSECRET123',
        },
      }).as('createOAuthApplication');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('Create new application').click();

      // Fill out form
      cy.get('[data-testid="application-name-input"]').type('new-test-app');
      cy.get('[data-testid="homepage-url-input"]').type('https://newapp.com');
      cy.get('[data-testid="description-input"]').type('New test app');
      cy.get('[data-testid="avatar-email-input"]').type('new@example.com');
      cy.get('[data-testid="redirect-url-input"]').type(
        'https://newapp.com/callback',
      );

      // Submit form
      cy.get('[data-testid="create-oauth-submit"]').click();

      cy.wait('@createOAuthApplication');
      cy.contains('Successfully created application:').should('exist');
      cy.get('[data-testid="create-oauth-modal"]').should('not.exist');
    });

    it('should handle create form errors', () => {
      cy.intercept('POST', '/api/v1/organization/testorg/applications', {
        statusCode: 400,
        body: {message: 'Application name already exists'},
      }).as('createOAuthApplicationError');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('Create new application').click();

      // Fill out form
      cy.get('[data-testid="application-name-input"]').type('duplicate-app');
      cy.get('[data-testid="homepage-url-input"]').type('https://example.com');

      // Submit form
      cy.get('[data-testid="create-oauth-submit"]').click();

      cy.wait('@createOAuthApplicationError');
      cy.contains('Error creating application').should('exist');
    });
  });

  describe('Manage OAuth Application', () => {
    beforeEach(() => {
      cy.intercept('GET', '/api/v1/organization/testorg', {
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          is_admin: true,
          is_member: true,
        },
      }).as('getOrg');

      cy.intercept('GET', '/api/v1/organization/testorg/applications*', {
        body: {
          applications: [
            {
              name: 'test-app',
              client_id: 'TEST123',
              application_uri: 'https://example.com',
              description: 'Test OAuth application',
              avatar_email: 'test@example.com',
              client_secret: 'SECRET123',
            },
          ],
        },
      }).as('getOAuthApplications');
    });

    it('should open manage drawer when clicking application name', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      // Click on application name
      cy.contains('test-app').click();

      // Check drawer opened
      cy.get('[data-testid="manage-oauth-drawer"]').should('exist');
      cy.contains('Manage OAuth Application: test-app').should('exist');
    });

    it('should open manage drawer from actions menu', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      // Click actions kebab
      cy.get('[data-testid="oauth-application-actions"]').first().click();
      cy.contains('Edit').click();

      // Check drawer opened
      cy.get('[data-testid="manage-oauth-drawer"]').should('exist');
    });

    it('should display all three tabs in manage drawer', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();

      // Check all tabs exist
      cy.contains('Settings').should('exist');
      cy.contains('OAuth Information').should('exist');
      cy.contains('Generate Token').should('exist');
    });
  });

  describe('Settings Tab', () => {
    beforeEach(() => {
      cy.intercept('GET', '/api/v1/organization/testorg', {
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          is_admin: true,
          is_member: true,
        },
      }).as('getOrg');

      cy.intercept('GET', '/api/v1/organization/testorg/applications*', {
        body: {
          applications: [
            {
              name: 'test-app',
              client_id: 'TEST123',
              application_uri: 'https://example.com',
              description: 'Test OAuth application',
              avatar_email: 'test@example.com',
              client_secret: 'SECRET123',
            },
          ],
        },
      }).as('getOAuthApplications');
    });

    it('should display current application settings', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();

      // Settings tab should be active by default
      cy.get('[data-testid="application-name-input"]').should(
        'have.value',
        'test-app',
      );
      cy.get('[data-testid="homepage-url-input"]').should(
        'have.value',
        'https://example.com',
      );
      cy.get('[data-testid="description-input"]').should(
        'have.value',
        'Test OAuth application',
      );
      cy.get('[data-testid="avatar-email-input"]').should(
        'have.value',
        'test@example.com',
      );
    });

    it('should update application settings', () => {
      cy.intercept('PUT', '/api/v1/organization/testorg/applications/TEST123', {
        statusCode: 200,
        body: {
          name: 'updated-test-app',
          client_id: 'TEST123',
          application_uri: 'https://updated.com',
          description: 'Updated description',
          avatar_email: 'updated@example.com',
          client_secret: 'SECRET123',
        },
      }).as('updateOAuthApplication');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();

      // Update fields
      cy.get('[data-testid="application-name-input"]')
        .clear()
        .type('updated-test-app');
      cy.get('[data-testid="homepage-url-input"]')
        .clear()
        .type('https://updated.com');
      cy.get('[data-testid="description-input"]')
        .clear()
        .type('Updated description');

      // Submit update
      cy.get('[data-testid="update-application-button"]').click();

      cy.wait('@updateOAuthApplication');
      cy.contains('OAuth application updated successfully').should('exist');
    });

    it('should handle update errors', () => {
      cy.intercept('PUT', '/api/v1/organization/testorg/applications/TEST123', {
        statusCode: 400,
        body: {message: 'Invalid application URI'},
      }).as('updateOAuthApplicationError');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();

      // Update with invalid URL
      cy.get('[data-testid="homepage-url-input"]').clear().type('invalid-url');

      // Submit update
      cy.get('[data-testid="update-application-button"]').click();

      cy.wait('@updateOAuthApplicationError');
      cy.contains('Failed to update OAuth application').should('exist');
    });
  });

  describe('OAuth Information Tab', () => {
    beforeEach(() => {
      cy.intercept('GET', '/api/v1/organization/testorg', {
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          is_admin: true,
          is_member: true,
        },
      }).as('getOrg');

      cy.intercept('GET', '/api/v1/organization/testorg/applications*', {
        body: {
          applications: [
            {
              name: 'test-app',
              client_id: 'TEST123',
              application_uri: 'https://example.com',
              description: 'Test OAuth application',
              avatar_email: 'test@example.com',
              client_secret: 'SECRET123',
            },
          ],
        },
      }).as('getOAuthApplications');
    });

    it('should display client ID and client secret', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();

      // Click OAuth Information tab
      cy.contains('OAuth Information').click();

      // Check client ID is displayed with copy functionality
      cy.contains('Client ID:').should('exist');
      cy.get('[data-testid="client-id-copy"]').should('exist');

      // Check client secret is displayed
      cy.contains('Client Secret:').should('exist');
      cy.contains('SECRET123').should('exist');
    });

    it('should reset client secret with confirmation', () => {
      cy.intercept(
        'POST',
        '/api/v1/organization/testorg/applications/TEST123/resetclientsecret',
        {
          statusCode: 200,
          body: {
            name: 'test-app',
            client_id: 'TEST123',
            application_uri: 'https://example.com',
            description: 'Test OAuth application',
            avatar_email: 'test@example.com',
            client_secret: 'NEWSECRET456',
          },
        },
      ).as('resetClientSecret');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();
      cy.contains('OAuth Information').click();

      // Click reset button
      cy.get('[data-testid="reset-client-secret-button"]').click();

      // Confirm in modal
      cy.get('[data-testid="confirm-reset-secret"]').click();

      cy.wait('@resetClientSecret');
      cy.contains('Client secret reset successfully').should('exist');
    });

    it('should handle reset client secret errors', () => {
      cy.intercept(
        'POST',
        '/api/v1/organization/testorg/applications/TEST123/resetclientsecret',
        {
          statusCode: 500,
          body: {message: 'Failed to reset client secret'},
        },
      ).as('resetClientSecretError');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();
      cy.contains('OAuth Information').click();

      // Click reset button and confirm
      cy.get('[data-testid="reset-client-secret-button"]').click();
      cy.get('[data-testid="confirm-reset-secret"]').click();

      cy.wait('@resetClientSecretError');
      cy.contains('Failed to reset client secret').should('exist');
    });
  });

  describe('Generate Token Tab', () => {
    beforeEach(() => {
      cy.intercept('GET', '/api/v1/organization/testorg', {
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          is_admin: true,
          is_member: true,
        },
      }).as('getOrg');

      cy.intercept('GET', '/api/v1/organization/testorg/applications*', {
        body: {
          applications: [
            {
              name: 'test-app',
              client_id: 'TEST123',
              application_uri: 'https://example.com',
              description: 'Test OAuth application',
              avatar_email: 'test@example.com',
              client_secret: 'SECRET123',
            },
          ],
        },
      }).as('getOAuthApplications');

      cy.intercept('GET', '/api/v1/user/', {
        body: {
          username: 'testuser',
          email: 'testuser@example.com',
        },
      }).as('getCurrentUser');

      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.config.LOCAL_OAUTH_HANDLER = '/oauth/localapp';
          res.body.config.PREFERRED_URL_SCHEME = 'http';
          res.body.config.SERVER_HOSTNAME = 'localhost:8080';
          return res;
        }),
      ).as('getConfig');
    });

    it('should display scope selection with OAuth scopes', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();

      // Click Generate Token tab
      cy.get('[data-testid="generate-token-tab"]').click();
      cy.wait('@getCurrentUser');
      cy.wait('@getConfig');

      // Check OAuth scopes are displayed
      cy.contains('Read User Information').should('exist');
      cy.contains('Administer Organization').should('exist');
      cy.contains('Create Repositories').should('exist');

      // Check current user is displayed
      cy.contains('testuser').should('exist');
    });

    it('should enable generate token button when scopes are selected', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();
      cy.get('[data-testid="generate-token-tab"]').click();
      cy.wait('@getCurrentUser');
      cy.wait('@getConfig');

      // Initially button should be disabled
      cy.get('[data-testid="generate-token-button"]').should('be.disabled');

      // Select a scope
      cy.get('[data-testid="scope-repo:read"]').check();

      // Button should now be enabled
      cy.get('[data-testid="generate-token-button"]').should('not.be.disabled');
    });

    it('should open OAuth authorization in popup window when generating token', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();
      cy.get('[data-testid="generate-token-tab"]').click();
      cy.wait('@getCurrentUser');
      cy.wait('@getConfig');

      // Select scopes
      cy.get('[data-testid="scope-repo:read"]').check();
      cy.get('[data-testid="scope-repo:write"]').check();

      // Click generate token to open modal
      cy.get('[data-testid="generate-token-button"]').click();

      // Modal should appear
      cy.get('[role="dialog"]').should('be.visible');
      cy.contains('Authorize Application').should('be.visible');

      // Capture form data during submission
      const capturedFormData: Record<string, string> = {};
      let capturedFormAction = '';
      let capturedFormMethod = '';
      let capturedFormTarget = '';

      cy.window().then((win) => {
        const submitStub = cy.stub(win.HTMLFormElement.prototype, 'submit');
        submitStub.callsFake(function () {
          // Capture form properties
          capturedFormAction = this.action;
          capturedFormMethod = this.method;
          capturedFormTarget = this.target;

          // Capture form data
          const inputs = this.querySelectorAll('input[type="hidden"]');
          inputs.forEach((input) => {
            const inputElement = input as HTMLInputElement;
            capturedFormData[inputElement.name] = inputElement.value;
          });
        });
        submitStub.as('formSubmit');
      });

      // Click authorize in modal
      cy.get('[role="dialog"]').contains('Authorize Application').click();

      // Verify the form was created and submitted with correct data
      cy.get('@formSubmit')
        .should('have.been.called')
        .then(() => {
          // Check form properties
          expect(capturedFormAction).to.include('/oauth/authorizeapp');
          expect(capturedFormMethod.toLowerCase()).to.equal('post');
          expect(capturedFormTarget).to.equal('oauth_authorization');

          // Check form data
          expect(capturedFormData.client_id).to.exist;
          expect(capturedFormData.scope).to.contain('repo:read repo:write');
          expect(capturedFormData.response_type).to.equal('token');
        });
    });

    it('should display token in React modal after generation (not redirect to Angular)', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();
      cy.get('[data-testid="generate-token-tab"]').click();
      cy.wait('@getCurrentUser');
      cy.wait('@getConfig');

      // Select scopes
      cy.get('[data-testid="scope-repo:read"]').check();

      // Click generate token to open modal
      cy.get('[data-testid="generate-token-button"]').click();

      // Stub window.open and postMessage to simulate OAuth flow
      cy.window().then((win) => {
        // Stub window.open to return a fake popup
        const fakePopup = {
          closed: false,
          close: cy.stub(),
        };
        cy.stub(win, 'open').returns(fakePopup);

        // Stub form submit to simulate OAuth callback
        const submitStub = cy.stub(win.HTMLFormElement.prototype, 'submit');
        submitStub.callsFake(function () {
          // Simulate OAuth callback by posting message
          setTimeout(() => {
            win.postMessage(
              {
                type: 'OAUTH_TOKEN_GENERATED',
                token: 'test-access-token-123456',
                scope: 'repo:read',
                state: null,
              },
              win.location.origin,
            );
          }, 100);
        });
      });

      // Click authorize in modal
      cy.get('[role="dialog"]').contains('Authorize Application').click();

      // CRITICAL: Verify token modal appears in React UI
      cy.contains('Access Token Generated', {timeout: 5000}).should('exist');
      cy.contains('Your access token has been successfully generated').should(
        'exist',
      );

      // Verify token is displayed in the ClipboardCopy input
      cy.get('.pf-v5-c-clipboard-copy input').should(
        'have.value',
        'test-access-token-123456',
      );

      // Verify user is still in React UI (no redirect to Angular)
      cy.url().should('include', 'localhost');
      cy.url().should('not.include', '/oauth/localapp');
      cy.url().should('include', '/organization/testorg');
    });

    it('should handle popup blocked scenario gracefully', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();
      cy.get('[data-testid="generate-token-tab"]').click();
      cy.wait('@getCurrentUser');
      cy.wait('@getConfig');

      // Select scopes
      cy.get('[data-testid="scope-repo:read"]').check();

      // Click generate token to open modal
      cy.get('[data-testid="generate-token-button"]').click();

      // Stub window.open to return null (popup blocked) BEFORE clicking authorize
      cy.window().then((win) => {
        cy.stub(win, 'open').returns(null);
      });

      // Click authorize in modal
      cy.get('[role="dialog"]').contains('Authorize Application').click();

      // Verify PatternFly warning alert appears (not browser alert)
      cy.contains(
        'Popup was blocked by your browser. Please allow popups for this site and try again.',
      ).should('exist');
    });

    it('should handle user assignment functionality', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();
      cy.get('[data-testid="generate-token-tab"]').click();
      cy.wait('@getCurrentUser');
      cy.wait('@getConfig');

      // Click assign another user
      cy.get('[data-testid="assign-user-button"]').click();

      // Check UI changes for user assignment
      cy.get('#entity-search-input').should('exist');
      cy.get('[data-testid="cancel-assign-button"]').should('exist');

      // Enter custom user
      cy.get('#entity-search-input').type('customuser');

      // Button text should change
      cy.get('[data-testid="generate-token-button"]').should(
        'contain.text',
        'Assign token',
      );
    });

    it('should assign token with correct parameter placement (query string)', () => {
      // Mock configuration with ASSIGN_OAUTH_TOKEN feature
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.features = {
            ...res.body.features,
            ASSIGN_OAUTH_TOKEN: true,
          };
          res.body.config.LOCAL_OAUTH_HANDLER = '/oauth/localapp';
          res.body.config.PREFERRED_URL_SCHEME = 'http';
          res.body.config.SERVER_HOSTNAME = 'localhost:8080';
          return res;
        }),
      ).as('getConfig');

      // Mock the assignuser OAuth endpoint with success response
      cy.intercept('POST', '/oauth/authorize/assignuser*', {
        statusCode: 200,
        body: {
          message: 'Token assigned successfully',
        },
      }).as('assignToken');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      cy.contains('test-app').click();
      cy.get('[data-testid="generate-token-tab"]').click();
      cy.wait('@getCurrentUser');
      cy.wait('@getConfig');

      // Click assign another user
      cy.get('[data-testid="assign-user-button"]').click();

      // Search for user (user2 exists in seed data)
      cy.get('#entity-search-input').type('user2');

      // Select user from results
      cy.contains('user2').click();

      // Select scopes
      cy.get('[data-testid="scope-repo:read"]').check();
      cy.get('[data-testid="scope-repo:write"]').check();

      // Click assign token button
      cy.get('[data-testid="generate-token-button"]').click();

      // Authorization modal should appear
      cy.get('[role="dialog"]').should('be.visible');

      // Click assign token button in modal to trigger fetch request
      cy.get('[role="dialog"]').contains('Assign token').click();

      // Wait for the assign token request and verify it was called
      cy.wait('@assignToken').then((interception) => {
        // Verify query parameters are present in URL
        expect(interception.request.url).to.include('username=user2');
        expect(interception.request.url).to.include('client_id=TEST123');
        expect(interception.request.url).to.match(/scope=repo(%3A|:)read/);
        expect(interception.request.url).to.include('redirect_uri=');
        expect(interception.request.url).to.include('response_type=token');
        expect(interception.request.url).to.include('format=json');
      });

      // Verify success alert appears (PatternFly alert)
      cy.contains('Token assigned successfully').should('exist');

      // Verify modal is closed
      cy.get('[role="dialog"]').should('not.exist');

      // Verify form is reset (user selection cleared)
      cy.get('[data-testid="cancel-assign-button"]').should('not.exist');
      cy.get('[data-testid="assign-user-button"]').should('exist');
    });
  });

  describe('Delete OAuth Application', () => {
    beforeEach(() => {
      cy.intercept('GET', '/api/v1/organization/testorg', {
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          is_admin: true,
          is_member: true,
        },
      }).as('getOrg');

      cy.intercept('GET', '/api/v1/organization/testorg/applications*', {
        body: {
          applications: [
            {
              name: 'test-app',
              client_id: 'TEST123',
              application_uri: 'https://example.com',
              description: 'Test OAuth application',
              avatar_email: 'test@example.com',
              client_secret: 'SECRET123',
            },
          ],
        },
      }).as('getOAuthApplications');
    });

    it('should delete OAuth application with confirmation', () => {
      cy.intercept(
        'DELETE',
        '/api/v1/organization/testorg/applications/TEST123',
        {
          statusCode: 204,
        },
      ).as('deleteOAuthApplication');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      // Click actions kebab
      cy.get('[data-testid="oauth-application-actions"]').first().click();
      cy.contains('Delete').click();

      // Confirm deletion
      cy.get('[data-testid="test-app-del-btn"]').click();

      cy.wait('@deleteOAuthApplication');
      cy.contains('Successfully deleted oauth application').should('exist');
    });

    it('should handle delete errors', () => {
      cy.intercept(
        'DELETE',
        '/api/v1/organization/testorg/applications/TEST123',
        {
          statusCode: 500,
          body: {message: 'Failed to delete application'},
        },
      ).as('deleteOAuthApplicationError');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      // Click actions kebab and delete
      cy.get('[data-testid="oauth-application-actions"]').first().click();
      cy.contains('Delete').click();
      cy.get('[data-testid="test-app-del-btn"]').click();

      cy.wait('@deleteOAuthApplicationError');
      cy.contains('Error deleting oauth application').should('exist');
    });
  });

  describe('Bulk Operations', () => {
    beforeEach(() => {
      cy.intercept('GET', '/api/v1/organization/testorg', {
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          is_admin: true,
          is_member: true,
        },
      }).as('getOrg');

      cy.intercept('GET', '/api/v1/organization/testorg/applications*', {
        body: {
          applications: [
            {
              name: 'test-app-1',
              client_id: 'TEST123',
              application_uri: 'https://example1.com',
              description: 'Test OAuth application 1',
              avatar_email: 'test1@example.com',
              client_secret: 'SECRET123',
            },
            {
              name: 'test-app-2',
              client_id: 'TEST456',
              application_uri: 'https://example2.com',
              description: 'Test OAuth application 2',
              avatar_email: 'test2@example.com',
              client_secret: 'SECRET456',
            },
          ],
        },
      }).as('getOAuthApplications');
    });

    it('should select multiple applications for bulk delete', () => {
      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      // Ensure we're on the OAuth Applications tab
      cy.contains('OAuth Applications').click();

      // Select multiple applications
      cy.get(
        'tbody tr:first-child td:first-child input[type="checkbox"]',
      ).check({force: true});
      cy.get(
        'tbody tr:nth-child(2) td:first-child input[type="checkbox"]',
      ).check({force: true});

      // Bulk delete button should be enabled
      cy.get('[data-testid="default-perm-bulk-delete-icon"]').should(
        'not.be.disabled',
      );
    });

    // passes locally, fails in CI due to timing issues
    it.skip('should perform bulk delete with confirmation', () => {
      // Mock bulk delete endpoint
      cy.intercept(
        'DELETE',
        '/api/v1/organization/testorg/applications/TEST123',
        {
          statusCode: 204,
        },
      ).as('deleteApp1');

      cy.intercept(
        'DELETE',
        '/api/v1/organization/testorg/applications/TEST456',
        {
          statusCode: 204,
        },
      ).as('deleteApp2');

      cy.visit('/organization/testorg?tab=OAuthApplications');
      cy.wait('@getOrg');
      cy.wait('@getOAuthApplications');

      // Ensure we're on the OAuth Applications tab and wait for content to load
      cy.contains('OAuth Applications').click();

      // Wait for the OAuth Applications tab content to be visible
      cy.get('[data-testid="oauth-applications-table"], tbody tr', {
        timeout: 10000,
      }).should('be.visible');

      // Select applications with explicit waits
      cy.get('tbody tr:first-child td:first-child input[type="checkbox"]')
        .should('be.visible')
        .check({force: true})
        .should('be.checked');

      cy.get('tbody tr:nth-child(2) td:first-child input[type="checkbox"]')
        .should('be.visible')
        .check({force: true})
        .should('be.checked');

      // Wait for UI state to update after selection
      cy.wait(500);

      // Wait for bulk delete button to be enabled (now that we're on the right tab)
      cy.get('[data-testid="default-perm-bulk-delete-icon"]')
        .should('be.visible')
        .should('not.be.disabled')
        .first()
        .click({force: true});

      // Type confirmation and confirm bulk delete
      cy.get('[data-testid="bulk-delete-confirmation-input"]').type('confirm', {
        force: true,
      });
      cy.get('[data-testid="bulk-delete-confirm-btn"]').click({force: true});

      cy.wait('@deleteApp1');
      cy.wait('@deleteApp2');
      cy.contains('Successfully deleted OAuth applications').should('exist');
    });
  });

  describe('Permissions', () => {
    it('should hide OAuth Applications tab for non-admin users', () => {
      cy.intercept('GET', '/api/v1/organization/testorg', {
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          is_admin: false,
          is_member: true,
        },
      }).as('getOrgNonAdmin');

      cy.visit('/organization/testorg');
      cy.wait('@getOrgNonAdmin');

      // OAuth Applications tab should not exist for non-admin users
      cy.contains('OAuth Applications').should('not.exist');
    });

    it('should show OAuth Applications tab for admin users', () => {
      cy.intercept('GET', '/api/v1/organization/testorg', {
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          is_admin: true,
          is_member: true,
        },
      }).as('getOrgAdmin');

      cy.intercept('GET', '/api/v1/organization/testorg/applications*', {
        body: {applications: []},
      }).as('getOAuthApplications');

      cy.visit('/organization/testorg');
      cy.wait('@getOrgAdmin');

      // OAuth Applications tab should exist for admin users
      cy.contains('OAuth Applications').should('exist');
    });
  });

  describe('User External Logins - Authorize Application', () => {
    it('should authorize assigned application from user external logins tab', () => {
      // Mock config with ASSIGN_OAUTH_TOKEN feature enabled
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.features = {
            ...res.body.features,
            ASSIGN_OAUTH_TOKEN: true,
          };
          res.body.config.LOCAL_OAUTH_HANDLER = '/oauth/localapp';
          res.body.config.PREFERRED_URL_SCHEME = 'http';
          res.body.config.SERVER_HOSTNAME = 'localhost:8080';
          return res;
        }),
      ).as('getConfig');

      // Mock user1's already authorized applications (empty for this test)
      cy.intercept('GET', '/api/v1/user/authorizations', {
        body: {
          authorizations: [],
        },
      }).as('getAuthorizedApps');

      // Mock user1's ASSIGNED applications (apps waiting for authorization)
      cy.intercept('GET', '/api/v1/user/assignedauthorization', {
        body: {
          authorizations: [
            {
              application: {
                name: 'test-app',
                description: 'Test OAuth application',
                url: 'https://example.com',
                organization: {
                  name: 'testorg',
                  avatar: {
                    name: 'testorg',
                    hash: 'abc123',
                    command: [],
                    kind: 'user',
                  },
                },
                clientId: 'TEST123',
              },
              scopes: [
                {
                  scope: 'user:read',
                  description:
                    'This application will be able to read user information such as username and email address.',
                },
              ],
              uuid: 'assigned-uuid-123',
              responseType: 'token',
              redirectUri: 'http://localhost:8080/oauth/localapp',
            },
          ],
        },
      }).as('getAssignedApps');

      // Mock the /oauth/authorize endpoint to return authorization data
      cy.intercept('GET', '/oauth/authorize?*', {
        body: {
          application: {
            name: 'test-app',
            description: 'Test OAuth application',
            organization: {
              name: 'testorg',
            },
          },
          client_id: 'TEST123',
          redirect_uri: 'http://localhost:8080/oauth/localapp',
          scope: 'user:read',
          response_type: 'token',
          assignment_uuid: 'assigned-uuid-123',
          csrf_token_val: 'test-csrf-token',
          scopes: [
            {
              scope: 'user:read',
              title: 'Read User Information',
              description:
                'This application will be able to read user information such as username and email address.',
              icon: 'fa-user',
              dangerous: false,
            },
          ],
          has_dangerous_scopes: false,
        },
      }).as('getAuthorizationData');

      // Visit user1's external logins page (user1 is already logged in from beforeEach)
      cy.visit('/organization/user1?tab=Externallogins');
      cy.wait('@getConfig');
      cy.wait('@getAuthorizedApps');
      cy.wait('@getAssignedApps');

      // Find and click the "Authorize Application" button
      cy.contains('Authorize Application').should('exist').click();

      // Wait for authorization data to be fetched
      cy.wait('@getAuthorizationData');

      // Verify the authorization modal appears
      cy.get('[role="dialog"]').should('be.visible');
      cy.contains('test-app').should('be.visible');
      cy.contains('This application would like permission to:').should(
        'be.visible',
      );

      // Stub window.open and form submission to simulate OAuth flow
      cy.window().then((win) => {
        // Stub window.open to return a fake popup
        const fakePopup = {
          closed: false,
          close: cy.stub(),
        };
        cy.stub(win, 'open').returns(fakePopup);

        // Stub form submit to simulate OAuth callback
        const submitStub = cy.stub(win.HTMLFormElement.prototype, 'submit');
        submitStub.callsFake(function () {
          // Simulate successful OAuth callback by posting message
          setTimeout(() => {
            win.postMessage(
              {
                type: 'OAUTH_TOKEN_GENERATED',
                token: 'test-generated-token-456',
                scope: 'user:read',
                state: null,
              },
              win.location.origin,
            );
          }, 100);
        });
      });

      // Click "Authorize Application" button in the modal
      cy.get('[role="dialog"]').contains('Authorize Application').click();

      // Verify token display modal appears
      cy.contains('Access Token Generated', {timeout: 5000}).should('exist');
      cy.contains('Your access token has been successfully generated').should(
        'exist',
      );

      // Verify token is displayed in the ClipboardCopy input
      cy.get('.pf-v5-c-clipboard-copy input').should(
        'have.value',
        'test-generated-token-456',
      );

      // Verify user is still in the External Logins tab (no redirect)
      cy.url().should('include', '/organization/user1');
      cy.url().should('include', 'tab=Externallogins');
    });
  });
});
