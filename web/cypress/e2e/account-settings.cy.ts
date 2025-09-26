/// <reference types="cypress" />

import {humanizeTimeForExpiry, parseTimeDuration} from 'src/libs/utils';

describe('Account Settings Page', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.visit('/signin');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.intercept('GET', '/api/v1/plans/', {fixture: 'plans.json'}).as(
      'getPlans',
    );
  });

  it('General Settings', () => {
    cy.fixture('config.json').then((config) => {
      config.features.USER_METADATA = true;
      cy.intercept('GET', '/config', config).as('getConfigWithUserMetadata');
    });

    // Intercept user/organization API calls
    cy.intercept('GET', '/api/v1/user').as('getUser');
    cy.intercept('GET', '/api/v1/organization/user1').as('getOrg');

    cy.visit('/organization/user1?tab=Settings');
    cy.wait('@getConfigWithUserMetadata');

    // Wait for data to load
    cy.wait('@getUser');
    // Note: getOrg might 404 for user accounts, that's expected

    // Debug: Check if form exists at all
    cy.get('#form-form').should('exist');

    // Debug: Log all input elements and their IDs
    cy.get('input').then(($inputs) => {
      console.log('Found inputs:', $inputs.length);
      $inputs.each((i, input) => {
        console.log(
          `Input ${i}: id="${input.id}", name="${input.name}", type="${input.type}"`,
        );
      });
    });

    // Wait for the form to load
    cy.get('#org-settings-email').should('be.visible');

    // Type a bad e-mail
    cy.get('#org-settings-email').clear();
    cy.get('#org-settings-email').type('this is not a good e-mail');
    cy.contains('Please enter a valid email address');

    // Leave empty (email field is not required, so no error should appear)
    cy.get('#org-settings-email').clear();

    // Button should be disabled initially (since form is not dirty with valid changes)
    cy.get('#save-org-settings').should('be.disabled');

    // Type a good content
    cy.get('#org-settings-email').type('good-email@redhat.com');
    cy.get('#org-settings-fullname').type('Joe Smith');
    cy.get('#org-settings-location').type('Raleigh, NC');
    cy.get('#org-settings-company').type('Red Hat');
    cy.get('#save-org-settings').click();

    // refresh page and check if email is saved
    cy.reload();
    cy.get('#org-settings-email').should('have.value', 'good-email@redhat.com');
    cy.get('#org-settings-fullname').should('have.value', 'Joe Smith');
    cy.get('#org-settings-location').should('have.value', 'Raleigh, NC');
    cy.get('#org-settings-company').should('have.value', 'Red Hat');
  });

  it('Tag Expiration picker visibility', () => {
    cy.fixture('config.json').then((config) => {
      config.features.CHANGE_TAG_EXPIRATION = false;
      cy.intercept('GET', '/config', config).as('getConfigDisabled');
    });

    cy.visit('/organization/user1?tab=Settings');
    cy.wait('@getConfigDisabled');

    // Verify the FormGroup is not visible
    cy.get('[data-testid="tag-expiration-picker"]').should('not.exist');

    cy.fixture('config.json').then((config) => {
      config.features.CHANGE_TAG_EXPIRATION = true;
      cy.intercept('GET', '/config', config).as('getConfigEnabled');
    });

    cy.visit('/organization/user1?tab=Settings');
    cy.wait('@getConfigEnabled');

    // Wait for the General settings tab to be active (it should be default)
    cy.contains('General settings').should('be.visible');

    // Wait for the form to load
    cy.get('#org-settings-email').should('be.visible');

    // Scroll to and verify the FormGroup is visible
    cy.get('[data-testid="tag-expiration-picker"]')
      .scrollIntoView()
      .should('be.visible');
  });

  it('Tag expiration picker dropdown values', () => {
    // 1. Single fixture load at the beginning
    cy.fixture('config.json').then((config) => {
      config.features.CHANGE_TAG_EXPIRATION = true;
      cy.intercept('GET', '/config', config).as('getConfigEnabled');

      cy.intercept('GET', '/api/v1/user', (req) => {
        req.continue((res) => {
          res.body.tag_expiration_s = 60 * 60 * 24 * 80; // 80 days in seconds
        });
      }).as('getUser');

      cy.visit('/organization/user1?tab=Settings');
      cy.wait('@getConfigEnabled');
      cy.wait('@getUser');

      // 2. Wait for form initialization to complete
      cy.get('#org-settings-email').should('be.visible');

      // 3. Wait for dropdown to be populated and scroll it into view
      cy.get('[data-testid="tag-expiration-picker"]')
        .scrollIntoView()
        .should('be.visible')
        .find('option')
        .should('have.length.greaterThan', 0);

      // 4. Verify the dropdown values using the config from this context
      const options = config.config.TAG_EXPIRATION_OPTIONS;
      options.forEach((option) => {
        const duration = parseTimeDuration(option);
        const durationInSeconds = duration.asSeconds();
        const humanized = humanizeTimeForExpiry(durationInSeconds);

        // 5. More stable selector - find by value instead of just position
        cy.get('[data-testid="tag-expiration-picker"]')
          .find(`option[value="${durationInSeconds}"]`)
          .should('exist')
          .and('contain', humanized);
      });

      // Verify the correct value is selected
      cy.get('[data-testid="tag-expiration-picker"]').should(
        'have.value',
        60 * 60 * 24 * 80, // 80 days in seconds
      );
    });
  });

  it('Billing Information', () => {
    cy.fixture('config.json').then((config) => {
      config.features.BILLING = true;
      cy.intercept('GET', '/config', config).as('getConfigWithBilling');
    });

    cy.visit('/organization/user1?tab=Settings');
    cy.wait('@getConfigWithBilling');

    // navigate to billing tab
    cy.contains('Billing information').click();

    // Type a bad e-mail
    cy.get('#billing-settings-invoice-email').clear();
    cy.get('#billing-settings-invoice-email').type('this is not a good e-mail');

    // check is disabled
    cy.get('#save-billing-settings').should('be.disabled');
    cy.get('#billing-settings-invoice-email').clear();

    // Type a good e-mail and save
    cy.get('#billing-settings-invoice-email').type('invoice-email@redhat.com');

    // check save receipts
    cy.get('#checkbox').should('not.be.checked');
    cy.get('#checkbox').click();

    // Save
    cy.get('#save-billing-settings').click();

    // refresh page, navigate to billing tab and check if email is saved
    cy.reload();
    cy.get('#pf-tab-1-billinginformation').click();
    cy.get('#billing-settings-invoice-email').should(
      'have.value',
      'invoice-email@redhat.com',
    );
    cy.get('#checkbox').should('be.checked');
  });

  it('CLI Token', () => {
    cy.visit('/organization/user1?tab=Settings');

    // navigate to CLI Tab
    cy.contains('CLI configuration').click();

    // Click generate password
    cy.get('#cli-password-button').click();

    // Wrong password
    cy.get('#delete-confirmation-input').type('wrongpassword');
    cy.get('#submit').click();
    cy.contains('Invalid Username or Password');

    // Correct password
    cy.get('#delete-confirmation-input').clear();
    cy.get('#delete-confirmation-input').type('password');
    cy.get('#submit').click();
    cy.contains('Your encrypted password is');
  });

  it('Avatar Display', () => {
    cy.intercept('GET', '/api/v1/user', (req) => {
      req.continue((res) => {
        res.body.avatar = {
          name: 'user1',
          hash: 'abcd1234',
          color: '#e74c3c',
          kind: 'user',
        };
      });
    }).as('getUserWithAvatar');

    cy.visit('/organization/user1?tab=Settings');
    cy.wait('@getUserWithAvatar');

    // Check avatar appears in general settings
    cy.get('[data-testid="form-avatar"]').should('exist');
    cy.get('[data-testid="form-avatar"]').within(() => {
      cy.get('[data-testid="avatar"]').should('exist');
      cy.contains('Avatar is generated based off of your username');
    });
  });

  it('Password Change Modal', () => {
    cy.fixture('config.json').then((config) => {
      config.config.AUTHENTICATION_TYPE = 'Database';
      cy.intercept('GET', '/config', config).as('getConfigWithDatabase');
    });

    cy.visit('/organization/user1?tab=Settings');
    cy.wait('@getConfigWithDatabase');

    // Check password change link appears
    cy.contains('Change password').should('exist');

    // Click to open modal
    cy.contains('Change password').click();
    cy.get('[data-testid="change-password-modal"]').should('be.visible');

    // Test form validation
    cy.get('#new-password').type('short');
    cy.get('#confirm-password').type('short');
    cy.get('[data-testid="change-password-submit"]').should('be.disabled');

    // Clear and enter valid passwords that don't match
    cy.get('#new-password').clear().type('validpassword123');
    cy.get('#confirm-password').clear().type('differentpassword123');
    cy.get('[data-testid="change-password-submit"]').should('be.disabled');

    // Enter matching valid passwords
    cy.get('#new-password').clear().type('validpassword123');
    cy.get('#confirm-password').clear().type('validpassword123');
    cy.get('[data-testid="change-password-submit"]').should('not.be.disabled');

    // Mock successful password change
    cy.intercept('PUT', '/api/v1/user/', {
      statusCode: 200,
      body: {},
    }).as('changePassword');

    cy.get('[data-testid="change-password-submit"]').click();
    cy.wait('@changePassword');

    // Modal should close
    cy.get('[data-testid="change-password-modal"]').should('not.exist');
  });

  it('Account Type Change Modal', () => {
    cy.fixture('config.json').then((config) => {
      config.config.AUTHENTICATION_TYPE = 'Database';
      cy.intercept('GET', '/config', config).as('getConfigWithDatabase');
    });

    // Mock user with organization memberships (realistic scenario)
    cy.intercept('GET', '/api/v1/user', (req) => {
      req.continue((res) => {
        res.body.organizations = [
          {
            name: 'testorg1',
            is_org_admin: false,
            email: 'test@org1.com',
            tag_expiration_s: 1209600,
            avatar: {
              name: 'testorg1',
              hash: 'abc123',
              color: '#e74c3c',
              kind: 'org',
            },
          },
          {
            name: 'testorg2',
            is_org_admin: true,
            email: 'test@org2.com',
            tag_expiration_s: 1209600,
            avatar: {
              name: 'testorg2',
              hash: 'def456',
              color: '#3498db',
              kind: 'org',
            },
          },
        ];
      });
    }).as('getUserWithOrgs');

    cy.visit('/organization/user1?tab=Settings');
    cy.wait('@getConfigWithDatabase');
    cy.wait('@getUserWithOrgs');

    // Check account type link appears
    cy.contains('Individual account').should('exist');

    // Click to open modal
    cy.contains('Individual account').click();
    cy.get('[data-testid="change-account-type-modal"]').should('be.visible');

    // Should show warning about unable to convert (user has organizations)
    cy.contains('This account cannot be converted into an organization').should(
      'exist',
    );

    // Close modal
    cy.get('[data-testid="change-account-type-modal-close"]').click();
    cy.get('[data-testid="change-account-type-modal"]').should('not.exist');
  });

  it('Desktop Notifications', () => {
    // Mock browser notifications as available before visiting page
    cy.visit('/organization/user1?tab=Settings', {
      onBeforeLoad: (win) => {
        // Mock Notification API properly before page loads
        const mockNotification = function () {
          // Empty constructor for mocking purposes
        } as unknown as typeof Notification;
        (mockNotification as any).permission = 'default';
        (mockNotification as any).requestPermission = cy
          .stub()
          .resolves('granted');

        win.Notification = mockNotification;
      },
    });

    // Intercept API calls with proper mock data
    cy.intercept('GET', '/api/v1/user', {
      body: {
        username: 'user1',
        email: 'user1@example.com',
        organizations: [], // Provide empty array instead of undefined
      },
    }).as('getUser');
    cy.intercept('GET', '/api/v1/organization/user1', {statusCode: 404}).as(
      'getOrg404',
    );

    // Wait for desktop notifications checkbox to appear (user data may be cached)
    cy.get('[data-testid="form-notifications"]', {timeout: 10000}).should(
      'exist',
    );
    cy.contains('Enable desktop notifications').should('exist');

    // Click checkbox to enable notifications
    cy.get('#form-notifications').click();

    // Confirmation modal should appear
    cy.get('[data-testid="desktop-notifications-modal"]').should('be.visible');
    cy.contains('Enable Desktop Notifications').should('exist');

    // Confirm enabling
    cy.get('[data-testid="notification-confirm"]').click();

    // Wait for the async handleNotificationConfirm to complete
    cy.wait(100); // Small wait for async operation

    // Modal should close and checkbox should be checked
    cy.get('[data-testid="desktop-notifications-modal"]').should('not.exist');
    cy.get('#form-notifications').should('be.checked');

    // Click again to disable
    cy.get('#form-notifications').click();
    cy.get('[data-testid="desktop-notifications-modal"]').should('be.visible');
    cy.contains('Disable Desktop Notifications').should('exist');

    // Cancel should leave checkbox unchanged
    cy.get('[data-testid="notification-cancel"]').click();
    cy.get('[data-testid="desktop-notifications-modal"]').should('not.exist');
    cy.get('#form-notifications').should('be.checked');
  });

  it('Delete Account', () => {
    cy.fixture('config.json').then((config) => {
      config.config.AUTHENTICATION_TYPE = 'Database';
      cy.intercept('GET', '/config', config).as('getConfigWithDatabase');
    });

    // Intercept API calls to ensure user vs org detection works
    cy.intercept('GET', '/api/v1/user').as('getUser');
    cy.intercept('GET', '/api/v1/organization/user1', {statusCode: 404}).as(
      'getOrg404',
    );

    cy.visit('/organization/user1?tab=Settings');
    cy.wait('@getConfigWithDatabase');
    cy.wait('@getUser');

    // Check delete button appears
    cy.contains('Delete account').should('exist');

    // Click to open modal
    cy.contains('Delete account').click();
    cy.get('[data-testid="delete-account-modal"]').should('be.visible');

    // Check warning message
    cy.contains('Deleting an account is non-reversible');
    cy.contains('You must type user1 below to confirm deletion is requested');

    // Submit button should be disabled initially
    cy.get('[data-testid="delete-account-confirm"]').should('be.disabled');

    // Type wrong name
    cy.get('#delete-confirmation-input').type('wrongname');
    cy.get('[data-testid="delete-account-confirm"]').should('be.disabled');

    // Type correct name
    cy.get('#delete-confirmation-input').clear().type('user1');
    cy.get('[data-testid="delete-account-confirm"]').should('not.be.disabled');

    // Mock successful deletion (should redirect)
    cy.intercept('DELETE', '/api/v1/user/', {
      statusCode: 204,
    }).as('deleteUser');

    cy.get('[data-testid="delete-account-confirm"]').click();
    cy.wait('@deleteUser');

    // Should redirect to signin
    cy.url().should('include', '/signin');
  });

  it('Application Tokens Management', () => {
    // Mock existing tokens
    cy.intercept('GET', '/api/v1/user/apptoken', {
      body: {
        tokens: [
          {
            uuid: 'token1-uuid',
            title: 'My CLI Token',
            last_accessed: '2024-01-15T10:30:00Z',
            created: '2024-01-01T09:00:00Z',
            expiration: null,
          },
          {
            uuid: 'token2-uuid',
            title: 'Docker Token',
            last_accessed: null,
            created: '2024-01-10T14:20:00Z',
            expiration: '2024-12-31T23:59:59Z',
          },
        ],
        only_expiring: false,
      },
    }).as('getTokens');

    cy.visit('/organization/user1?tab=Settings');

    // Navigate to CLI configuration tab
    cy.contains('CLI configuration').click();
    cy.wait('@getTokens');

    // Check section title
    cy.contains('Docker CLI and other Application Tokens').should('exist');

    // Check tokens table
    cy.get('table')
      .last()
      .within(() => {
        cy.contains('My CLI Token').should('exist');
        cy.contains('Docker Token').should('exist');
        cy.contains('1/15/2024').should('exist'); // last accessed
        cy.contains('Never').should('exist'); // never accessed
      });

    // Test create token
    cy.get('#create-app-token-button').click();
    cy.get('[data-testid="create-token-modal"]').should('be.visible');

    // Enter token title
    cy.get('#token-title').type('Test Token');

    // Mock successful token creation
    cy.intercept('POST', '/api/v1/user/apptoken', {
      statusCode: 200,
      body: {
        token: {
          uuid: 'new-token-uuid',
          title: 'Test Token',
          token_code: 'fake-token-not-real',
          created: '2024-01-20T12:00:00Z',
          expiration: null,
          last_accessed: null,
        },
      },
    }).as('createToken');

    // Mock updated token list (with new token added)
    cy.intercept('GET', '/api/v1/user/apptoken', {
      body: {
        tokens: [
          {
            uuid: 'token1-uuid',
            title: 'My CLI Token',
            last_accessed: '2024-01-15T10:30:00Z',
            created: '2024-01-01T09:00:00Z',
            expiration: null,
          },
          {
            uuid: 'token2-uuid',
            title: 'Docker Token',
            last_accessed: null,
            created: '2024-01-10T14:20:00Z',
            expiration: '2024-12-31T23:59:59Z',
          },
          {
            uuid: 'new-token-uuid',
            title: 'Test Token',
            last_accessed: null,
            created: '2024-01-20T12:00:00Z',
            expiration: null,
          },
        ],
        only_expiring: false,
      },
    }).as('getTokensAfterCreate');

    cy.get('[data-testid="create-token-submit"]').click();
    cy.wait('@createToken');

    // Should show success step with token
    cy.get('[data-testid="create-token-modal"]').within(() => {
      cy.contains('Token Created Successfully').should('exist');
      cy.get('[data-testid="copy-token-button"]').should('exist');
    });

    cy.get('[data-testid="create-token-close"]').click();
    cy.get('[data-testid="create-token-modal"]').should('not.exist');
    cy.wait('@getTokensAfterCreate');

    // Verify new token appears in table
    cy.get('table')
      .last()
      .within(() => {
        cy.contains('Test Token').should('exist'); // The token we just created
        cy.contains('My CLI Token').should('exist'); // Original tokens still there
        cy.contains('Docker Token').should('exist');
      });

    // Test revoke token
    cy.get('table')
      .last()
      .contains('tr', 'My CLI Token')
      .within(() => {
        cy.get('[data-testid="token-actions-dropdown"]').click();
      });
    cy.contains('Revoke Token').click();

    cy.get('[data-testid="revoke-token-modal"]').should('be.visible');
    cy.contains('revoke the application token "My CLI Token"').should('exist');

    // Mock successful revocation
    cy.intercept('DELETE', '/api/v1/user/apptoken/token1-uuid', {
      statusCode: 204,
    }).as('revokeToken');

    // Mock updated token list (without revoked token)
    cy.intercept('GET', '/api/v1/user/apptoken', {
      body: {
        tokens: [
          {
            uuid: 'token2-uuid',
            title: 'Docker Token',
            last_accessed: null,
            created: '2024-01-10T14:20:00Z',
            expiration: '2024-12-31T23:59:59Z',
          },
        ],
        only_expiring: false,
      },
    }).as('getTokensAfterRevoke');

    cy.get('[data-testid="revoke-token-confirm"]').click();
    cy.wait('@revokeToken');
    cy.wait('@getTokensAfterRevoke');

    // Modal should close and token should be removed from table
    cy.get('[data-testid="revoke-token-modal"]').should('not.exist');
    cy.get('table')
      .last()
      .within(() => {
        cy.contains('My CLI Token').should('not.exist');
        cy.contains('Docker Token').should('exist');
      });
  });

  it('Application Tokens Empty State', () => {
    // Mock empty token response
    cy.intercept('GET', '/api/v1/user/apptoken', {
      body: {
        tokens: [],
        only_expiring: false,
      },
    }).as('getEmptyTokens');

    cy.visit('/organization/user1?tab=Settings');

    // Navigate to CLI configuration tab
    cy.contains('CLI configuration').click();
    cy.wait('@getEmptyTokens');

    // Check empty state
    cy.contains('No application tokens').should('exist');
    cy.contains("You haven't created any application tokens yet").should(
      'exist',
    );
  });

  it('Feature Visibility Based on User Type and Auth', () => {
    // Intercept user API call as well
    cy.intercept('GET', '/api/v1/user').as('getUser');

    // Test organization view - should not show user-specific features
    cy.intercept('GET', '/api/v1/organization/testorg', {
      body: {
        name: 'testorg',
        email: 'org@example.com',
        avatar: {
          name: 'testorg',
          hash: 'org1234',
          color: '#3498db',
          kind: 'org',
        },
        is_admin: true,
      },
    }).as('getOrg');

    cy.visit('/organization/testorg?tab=Settings');
    cy.wait('@getUser');
    cy.wait('@getOrg');

    // User-specific features should not appear for organizations
    cy.contains('Change password').should('not.exist');
    cy.contains('Individual account').should('not.exist');
    cy.get('[data-testid="form-notifications"]').should('not.exist');

    // Test non-database auth - should not show password/account type
    cy.fixture('config.json').then((config) => {
      config.config.AUTHENTICATION_TYPE = 'LDAP';
      cy.intercept('GET', '/config', config).as('getConfigWithLDAP');
    });

    cy.visit('/organization/user1?tab=Settings');
    cy.wait('@getConfigWithLDAP');

    // Database-only features should not appear
    cy.contains('Change password').should('not.exist');
    cy.contains('Individual account').should('not.exist');
    cy.contains('Delete account').should('not.exist');
  });
});
