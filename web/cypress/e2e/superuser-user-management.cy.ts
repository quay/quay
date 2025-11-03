/// <reference types="cypress" />

describe('Superuser User Management', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });

    // Mock config with all features enabled
    cy.fixture('config.json').then((config) => {
      config.features.SUPER_USERS = true;
      config.features.SUPERUSERS_FULL_ACCESS = true;
      config.features.QUOTA_MANAGEMENT = true;
      config.features.EDIT_QUOTA = true;
      config.features.MAILING = true;
      cy.intercept('GET', '/config', config).as('getConfig');
    });

    // Mock logged-in superuser
    cy.fixture('superuser.json').then((user) => {
      cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
    });

    // Mock organization and user endpoints
    cy.intercept('GET', '/api/v1/organization/*/robots*', {
      statusCode: 200,
      body: {robots: []},
    });

    cy.intercept('GET', '/api/v1/organization/*/members', {
      statusCode: 200,
      body: {members: []},
    }).as('getOrgMembers');

    cy.intercept('GET', '/api/v1/repository*', {
      statusCode: 200,
      body: {repositories: []},
    });
  });

  describe('Create User', () => {
    it('shows Create User button for superusers', () => {
      cy.visit('/organization');

      cy.get('[data-testid="create-user-button"]').should('be.visible');
      cy.get('[data-testid="create-user-button"]').should(
        'contain',
        'Create User',
      );
    });

    it('opens Create User modal when clicked', () => {
      cy.visit('/organization');

      cy.get('[data-testid="create-user-button"]').click();

      cy.get('[data-testid="create-user-modal"]').should('be.visible');
      cy.contains('Create New User').should('be.visible');
    });

    it('successfully creates user', () => {
      cy.intercept('POST', '/api/v1/superuser/users/', {
        statusCode: 201,
        body: {
          username: 'newuser',
          email: 'newuser@example.com',
          enabled: true,
        },
      }).as('createUser');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');
      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        fixture: 'superuser-organizations.json',
      }).as('getOrgs');

      cy.visit('/organization');
      cy.wait(['@getUsers', '@getOrgs']);

      cy.get('[data-testid="create-user-button"]').click();
      cy.get('[data-testid="username-input"]').type('newuser');
      cy.get('[data-testid="email-input"]').type('newuser@example.com');
      cy.get('[data-testid="password-input"]').type('password123');
      cy.get('[data-testid="confirm-password-input"]').type('password123');
      cy.get('[data-testid="create-user-submit"]').click();

      cy.wait('@createUser');
    });
  });

  describe('Access Control - Own Row (Superuser)', () => {
    beforeEach(() => {
      // Mock logged-in user as user1 (overrides the default superuser fixture)
      cy.intercept('GET', '/api/v1/user/', {
        body: {
          username: 'user1',
          email: 'user1@example.com',
          verified: true,
          super_user: true,
          avatar: {
            name: 'user1',
            hash: 'd2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2',
            color: '#ff0000',
            kind: 'user',
          },
          organizations: [],
          logins: [],
          invoice_email: false,
          tag_expiration_s: 1209600,
          preferred_namespace: false,
        },
      }).as('getUser1');

      // Mock users with superuser flags
      cy.intercept('GET', '/api/v1/superuser/users/', {
        body: {
          users: [
            {
              username: 'user1',
              email: 'user1@example.com',
              enabled: true,
              super_user: true,
            },
            {
              username: 'tom',
              email: 'tom@example.com',
              enabled: true,
              super_user: false,
            },
          ],
        },
      }).as('getUsers');

      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        body: {organizations: []},
      }).as('getOrgs');

      cy.intercept('GET', '/api/v1/superuser/users/*/quota*', {
        statusCode: 200,
        body: [],
      });
    });

    it('shows ONLY Configure Quota for logged-in superuser own row', () => {
      cy.visit('/organization');
      cy.wait(['@getConfig', '@getUser1', '@getUsers', '@getOrgs']);

      // Find user1 row and click kebab menu
      cy.contains('user1').should('be.visible');
      cy.get('[data-testid="user1-options-toggle"]').should('be.visible');
      cy.get('[data-testid="user1-options-toggle"]').click();

      // Should ONLY see Configure Quota
      cy.contains('Configure Quota').should('be.visible');

      // Should NOT see other management options
      cy.contains('Change E-mail Address').should('not.exist');
      cy.contains('Change Password').should('not.exist');
      cy.contains('Delete User').should('not.exist');
      cy.contains('Take Ownership').should('not.exist');
      cy.contains('Disable User').should('not.exist');
      cy.contains('Enable User').should('not.exist');
    });

    it('hides kebab menu for own row when quota features disabled', () => {
      // Disable quota features
      cy.fixture('config.json').then((config) => {
        config.features.SUPER_USERS = true;
        config.features.SUPERUSERS_FULL_ACCESS = true;
        config.features.QUOTA_MANAGEMENT = false;
        config.features.EDIT_QUOTA = false;
        cy.intercept('GET', '/config', config).as('getConfigNoQuota');
      });

      cy.visit('/organization');
      cy.wait(['@getConfigNoQuota', '@getUsers', '@getOrgs']);

      // user1 row should have NO kebab menu
      cy.get('[data-testid="user1-options-toggle"]').should('not.exist');
    });
  });

  describe('Access Control - Other Superusers', () => {
    it('hides kebab menu for other superuser rows', () => {
      // Mock users with multiple superusers
      cy.intercept('GET', '/api/v1/superuser/users/', {
        body: {
          users: [
            {
              username: 'user1',
              email: 'user1@example.com',
              enabled: true,
              super_user: true,
            },
            {
              username: 'admin',
              email: 'admin@example.com',
              enabled: true,
              super_user: true, // Another superuser
            },
            {
              username: 'tom',
              email: 'tom@example.com',
              enabled: true,
              super_user: false,
            },
          ],
        },
      }).as('getUsers');

      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        body: {organizations: []},
      }).as('getOrgs');

      cy.visit('/organization');
      cy.wait(['@getConfig', '@getUsers', '@getOrgs']);

      // Other superuser (admin) should NOT have a kebab menu
      cy.get('[data-testid="admin-options-toggle"]').should('not.exist');
    });
  });

  describe('Access Control - Regular Users', () => {
    beforeEach(() => {
      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        body: {organizations: []},
      }).as('getOrgs');
    });

    it('shows all management options for regular users', () => {
      cy.intercept('GET', '/api/v1/superuser/users/', {
        body: {
          users: [
            {
              username: 'user1',
              email: 'user1@example.com',
              enabled: true,
              super_user: true,
            },
            {
              username: 'tom',
              email: 'tom@example.com',
              enabled: true,
              super_user: false,
            },
          ],
        },
      }).as('getUsers');

      cy.visit('/organization');
      cy.wait(['@getConfig', '@getUsers', '@getOrgs']);

      // Click kebab menu for regular user (tom)
      cy.get('[data-testid="tom-options-toggle"]').click();

      // Should see all 6 options
      cy.contains('Change E-mail Address').should('be.visible');
      cy.contains('Change Password').should('be.visible');
      cy.contains('Disable User').should('be.visible');
      cy.contains('Delete User').should('be.visible');
      cy.contains('Take Ownership').should('be.visible');
      cy.contains('Configure Quota').should('be.visible');
    });

    it('shows "Enable User" for disabled users', () => {
      cy.intercept('GET', '/api/v1/superuser/users/', {
        body: {
          users: [
            {
              username: 'user1',
              email: 'user1@example.com',
              enabled: true,
              super_user: true,
            },
            {
              username: 'disableduser',
              email: 'disabled@example.com',
              enabled: false,
              super_user: false,
            },
          ],
        },
      }).as('getUsers');

      cy.visit('/organization');
      cy.wait(['@getConfig', '@getUsers', '@getOrgs']);

      // Click kebab menu
      cy.get('[data-testid="disableduser-options-toggle"]').click();

      // Should see "Enable User" instead of "Disable User"
      cy.contains('Enable User').should('be.visible');
      cy.contains('Disable User').should('not.exist');
    });
  });

  describe('Change Email', () => {
    it('successfully changes email', () => {
      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        body: {organizations: []},
      }).as('getOrgs');

      // Fix: Use the correct endpoint - PUT /api/v1/superuser/users/{username} with email in body
      cy.intercept('PUT', '/api/v1/superuser/users/tom', (req) => {
        if (req.body.email) {
          req.reply({statusCode: 200, body: {}});
        }
      }).as('updateEmail');

      cy.visit('/organization');
      cy.wait(['@getUsers', '@getOrgs']);

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Change E-mail Address').click();

      // Modal should open
      cy.contains('Change Email for tom').should('be.visible');

      // Enter new email and submit within modal context
      cy.get('[role="dialog"]').within(() => {
        cy.get('input[type="email"]').clear().type('newemail@example.com');
        cy.contains('button', 'Change Email').click();
      });

      cy.wait('@updateEmail');
    });
  });

  describe('Change Password', () => {
    it('successfully changes password', () => {
      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        body: {organizations: []},
      }).as('getOrgs');

      // Fix: Use the correct endpoint - PUT /api/v1/superuser/users/{username} with password in body
      cy.intercept('PUT', '/api/v1/superuser/users/tom', (req) => {
        if (req.body.password) {
          req.reply({statusCode: 200, body: {}});
        }
      }).as('updatePassword');

      cy.visit('/organization');
      cy.wait(['@getUsers', '@getOrgs']);

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Change Password').click();

      // Modal should open
      cy.contains('Change Password for tom').should('be.visible');

      // Enter new password and submit within modal context
      cy.get('[role="dialog"]').within(() => {
        cy.get('input[type="password"]').clear().type('newpassword123');
        cy.contains('button', 'Change Password').click();
      });

      cy.wait('@updatePassword');
    });
  });

  describe('Toggle User Status', () => {
    beforeEach(() => {
      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        body: {organizations: []},
      }).as('getOrgs');
    });

    it('disables enabled user', () => {
      cy.intercept('GET', '/api/v1/superuser/users/', {
        body: {
          users: [
            {
              username: 'user1',
              email: 'user1@example.com',
              enabled: true,
              super_user: true,
            },
            {
              username: 'tom',
              email: 'tom@example.com',
              enabled: true,
              super_user: false,
            },
          ],
        },
      }).as('getUsers');

      // Fix: Use the correct endpoint - PUT /api/v1/superuser/users/{username} with enabled in body
      cy.intercept('PUT', '/api/v1/superuser/users/tom', (req) => {
        if (Object.hasOwn(req.body, 'enabled')) {
          req.reply({statusCode: 200, body: {}});
        }
      }).as('toggleStatus');

      cy.visit('/organization');
      cy.wait(['@getUsers', '@getOrgs']);

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Disable User').click();

      // Confirm action within modal context
      cy.get('[role="dialog"]').within(() => {
        cy.contains('button', 'Disable User').click();
      });

      cy.wait('@toggleStatus');
    });

    it('enables disabled user', () => {
      cy.intercept('GET', '/api/v1/superuser/users/', {
        body: {
          users: [
            {
              username: 'user1',
              email: 'user1@example.com',
              enabled: true,
              super_user: true,
            },
            {
              username: 'disableduser',
              email: 'disabled@example.com',
              enabled: false,
              super_user: false,
            },
          ],
        },
      }).as('getUsers');

      // Fix: Use the correct endpoint - PUT /api/v1/superuser/users/{username} with enabled in body
      cy.intercept('PUT', '/api/v1/superuser/users/disableduser', (req) => {
        if (Object.hasOwn(req.body, 'enabled')) {
          req.reply({statusCode: 200, body: {}});
        }
      }).as('toggleStatus');

      cy.visit('/organization');
      cy.wait(['@getUsers', '@getOrgs']);

      cy.get('[data-testid="disableduser-options-toggle"]').click();
      cy.contains('Enable User').click();

      // Confirm action within modal context
      cy.get('[role="dialog"]').within(() => {
        cy.contains('button', 'Enable User').click();
      });

      cy.wait('@toggleStatus');
    });
  });

  describe('Delete User', () => {
    it('successfully deletes user', () => {
      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        body: {organizations: []},
      }).as('getOrgs');

      cy.intercept('DELETE', '/api/v1/superuser/users/tom', {
        statusCode: 204,
      }).as('deleteUser');

      cy.visit('/organization');
      cy.wait(['@getUsers', '@getOrgs']);

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Delete User').click();

      // Modal should show warning
      cy.contains('Delete User').should('be.visible');
      cy.contains('permanently deleted').should('be.visible');

      // Confirm deletion
      cy.contains('button', 'Delete User').click();

      cy.wait('@deleteUser');
    });
  });

  describe('Take Ownership', () => {
    it('takes ownership of user (converts to org)', () => {
      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        body: {organizations: []},
      }).as('getOrgs');

      // Fix: Use the correct endpoint - POST /api/v1/superuser/takeownership/{namespace}
      cy.intercept('POST', '/api/v1/superuser/takeownership/tom', {
        statusCode: 200,
        body: {},
      }).as('takeOwnership');

      cy.visit('/organization');
      cy.wait(['@getUsers', '@getOrgs']);

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Take Ownership').click();

      // Modal should show conversion warning
      cy.contains('Take Ownership').should('be.visible');
      cy.contains('convert the user namespace into an organization').should(
        'be.visible',
      );

      // Confirm action within modal context
      cy.get('[role="dialog"]').within(() => {
        cy.contains('button', 'Take Ownership').click();
      });

      cy.wait('@takeOwnership');
    });
  });

  describe('Configure Quota Option Visibility', () => {
    beforeEach(() => {
      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        body: {
          organizations: [
            {
              name: 'testorg',
              email: 'testorg@example.com',
            },
          ],
        },
      }).as('getOrgs');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        body: {
          users: [
            {
              username: 'user1',
              email: 'user1@example.com',
              enabled: true,
              super_user: true,
            },
            {
              username: 'tom',
              email: 'tom@example.com',
              enabled: true,
              super_user: false,
            },
          ],
        },
      }).as('getUsers');

      cy.intercept('GET', '/api/v1/organization/testorg*', {
        statusCode: 200,
        body: {name: 'testorg'},
      });
    });

    it('should NOT show Configure Quota option for regular users (only superusers can configure quota)', () => {
      cy.visit('/organization');
      cy.wait(['@getConfig', '@getUsers', '@getOrgs']);

      // Click kebab menu for regular user
      cy.get('[data-testid="tom-options-toggle"]').click();

      // Should NOT see Configure Quota in menu (only superusers can configure quota)
      cy.contains('Configure Quota').should('not.exist');
    });

    it('shows Configure Quota option for organizations when user is superuser', () => {
      cy.visit('/organization');
      cy.wait(['@getConfig', '@getUsers', '@getOrgs']);

      // Click kebab menu for organization
      cy.get('[data-testid="testorg-options-toggle"]').click();

      // Should see Configure Quota in menu (superusers can configure quota)
      cy.contains('Configure Quota').should('be.visible');
    });

    it('shows Configure Quota option for superuser viewing their own row', () => {
      // Mock logged-in user as user1 (superuser viewing own row)
      cy.intercept('GET', '/api/v1/user/', {
        body: {
          username: 'user1',
          email: 'user1@example.com',
          super_user: true,
          global_readonly_super_user: false,
        },
      }).as('getUser1');

      cy.visit('/organization');
      cy.wait(['@getConfig', '@getUser1', '@getUsers', '@getOrgs']);

      // Click kebab menu for superuser's own row
      cy.get('[data-testid="user1-options-toggle"]').click();

      // Should see Configure Quota in menu (superusers can configure quota for themselves)
      cy.contains('Configure Quota').should('be.visible');
    });
  });

  describe('Send Recovery Email', () => {
    beforeEach(() => {
      cy.intercept('GET', '/api/v1/superuser/users/', {
        body: {
          users: [
            {
              username: 'user1',
              email: 'user1@example.com',
              enabled: true,
              super_user: true,
            },
            {
              username: 'tom',
              email: 'tom@example.com',
              enabled: true,
              super_user: false,
            },
          ],
        },
      }).as('getUsers');

      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        body: {organizations: []},
      }).as('getOrgs');
    });

    it('shows Send Recovery E-mail option when MAILING feature enabled', () => {
      cy.visit('/organization');
      cy.wait(['@getUsers', '@getOrgs']);

      cy.get('[data-testid="tom-options-toggle"]').click();

      // Should see Send Recovery E-mail option
      cy.contains('Send Recovery E-mail').should('be.visible');
    });

    it('hides Send Recovery E-mail option when MAILING feature disabled', () => {
      // Disable MAILING feature
      cy.fixture('config.json').then((config) => {
        config.features.SUPER_USERS = true;
        config.features.SUPERUSERS_FULL_ACCESS = true;
        config.features.MAILING = false;
        cy.intercept('GET', '/config', config).as('getConfigNoMailing');
      });

      cy.visit('/organization');
      cy.wait(['@getConfigNoMailing', '@getUsers', '@getOrgs']);

      cy.get('[data-testid="tom-options-toggle"]').click();

      // Should NOT see Send Recovery E-mail option
      cy.contains('Send Recovery E-mail').should('not.exist');
    });

    it('successfully sends recovery email', () => {
      cy.intercept('POST', '/api/v1/superusers/users/tom/sendrecovery', {
        statusCode: 200,
        body: {email: 'tom@example.com'},
      }).as('sendRecoveryEmail');

      cy.visit('/organization');
      cy.wait(['@getUsers', '@getOrgs']);

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Send Recovery E-mail').click();

      // Modal should open
      cy.contains('Send Recovery Email').should('be.visible');
      cy.contains('Are you sure you want to send a recovery email').should(
        'be.visible',
      );

      // Send recovery email
      cy.get('[role="dialog"]').within(() => {
        cy.contains('button', 'Send Recovery Email').click();
      });

      cy.wait('@sendRecoveryEmail');

      // Success message should be shown
      cy.contains('A recovery email has been sent to tom@example.com').should(
        'be.visible',
      );
    });

    it('displays error when sending recovery email fails', () => {
      cy.intercept('POST', '/api/v1/superusers/users/tom/sendrecovery', {
        statusCode: 400,
        body: {
          error_message: 'Cannot send a recovery email for non-database auth',
        },
      }).as('sendRecoveryEmailError');

      cy.visit('/organization');
      cy.wait(['@getUsers', '@getOrgs']);

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Send Recovery E-mail').click();

      // Modal should open
      cy.contains('Send Recovery Email').should('be.visible');

      // Send recovery email
      cy.get('[role="dialog"]').within(() => {
        cy.contains('button', 'Send Recovery Email').click();
      });

      cy.wait('@sendRecoveryEmailError');

      // Error message should be shown
      cy.contains('Cannot send a recovery email for non-database auth').should(
        'be.visible',
      );
    });
  });

  describe('Access Control - Permissions', () => {
    it('hides Create User button for non-superusers', () => {
      // Mock regular user (non-superuser)
      cy.fixture('user.json').then((user) => {
        user.super_user = false;
        cy.intercept('GET', '/api/v1/user/', user).as('getUser');
      });

      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        body: {organizations: []},
      });

      cy.visit('/organization');
      cy.wait('@getUser');

      cy.get('[data-testid="create-user-button"]').should('not.exist');
    });

    it('hides all actions in read-only mode', () => {
      // Mock read-only superuser
      cy.fixture('config.json').then((config) => {
        config.features.SUPER_USERS = true;
        config.features.SUPERUSERS_FULL_ACCESS = false;
        cy.intercept('GET', '/config', config).as('getConfigReadOnly');
      });

      cy.fixture('superuser.json').then((user) => {
        user.global_readonly_super_user = true;
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUserReadOnly');
      });

      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        body: {organizations: []},
      });

      cy.visit('/organization');
      cy.wait(['@getConfigReadOnly', '@getSuperUserReadOnly']);

      // Should not show Create User button
      cy.get('[data-testid="create-user-button"]').should('not.exist');

      // Should not show any kebab menus
      cy.get('[data-testid$="-options-toggle"]').should('not.exist');
    });
  });
});
