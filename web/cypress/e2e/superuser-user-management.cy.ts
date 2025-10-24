/// <reference types="cypress" />

describe('Superuser User Management', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  describe('Create User Button', () => {
    it('should show Create User button for superusers', () => {
      cy.visit('/organization');

      // Verify Create User button exists
      cy.get('[data-testid="create-user-button"]').should('be.visible');
      cy.get('[data-testid="create-user-button"]').should(
        'contain',
        'Create User',
      );
    });

    it('should open Create User modal when clicked', () => {
      cy.visit('/organization');

      cy.get('[data-testid="create-user-button"]').click();

      // Verify modal is open
      cy.get('[data-testid="create-user-modal"]').should('be.visible');
      cy.contains('Create New User').should('be.visible');
    });
  });

  describe('Create User Modal', () => {
    beforeEach(() => {
      cy.visit('/organization');
      cy.get('[data-testid="create-user-button"]').click();
    });

    it('should have all required form fields', () => {
      cy.get('[data-testid="username-input"]').should('be.visible');
      cy.get('[data-testid="email-input"]').should('be.visible');
      cy.get('[data-testid="password-input"]').should('be.visible');
      cy.get('[data-testid="confirm-password-input"]').should('be.visible');
    });

    it('should validate username field', () => {
      // Try submitting with invalid username
      cy.get('[data-testid="username-input"]').type('A');
      cy.get('[data-testid="email-input"]').type('test@example.com');
      cy.get('[data-testid="password-input"]').type('password123');
      cy.get('[data-testid="confirm-password-input"]').type('password123');

      // Submit button should be disabled or show error
      cy.get('[data-testid="username-input"]').clear().type('a');
      cy.contains('Username must be at least 2 characters').should(
        'be.visible',
      );
    });

    it('should validate email field', () => {
      cy.get('[data-testid="username-input"]').type('testuser');
      cy.get('[data-testid="email-input"]').type('notanemail');
      cy.get('[data-testid="password-input"]').type('password123');
      cy.get('[data-testid="confirm-password-input"]').type('password123');

      // Should show email validation error
      cy.contains('Invalid email address').should('be.visible');
    });

    it('should validate password length', () => {
      cy.get('[data-testid="username-input"]').type('testuser');
      cy.get('[data-testid="email-input"]').type('test@example.com');
      cy.get('[data-testid="password-input"]').type('123');
      cy.get('[data-testid="confirm-password-input"]').type('123');

      cy.contains('Password must be at least 8 characters').should(
        'be.visible',
      );
    });

    it('should validate password confirmation matches', () => {
      cy.get('[data-testid="username-input"]').type('testuser');
      cy.get('[data-testid="email-input"]').type('test@example.com');
      cy.get('[data-testid="password-input"]').type('password123');
      cy.get('[data-testid="confirm-password-input"]').type('password456');

      cy.contains('Passwords do not match').should('be.visible');
    });

    it('should close modal when Cancel is clicked', () => {
      cy.get('[data-testid="create-user-cancel"]').click();
      cy.get('[data-testid="create-user-modal"]').should('not.exist');
    });

    it('should disable submit button when form is invalid', () => {
      cy.get('[data-testid="create-user-submit"]').should('be.disabled');
    });
  });

  describe('User Options Menu - Current User', () => {
    it('should NOT show options menu for currently logged-in user', () => {
      cy.visit('/organization');

      // Find the row for user1 (currently logged-in user)
      cy.contains('tr', 'user1').within(() => {
        // Should NOT have a settings button
        cy.get('[data-testid="user1-options-toggle"]').should('not.exist');
      });
    });
  });

  describe('User Options Menu - Other Users', () => {
    it('should show options menu for other users', () => {
      cy.visit('/organization');

      // Mock user data to ensure tom exists
      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.wait('@getUsers');

      // Find the row for tom (another user)
      cy.get('[data-testid="tom-options-toggle"]').should('be.visible');
    });

    it('should show all user management options for other users', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.wait('@getUsers');

      // Click options menu for tom
      cy.get('[data-testid="tom-options-toggle"]').click();

      // Verify all menu items are present
      cy.contains('Change E-mail Address').should('be.visible');
      cy.contains('Change Password').should('be.visible');
      cy.contains('Delete User').should('be.visible');
      cy.contains('Take Ownership').should('be.visible');

      // Should show either Enable or Disable based on user status
      cy.get('body').then(($body) => {
        const hasEnable = $body.text().includes('Enable User');
        const hasDisable = $body.text().includes('Disable User');
        expect(hasEnable || hasDisable).to.be.true;
      });
    });

    it('should show "Disable User" when user is enabled', () => {
      cy.visit('/organization');

      // Mock tom as enabled
      cy.intercept('GET', '/api/v1/superuser/users/', {
        body: {
          users: [
            {
              username: 'user1',
              email: 'user1@example.com',
              enabled: true,
            },
            {
              username: 'tom',
              email: 'tom@example.com',
              enabled: true, // Tom is enabled
            },
          ],
        },
      }).as('getUsers');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Disable User').should('be.visible');
    });

    it('should show "Enable User" when user is disabled', () => {
      cy.visit('/organization');

      // Mock tom as disabled
      cy.intercept('GET', '/api/v1/superuser/users/', {
        body: {
          users: [
            {
              username: 'user1',
              email: 'user1@example.com',
              enabled: true,
            },
            {
              username: 'tom',
              email: 'tom@example.com',
              enabled: false, // Tom is disabled
            },
          ],
        },
      }).as('getUsers');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Enable User').should('be.visible');
    });
  });

  describe('Change Email Modal', () => {
    it('should open Change Email modal', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Change E-mail Address').click();

      cy.contains('Change Email for tom').should('be.visible');
    });

    it('should validate email format', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Change E-mail Address').click();

      cy.get('#new-email').type('invalidemail');
      cy.contains('Change Email').click();

      cy.contains('Please enter a valid email address').should('be.visible');
    });

    it('should show success alert after changing email', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.intercept('PUT', '/api/v1/superuser/users/tom', {
        statusCode: 200,
        body: {},
      }).as('updateUser');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Change E-mail Address').click();

      cy.get('#new-email').type('newemail@example.com');
      cy.contains('button', 'Change Email').click();

      cy.wait('@updateUser');

      // Verify success alert appears
      cy.contains('Successfully changed email for tom').should('be.visible');
    });

    it('should show error alert when email change fails', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.intercept('PUT', '/api/v1/superuser/users/tom', {
        statusCode: 400,
        body: {error_message: 'Email already exists'},
      }).as('updateUserFail');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Change E-mail Address').click();

      cy.get('#new-email').type('duplicate@example.com');
      cy.contains('button', 'Change Email').click();

      cy.wait('@updateUserFail');

      // Verify error alert appears
      cy.contains('Failed to change email for tom').should('be.visible');
    });
  });

  describe('Change Password Modal', () => {
    it('should open Change Password modal', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Change Password').click();

      cy.contains('Change Password for tom').should('be.visible');
    });

    it('should require minimum 8 characters', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Change Password').click();

      cy.get('#new-password').type('123');
      cy.contains('Change Password').last().click();

      cy.contains('Password must be at least 8 characters').should(
        'be.visible',
      );
    });
  });

  describe('Delete User Modal', () => {
    it('should open Delete User modal with warning', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Delete User').click();

      cy.contains('Delete User').should('be.visible');
      cy.contains('permanently deleted').should('be.visible');
    });

    it('should have danger-styled delete button', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Delete User').click();

      // Verify delete button has danger variant
      cy.contains('button', 'Delete User').should('have.class', 'pf-m-danger');
    });
  });

  describe('Toggle User Status Modal', () => {
    it('should show appropriate warning for disabling user', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        body: {
          users: [
            {username: 'user1', email: 'user1@example.com', enabled: true},
            {username: 'tom', email: 'tom@example.com', enabled: true},
          ],
        },
      }).as('getUsers');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Disable User').click();

      cy.contains('Disable User').should('be.visible');
      cy.contains('prevent them from logging in').should('be.visible');
    });

    it('should show appropriate message for enabling user', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        body: {
          users: [
            {username: 'user1', email: 'user1@example.com', enabled: true},
            {username: 'tom', email: 'tom@example.com', enabled: false},
          ],
        },
      }).as('getUsers');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Enable User').click();

      cy.contains('Enable User').should('be.visible');
      cy.contains('allow them to log in').should('be.visible');
    });
  });

  describe('Take Ownership Modal - User', () => {
    it('should show warning about converting user to organization', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');

      cy.wait('@getUsers');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Take Ownership').click();

      cy.contains('Take Ownership').should('be.visible');
      cy.contains('convert the user namespace into an organization').should(
        'be.visible',
      );
      cy.contains('will no longer be able to login').should('be.visible');
    });
  });

  describe('Organization Options Menu', () => {
    it('should show organization-specific options', () => {
      cy.visit('/organization');

      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        fixture: 'superuser-organizations.json',
      }).as('getOrgs');

      cy.wait('@getOrgs');

      // Click options for an organization (not a user)
      cy.get('[data-testid="org-options-toggle"]').click();

      // Should show org-specific options
      cy.contains('Rename Organization').should('be.visible');
      cy.contains('Delete Organization').should('be.visible');
      cy.contains('Take Ownership').should('be.visible');

      // Should NOT show user-specific options
      cy.contains('Change E-mail Address').should('not.exist');
      cy.contains('Change Password').should('not.exist');
    });
  });

  describe('Access Control', () => {
    it('should hide Create User button for non-superusers', () => {
      // Mock regular user (non-superuser)
      cy.fixture('user.json').then((user) => {
        user.super_user = false;
        cy.intercept('GET', '/api/v1/user/', user).as('getUser');
      });

      cy.visit('/organization');
      cy.wait('@getUser');

      cy.get('[data-testid="create-user-button"]').should('not.exist');
    });

    it('should hide all action buttons in read-only mode', () => {
      // Mock read-only superuser
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = false;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        user.global_readonly_super_user = true;
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Should not show Create User button
      cy.get('[data-testid="create-user-button"]').should('not.exist');

      // Should not show any options menus
      cy.get('[data-testid$="-options-toggle"]').should('not.exist');
    });
  });

  describe('Success and Error Alerts', () => {
    beforeEach(() => {
      cy.visit('/organization');
      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getUsers');
      cy.wait('@getUsers');
    });

    it('should show success alert when user is deleted', () => {
      cy.intercept('DELETE', '/api/v1/superuser/users/tom', {
        statusCode: 204,
      }).as('deleteUser');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Delete User').click();
      cy.contains('button', 'Delete User').click();

      cy.wait('@deleteUser');
      cy.contains('Successfully deleted user tom').should('be.visible');
    });

    it('should show success alert when user password is changed', () => {
      cy.intercept('PUT', '/api/v1/superuser/users/tom', {
        statusCode: 200,
        body: {},
      }).as('updatePassword');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Change Password').click();
      cy.get('#new-password').type('newpassword123');
      cy.contains('button', 'Change Password').click();

      cy.wait('@updatePassword');
      cy.contains('Successfully changed password for tom').should('be.visible');
    });

    it('should show success alert when user status is toggled', () => {
      cy.intercept('PUT', '/api/v1/superuser/users/tom', {
        statusCode: 200,
        body: {},
      }).as('toggleStatus');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Disable User').click();
      cy.contains('button', 'Disable User').click();

      cy.wait('@toggleStatus');
      cy.contains('Successfully disabled user tom').should('be.visible');
    });

    it('should show success alert when user is created', () => {
      cy.intercept('POST', '/api/v1/superuser/users/', {
        statusCode: 200,
        body: {username: 'newuser', email: 'newuser@example.com', enabled: true},
      }).as('createUser');

      cy.get('[data-testid="create-user-button"]').click();
      cy.get('[data-testid="username-input"]').type('newuser');
      cy.get('[data-testid="email-input"]').type('newuser@example.com');
      cy.get('[data-testid="password-input"]').type('password123');
      cy.get('[data-testid="confirm-password-input"]').type('password123');
      cy.get('[data-testid="create-user-submit"]').click();

      cy.wait('@createUser');
      cy.contains('Successfully created user newuser').should('be.visible');
    });

    it('should show error alert when user creation fails', () => {
      cy.intercept('POST', '/api/v1/superuser/users/', {
        statusCode: 400,
        body: {error_message: 'Username already exists'},
      }).as('createUserFail');

      cy.get('[data-testid="create-user-button"]').click();
      cy.get('[data-testid="username-input"]').type('tom');
      cy.get('[data-testid="email-input"]').type('tom@example.com');
      cy.get('[data-testid="password-input"]').type('password123');
      cy.get('[data-testid="confirm-password-input"]').type('password123');
      cy.get('[data-testid="create-user-submit"]').click();

      cy.wait('@createUserFail');
      cy.contains('Failed to create user').should('be.visible');
      cy.contains('Username already exists').should('be.visible');
    });

    it('should show error alert when user deletion fails', () => {
      cy.intercept('DELETE', '/api/v1/superuser/users/tom', {
        statusCode: 500,
        body: {error_message: 'Internal server error'},
      }).as('deleteUserFail');

      cy.get('[data-testid="tom-options-toggle"]').click();
      cy.contains('Delete User').click();
      cy.contains('button', 'Delete User').click();

      cy.wait('@deleteUserFail');
      cy.contains('Failed to delete user tom').should('be.visible');
    });
  });
});
