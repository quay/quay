/// <reference types="cypress" />

describe('Quota Management', () => {
  beforeEach(() => {
    // Handle pre-existing CanceledError from organization page navigation
    cy.on('uncaught:exception', (err) => {
      if (
        err.message.includes('canceled') ||
        err.message.includes('CanceledError')
      ) {
        return false;
      }
      return true;
    });

    // Seed database
    cy.exec('npm run quay:seed');

    // Get CSRF token and login
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  describe('Feature Flags', () => {
    it('should not show quota tab when QUOTA_MANAGEMENT feature is disabled', () => {
      cy.fixture('config.json').then((config) => {
        config.features.QUOTA_MANAGEMENT = false;
        config.features.EDIT_QUOTA = true;
        config.features.SUPER_USERS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      cy.get('[data-testid="Quota"]').should('not.exist');
    });

    it('should not show quota tab when EDIT_QUOTA feature is disabled', () => {
      cy.fixture('config.json').then((config) => {
        config.features.QUOTA_MANAGEMENT = true;
        config.features.EDIT_QUOTA = false;
        config.features.SUPER_USERS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      cy.get('[data-testid="Quota"]').should('not.exist');
    });

    it('should show quota tab when all required features are enabled', () => {
      cy.fixture('config.json').then((config) => {
        config.features.QUOTA_MANAGEMENT = true;
        config.features.EDIT_QUOTA = true;
        config.features.SUPER_USERS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.intercept('GET', '**/api/v1/organization/projectquay/quota*', {
        statusCode: 200,
        body: [],
      }).as('getQuota');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      cy.get('[data-testid="Quota"]').should('exist');
    });
  });

  describe('Organization Settings - Read-Only (Non-Superuser)', () => {
    beforeEach(() => {
      // Mock regular user
      cy.fixture('config.json').then((config) => {
        config.features.QUOTA_MANAGEMENT = true;
        config.features.EDIT_QUOTA = true;
        config.features.SUPER_USERS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('user.json').then((user) => {
        user.super_user = false;
        cy.intercept('GET', '/api/v1/user/', user).as('getUser');
      });
    });

    it('should display alert when no quota is configured for non-superuser', () => {
      cy.intercept('GET', '**/api/v1/organization/projectquay/quota*', {
        statusCode: 200,
        body: [],
      }).as('getQuotaEmpty');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaEmpty');

      // Should see alert for non-superuser with no quota
      cy.get('[data-testid="no-quota-alert"]').should('be.visible');
      cy.contains('Quota must be configured by a superuser').should('exist');
    });

    it('should display read-only quota when quota is configured for non-superuser', () => {
      cy.intercept('GET', '**/api/v1/organization/projectquay/quota*', {
        statusCode: 200,
        body: [
          {
            id: 1,
            limit_bytes: 10737418240,
            limit: '10.0 GiB',
            default_config: false,
            limits: [],
            default_config_exists: false,
          },
        ],
      }).as('getQuotaWithData');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaWithData');

      // Should see read-only alert
      cy.get('[data-testid="readonly-quota-alert"]').should('be.visible');

      // All fields should be disabled
      cy.get('[data-testid="quota-value-input"]').should('be.disabled');
      cy.get('[data-testid="quota-unit-select-toggle"]').should('be.disabled');

      // Apply and Remove buttons should NOT exist
      cy.get('[data-testid="apply-quota-button"]').should('not.exist');
      cy.get('[data-testid="remove-quota-button"]').should('not.exist');
    });
  });

  describe('Organization Settings - Read-Only (Superuser)', () => {
    beforeEach(() => {
      // Mock superuser
      cy.fixture('config.json').then((config) => {
        config.features.QUOTA_MANAGEMENT = true;
        config.features.EDIT_QUOTA = true;
        config.features.SUPER_USERS = true;
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });
    });

    it('should display alert when no quota is configured for superuser', () => {
      cy.intercept('GET', '**/api/v1/organization/projectquay/quota*', {
        statusCode: 200,
        body: [],
      }).as('getQuotaEmpty');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaEmpty');

      // Should see alert for superuser with no quota
      cy.get('[data-testid="no-quota-superuser-alert"]').should('be.visible');
      cy.contains(
        'Use the "Configure Quota" option from the Organizations list page to set up quota for this organization.',
      ).should('exist');
    });

    it('should display read-only quota when quota is configured for superuser', () => {
      cy.intercept('GET', '**/api/v1/organization/projectquay/quota*', {
        statusCode: 200,
        body: [
          {
            id: 1,
            limit_bytes: 10737418240,
            limit: '10.0 GiB',
            default_config: false,
            limits: [
              {
                id: 1,
                type: 'Warning',
                limit_percent: 80,
              },
            ],
            default_config_exists: false,
          },
        ],
      }).as('getQuotaWithData');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaWithData');

      // Should see read-only alert (same as non-superuser)
      cy.get('[data-testid="readonly-quota-alert"]').should('be.visible');

      // All fields should be disabled (even for superusers in org-view)
      cy.get('[data-testid="quota-value-input"]').should('be.disabled');
      cy.get('[data-testid="quota-unit-select-toggle"]').should('be.disabled');

      // Apply and Remove buttons should NOT exist
      cy.get('[data-testid="apply-quota-button"]').should('not.exist');
      cy.get('[data-testid="remove-quota-button"]').should('not.exist');

      // Quota policy fields should also be disabled
      cy.get('[data-testid="new-limit-type-select"]').should('be.disabled');
      cy.get('[data-testid="new-limit-percent-input"]').should('be.disabled');
      cy.get('[data-testid="add-limit-button"]').should('be.disabled');
    });

    it('should prevent quota submission attempts from organization-view (should not show 403 errors)', () => {
      cy.intercept('GET', '**/api/v1/organization/projectquay/quota*', {
        statusCode: 200,
        body: [
          {
            id: 1,
            limit_bytes: 10737418240,
            limit: '10.0 GiB',
            default_config: false,
            limits: [
              {
                id: 1,
                type: 'Warning',
                limit_percent: 80,
              },
            ],
            default_config_exists: false,
          },
        ],
      }).as('getQuotaWithData');

      // Ensure no API calls are made when attempting to submit from org-view
      cy.intercept('POST', '**/api/v1/organization/projectquay/quota*', {
        statusCode: 403,
      }).as('createQuota');
      cy.intercept('PUT', '**/api/v1/organization/projectquay/quota/*', {
        statusCode: 403,
      }).as('updateQuota');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaWithData');

      // Verify the form is rendered and read-only alert is visible
      cy.get('[data-testid="quota-management-form"]').should('be.visible');
      cy.get('[data-testid="readonly-quota-alert"]').should('be.visible');

      // Verify all form fields are disabled (read-only mode)
      cy.get('[data-testid="quota-value-input"]').should('be.disabled');
      cy.get('[data-testid="quota-unit-select-toggle"]').should('be.disabled');

      // Verify action buttons don't exist (they're hidden in organization-view)
      cy.get('[data-testid="apply-quota-button"]').should('not.exist');
      cy.get('[data-testid="remove-quota-button"]').should('not.exist');

      // Since form submission is prevented by disabled fields and hidden buttons,
      // and our guards in onSubmit(), no API calls should be made
      // Wait a bit to ensure no API calls are triggered
      cy.wait(1000);

      // Verify no API calls were made (no 403 errors should occur)
      cy.get('@createQuota.all').should('have.length', 0);
      cy.get('@updateQuota.all').should('have.length', 0);
    });
  });

  describe('Configure Quota Modal - Access Control', () => {
    beforeEach(() => {
      // Mock superuser
      cy.fixture('config.json').then((config) => {
        config.features.QUOTA_MANAGEMENT = true;
        config.features.EDIT_QUOTA = true;
        config.features.SUPER_USERS = true;
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.fixture('superuser-organizations.json').then((orgsData) => {
        cy.intercept('GET', '/api/v1/superuser/organizations/', orgsData).as(
          'getSuperuserOrganizations',
        );
      });

      cy.fixture('superuser-users.json').then((usersData) => {
        cy.intercept('GET', '/api/v1/superuser/users/', usersData).as(
          'getSuperuserUsers',
        );
      });

      // Mock organization details
      cy.intercept('GET', '/api/v1/organization/testorg', {
        statusCode: 200,
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          teams: {owners: 'admin'},
        },
      });

      cy.intercept('GET', '/api/v1/organization/projectquay', {
        statusCode: 200,
        body: {
          name: 'projectquay',
          email: 'projectquay@example.com',
          teams: {},
        },
      });

      // Mock robots/members
      cy.intercept('GET', '/api/v1/organization/*/robots', {
        statusCode: 200,
        body: {robots: []},
      });

      cy.intercept('GET', '/api/v1/organization/*/members', {
        statusCode: 200,
        body: {members: []},
      });
    });

    it('should show Configure Quota option for organizations', () => {
      cy.intercept('GET', '**/api/v1/organization/testorg/quota*', {
        statusCode: 200,
        body: [],
      }).as('getQuota');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');

      // Find testorg row and click kebab menu
      cy.get('[data-testid="testorg-options-toggle"]')
        .should('be.visible')
        .click();

      // Should see Configure Quota option
      cy.contains('Configure Quota').should('be.visible');
    });

    it('should hide Configure Quota when feature flags are disabled', () => {
      cy.fixture('config.json').then((config) => {
        config.features.QUOTA_MANAGEMENT = false; // Disable quota management
        config.features.EDIT_QUOTA = true;
        config.features.SUPER_USERS = true;
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfigNoQuota');
      });

      cy.visit('/organization');
      cy.wait('@getConfigNoQuota');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');

      // Find testorg row and click kebab menu
      cy.get('[data-testid="testorg-options-toggle"]')
        .should('be.visible')
        .click();

      // Should NOT see Configure Quota option
      cy.contains('Configure Quota').should('not.exist');
    });

    it('should hide Configure Quota for non-superusers', () => {
      cy.fixture('config.json').then((config) => {
        config.features.QUOTA_MANAGEMENT = true;
        config.features.EDIT_QUOTA = true;
        config.features.SUPER_USERS = true;
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('user.json').then((user) => {
        user.super_user = false;
        cy.intercept('GET', '/api/v1/user/', user).as('getUser');
      });

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getUser');

      // For non-superusers, kebab menu should not exist at all
      cy.get('[data-testid="testorg-options-toggle"]').should('not.exist');
    });
  });

  describe('Configure Quota Modal - Create Quota', () => {
    beforeEach(() => {
      // Mock superuser
      cy.fixture('config.json').then((config) => {
        config.features.QUOTA_MANAGEMENT = true;
        config.features.EDIT_QUOTA = true;
        config.features.SUPER_USERS = true;
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.fixture('superuser-organizations.json').then((orgsData) => {
        cy.intercept('GET', '/api/v1/superuser/organizations/', orgsData).as(
          'getSuperuserOrganizations',
        );
      });

      // Mock organization details
      cy.intercept('GET', '/api/v1/organization/testorg', {
        statusCode: 200,
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          teams: {owners: 'admin'},
        },
      });

      // Mock robots/members
      cy.intercept('GET', '/api/v1/organization/*/robots', {
        statusCode: 200,
        body: {robots: []},
      });

      cy.intercept('GET', '/api/v1/organization/*/members', {
        statusCode: 200,
        body: {members: []},
      });
    });

    it('should successfully create quota from modal', () => {
      cy.intercept('GET', '**/api/v1/organization/testorg/quota*', {
        statusCode: 200,
        body: [],
      }).as('getQuotaEmpty');

      cy.intercept('POST', '/api/v1/organization/testorg/quota*', {
        statusCode: 201,
        body: 'Created',
      }).as('createQuota');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');

      // Open Configure Quota modal
      cy.get('[data-testid="testorg-options-toggle"]')
        .should('be.visible')
        .click();
      cy.contains('Configure Quota').click();

      // Wait for modal to open
      cy.get('[data-testid="configure-quota-modal"]').should('be.visible');
      cy.wait('@getQuotaEmpty');

      // Verify modal title
      cy.contains('Configure Quota for testorg').should('exist');

      // Fields should NOT be disabled in super-user view
      cy.get('[data-testid="quota-value-input"]').should('not.be.disabled');
      cy.get('[data-testid="quota-value-input"]').clear().type('100');

      // Apply button should be enabled
      cy.get('[data-testid="apply-quota-button"]')
        .should('not.be.disabled')
        .click();

      cy.wait('@createQuota');
    });

    it('should handle creation errors', () => {
      cy.intercept('GET', '**/api/v1/organization/testorg/quota*', {
        statusCode: 200,
        body: [],
      }).as('getQuotaEmpty');

      cy.intercept('POST', '/api/v1/organization/testorg/quota*', {
        statusCode: 400,
        body: {message: 'Validation error'},
      }).as('createQuotaError');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');

      // Open Configure Quota modal
      cy.get('[data-testid="testorg-options-toggle"]')
        .should('be.visible')
        .click();
      cy.contains('Configure Quota').click();

      cy.get('[data-testid="configure-quota-modal"]').should('be.visible');
      cy.wait('@getQuotaEmpty');

      // Enter quota value
      cy.get('[data-testid="quota-value-input"]').clear().type('100');
      cy.get('[data-testid="apply-quota-button"]').click();

      cy.wait('@createQuotaError');

      // Should see error message
      cy.contains('quota creation error').should('exist');
    });
  });

  describe('Configure Quota Modal - Update Quota', () => {
    beforeEach(() => {
      // Mock superuser
      cy.fixture('config.json').then((config) => {
        config.features.QUOTA_MANAGEMENT = true;
        config.features.EDIT_QUOTA = true;
        config.features.SUPER_USERS = true;
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.fixture('superuser-organizations.json').then((orgsData) => {
        cy.intercept('GET', '/api/v1/superuser/organizations/', orgsData).as(
          'getSuperuserOrganizations',
        );
      });

      // Mock organization details
      cy.intercept('GET', '/api/v1/organization/testorg', {
        statusCode: 200,
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          teams: {owners: 'admin'},
        },
      });

      // Mock robots/members
      cy.intercept('GET', '/api/v1/organization/*/robots', {
        statusCode: 200,
        body: {robots: []},
      });

      cy.intercept('GET', '/api/v1/organization/*/members', {
        statusCode: 200,
        body: {members: []},
      });
    });

    it('should display existing quota in modal', () => {
      cy.intercept('GET', '**/api/v1/organization/testorg/quota*', {
        statusCode: 200,
        body: [
          {
            id: 1,
            limit_bytes: 10737418240,
            limit: '10.0 GiB',
            default_config: false,
            limits: [
              {
                id: 1,
                type: 'Warning',
                limit_percent: 80,
              },
            ],
            default_config_exists: false,
          },
        ],
      }).as('getQuotaWithData');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');

      // Open Configure Quota modal
      cy.get('[data-testid="testorg-options-toggle"]')
        .should('be.visible')
        .click();
      cy.contains('Configure Quota').click();

      cy.get('[data-testid="configure-quota-modal"]').should('be.visible');
      cy.wait('@getQuotaWithData');

      // Should display existing quota value
      cy.get('[data-testid="quota-value-input"]').should('have.value', '10');
      cy.get('[data-testid="quota-unit-select-toggle"]').should(
        'contain.text',
        'GiB',
      );

      // Should show existing limits
      cy.get('[data-testid="quota-limit-1"]').should('exist');
      cy.contains('Warning').should('exist');
    });

    it('should successfully update existing quota', () => {
      cy.intercept('GET', '**/api/v1/organization/testorg/quota*', {
        statusCode: 200,
        body: [
          {
            id: 1,
            limit_bytes: 10737418240,
            limit: '10.0 GiB',
            default_config: false,
            limits: [],
            default_config_exists: false,
          },
        ],
      }).as('getQuotaWithData');

      cy.intercept('PUT', '**/api/v1/organization/testorg/quota/1*', {
        statusCode: 200,
        body: {
          id: 1,
          limit_bytes: 21474836480,
          limit: '20.0 GiB',
          default_config: false,
          limits: [],
          default_config_exists: false,
        },
      }).as('updateQuota');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');

      // Open Configure Quota modal
      cy.get('[data-testid="testorg-options-toggle"]')
        .should('be.visible')
        .click();
      cy.contains('Configure Quota').click();

      cy.get('[data-testid="configure-quota-modal"]').should('be.visible');
      cy.wait('@getQuotaWithData');

      // Update quota value
      cy.get('[data-testid="quota-value-input"]').clear().type('20');
      cy.get('[data-testid="apply-quota-button"]').click();

      cy.wait('@updateQuota');
      cy.contains('Successfully updated quota').should('exist');
    });
  });

  describe('Configure Quota Modal - Delete Quota', () => {
    beforeEach(() => {
      // Mock superuser
      cy.fixture('config.json').then((config) => {
        config.features.QUOTA_MANAGEMENT = true;
        config.features.EDIT_QUOTA = true;
        config.features.SUPER_USERS = true;
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.fixture('superuser-organizations.json').then((orgsData) => {
        cy.intercept('GET', '/api/v1/superuser/organizations/', orgsData).as(
          'getSuperuserOrganizations',
        );
      });

      // Mock organization details
      cy.intercept('GET', '/api/v1/organization/testorg', {
        statusCode: 200,
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          teams: {owners: 'admin'},
        },
      });

      // Mock robots/members
      cy.intercept('GET', '/api/v1/organization/*/robots', {
        statusCode: 200,
        body: {robots: []},
      });

      cy.intercept('GET', '/api/v1/organization/*/members', {
        statusCode: 200,
        body: {members: []},
      });
    });

    it('should successfully delete quota', () => {
      cy.intercept('GET', '**/api/v1/organization/testorg/quota*', {
        statusCode: 200,
        body: [
          {
            id: 1,
            limit_bytes: 10737418240,
            limit: '10.0 GiB',
            default_config: false,
            limits: [],
            default_config_exists: false,
          },
        ],
      }).as('getQuotaWithData');

      cy.intercept('DELETE', '/api/v1/organization/testorg/quota/1*', {
        statusCode: 204,
      }).as('deleteQuota');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');

      // Open Configure Quota modal
      cy.get('[data-testid="testorg-options-toggle"]')
        .should('be.visible')
        .click();
      cy.contains('Configure Quota').click();

      cy.get('[data-testid="configure-quota-modal"]').should('be.visible');
      cy.wait('@getQuotaWithData');

      // Click Remove button
      cy.get('[data-testid="remove-quota-button"]')
        .should('be.visible')
        .click();

      // Confirm deletion in modal
      cy.contains('Delete Quota').should('be.visible');
      cy.get('[data-testid="confirm-delete-quota"]')
        .should('be.visible')
        .click();

      cy.wait('@deleteQuota');
    });
  });

  describe('Configure Quota Modal - Quota Limits', () => {
    beforeEach(() => {
      // Mock superuser
      cy.fixture('config.json').then((config) => {
        config.features.QUOTA_MANAGEMENT = true;
        config.features.EDIT_QUOTA = true;
        config.features.SUPER_USERS = true;
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.fixture('superuser-organizations.json').then((orgsData) => {
        cy.intercept('GET', '/api/v1/superuser/organizations/', orgsData).as(
          'getSuperuserOrganizations',
        );
      });

      // Mock organization details
      cy.intercept('GET', '/api/v1/organization/testorg', {
        statusCode: 200,
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          teams: {owners: 'admin'},
        },
      });

      // Mock robots/members
      cy.intercept('GET', '/api/v1/organization/*/robots', {
        statusCode: 200,
        body: {robots: []},
      });

      cy.intercept('GET', '/api/v1/organization/*/members', {
        statusCode: 200,
        body: {members: []},
      });
    });

    it('should successfully add quota limit', () => {
      cy.intercept('GET', '**/api/v1/organization/testorg/quota*', {
        statusCode: 200,
        body: [
          {
            id: 1,
            limit_bytes: 10737418240,
            limit: '10.0 GiB',
            default_config: false,
            limits: [],
            default_config_exists: false,
          },
        ],
      }).as('getQuotaNoLimits');

      cy.intercept('POST', '/api/v1/organization/testorg/quota/1/limit*', {
        statusCode: 201,
        body: 'Created',
      }).as('createQuotaLimit');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');

      // Open Configure Quota modal
      cy.get('[data-testid="testorg-options-toggle"]')
        .should('be.visible')
        .click();
      cy.contains('Configure Quota').click();

      cy.get('[data-testid="configure-quota-modal"]').should('be.visible');
      cy.wait('@getQuotaNoLimits');

      // Fields should NOT be disabled in modal
      cy.get('[data-testid="new-limit-type-select"]').should('not.be.disabled');
      cy.get('[data-testid="new-limit-type-select"]').click();
      cy.contains('Warning').click();

      cy.get('[data-testid="new-limit-percent-input"]')
        .should('not.be.disabled')
        .clear()
        .type('80');

      cy.get('[data-testid="add-limit-button"]')
        .should('not.be.disabled')
        .click();

      cy.wait('@createQuotaLimit');
    });

    it('should successfully update quota limit', () => {
      cy.intercept('GET', '**/api/v1/organization/testorg/quota*', {
        statusCode: 200,
        body: [
          {
            id: 1,
            limit_bytes: 10737418240,
            limit: '10.0 GiB',
            default_config: false,
            limits: [
              {
                id: 1,
                type: 'Warning',
                limit_percent: 80,
              },
            ],
            default_config_exists: false,
          },
        ],
      }).as('getQuotaWithLimits');

      cy.intercept('PUT', '/api/v1/organization/testorg/quota/1/limit/1*', {
        statusCode: 200,
        body: 'Updated',
      }).as('updateQuotaLimit');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');

      // Open Configure Quota modal
      cy.get('[data-testid="testorg-options-toggle"]')
        .should('be.visible')
        .click();
      cy.contains('Configure Quota').click();

      cy.get('[data-testid="configure-quota-modal"]').should('be.visible');
      cy.wait('@getQuotaWithLimits');

      // Update limit percentage
      cy.get('[data-testid="limit-percent-input"]')
        .should('not.be.disabled')
        .clear()
        .type('85');

      cy.get('[data-testid="update-limit-button"]')
        .should('not.be.disabled')
        .click();

      cy.wait('@updateQuotaLimit');
    });

    it('should successfully remove quota limit', () => {
      cy.intercept('GET', '**/api/v1/organization/testorg/quota*', {
        statusCode: 200,
        body: [
          {
            id: 1,
            limit_bytes: 10737418240,
            limit: '10.0 GiB',
            default_config: false,
            limits: [
              {
                id: 1,
                type: 'Warning',
                limit_percent: 80,
              },
            ],
            default_config_exists: false,
          },
        ],
      }).as('getQuotaWithLimits');

      cy.intercept('DELETE', '/api/v1/organization/testorg/quota/1/limit/1*', {
        statusCode: 204,
      }).as('deleteQuotaLimit');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');

      // Open Configure Quota modal
      cy.get('[data-testid="testorg-options-toggle"]')
        .should('be.visible')
        .click();
      cy.contains('Configure Quota').click();

      cy.get('[data-testid="configure-quota-modal"]').should('be.visible');
      cy.wait('@getQuotaWithLimits');

      // Remove limit
      cy.get('[data-testid="remove-limit-button"]')
        .should('not.be.disabled')
        .click();

      cy.wait('@deleteQuotaLimit');
    });
  });
});
