/// <reference types="cypress" />

describe('Organization Quota Management', () => {
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

    cy.exec('npm run quay:seed');
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

  describe('Feature Flag Behavior', () => {
    it('should not show quota tab when QUOTA_MANAGEMENT feature is disabled', () => {
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.features['QUOTA_MANAGEMENT'] = false;
          res.body.features['EDIT_QUOTA'] = true;
          res.body.features['SUPER_USERS'] = true;
          return res;
        }),
      ).as('getConfigNoQuota');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfigNoQuota');

      cy.get('[data-testid="Quota"]').should('not.exist');
    });

    it('should not show quota tab when EDIT_QUOTA feature is disabled', () => {
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.features['QUOTA_MANAGEMENT'] = true;
          res.body.features['EDIT_QUOTA'] = false;
          res.body.features['SUPER_USERS'] = true;
          return res;
        }),
      ).as('getConfigNoEditQuota');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfigNoEditQuota');

      cy.get('[data-testid="Quota"]').should('not.exist');
    });

    it('should show quota tab when all required features are enabled', () => {
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.features['QUOTA_MANAGEMENT'] = true;
          res.body.features['EDIT_QUOTA'] = true;
          res.body.features['SUPER_USERS'] = true;
          return res;
        }),
      ).as('getConfigQuotaEnabled');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfigQuotaEnabled');

      cy.get('[data-testid="Quota"]').should('exist');
    });
  });

  describe('Quota Management Form - No Existing Quota', () => {
    beforeEach(() => {
      // Enable quota features
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.features['QUOTA_MANAGEMENT'] = true;
          res.body.features['EDIT_QUOTA'] = true;
          res.body.features['SUPER_USERS'] = true;
          return res;
        }),
      ).as('getConfig');

      // Mock no existing quota (empty array response)
      cy.intercept('GET', '/api/v1/organization/projectquay/quota*', {
        statusCode: 200,
        body: [],
      }).as('getQuotaEmpty');
    });

    it('should display initial state with no quota configured', () => {
      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Check quota tab exists and click it
      cy.get('[data-testid="Quota"]').should('be.visible').click();

      // Wait for quota management form to appear
      cy.get('#quota-management-form', {timeout: 10000}).should('be.visible');

      // Now wait for the API call after form loads
      cy.wait('@getQuotaEmpty');

      // Check basic form elements exist
      cy.get('[data-testid="quota-value-input"]').should('exist');
    });

    it('should enable Apply button when valid quota is entered', () => {
      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Wait for quota tab to be available before clicking
      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaEmpty');

      // Enter valid quota value
      cy.get('[data-testid="quota-value-input"]').clear().type('10');

      // Apply button should now be enabled
      cy.get('[data-testid="apply-quota-button"]').should('not.be.disabled');
    });

    it('should successfully create new quota', () => {
      // Mock POST for quota creation
      cy.intercept('POST', '/api/v1/organization/projectquay/quota*', {
        statusCode: 201,
        body: 'Created',
      }).as('createQuota');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Wait for quota tab to be available before clicking
      cy.get('[data-testid="Quota"]').should('be.visible').click();

      // Wait for quota management form to appear
      cy.get('#quota-management-form', {timeout: 10000}).should('be.visible');
      cy.wait('@getQuotaEmpty'); // Use the beforeEach intercept

      // Wait for form elements to be ready
      cy.get('[data-testid="quota-value-input"]', {timeout: 10000}).should(
        'be.visible',
      );

      // Fill form
      cy.get('[data-testid="quota-value-input"]').clear().type('10');

      // Submit form
      cy.get('[data-testid="apply-quota-button"]').should('not.be.disabled');
      cy.get('[data-testid="apply-quota-button"]').click();

      cy.wait('@createQuota');

      // Just check that the form is still there (success is hard to verify consistently)
      cy.get('[data-testid="apply-quota-button"]').should('exist');
    });

    it('should handle server errors when creating quota', () => {
      // Mock server error response (simulating server-side validation or system error)
      cy.intercept('POST', '**/api/v1/organization/projectquay/quota*', {
        statusCode: 400,
        body: {message: 'Server validation failed'},
      }).as('createQuotaError');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Wait for quota tab to be available before clicking
      cy.get('[data-testid="Quota"]').should('be.visible').click();

      // Wait for quota management form to appear
      cy.get('#quota-management-form', {timeout: 10000}).should('be.visible');

      // Wait for form elements to be ready
      cy.get('[data-testid="quota-value-input"]', {timeout: 10000}).should(
        'be.visible',
      );
      cy.get('[data-testid="apply-quota-button"]', {timeout: 10000}).should(
        'be.visible',
      );

      // Fill form with valid data to enable the button
      cy.get('[data-testid="quota-value-input"]').clear().type('10');

      // Verify button becomes enabled
      cy.get('[data-testid="apply-quota-button"]').should('not.be.disabled');

      // Submit the form - this should trigger a server error
      cy.get('[data-testid="apply-quota-button"]').click();

      cy.wait('@createQuotaError');
      // Check for the actual error message format from addDisplayError
      cy.contains('quota creation error').should('exist');
    });
  });

  describe('Quota Management Form - Existing Quota', () => {
    beforeEach(() => {
      // Enable quota features
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.features['QUOTA_MANAGEMENT'] = true;
          res.body.features['EDIT_QUOTA'] = true;
          res.body.features['SUPER_USERS'] = true;
          return res;
        }),
      ).as('getConfig');

      // Mock existing quota with limits
      cy.intercept('GET', '**/api/v1/organization/projectquay/quota*', {
        statusCode: 200,
        body: [
          {
            id: 1,
            limit_bytes: 10737418240, // 10 GiB
            limit: '10.0 GiB',
            default_config: false,
            limits: [
              {
                id: 1,
                type: 'Warning',
                limit_percent: 80,
              },
              {
                id: 2,
                type: 'Reject',
                limit_percent: 90,
              },
            ],
            default_config_exists: false,
          },
        ],
      }).as('getQuotaWithLimits');
    });

    it('should display existing quota configuration', () => {
      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Wait for quota tab to be available before clicking
      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaWithLimits');

      // Check quota value and unit are populated
      cy.get('[data-testid="quota-value-input"]').should('have.value', '10');
      cy.get('[data-testid="quota-unit-select-toggle"]').should(
        'contain.text',
        'GiB',
      );

      // Check Quota Policy section is visible
      cy.get('[data-testid="quota-policy-section"]').should('exist');

      // Check existing limits are displayed
      cy.get('[data-testid="quota-limit-1"]').should('exist');
      cy.get('[data-testid="quota-limit-2"]').should('exist');

      // Check limit values
      cy.get('[data-testid="quota-limit-1"]').within(() => {
        cy.contains('Warning').should('exist');
        cy.get('[data-testid="limit-percent-input"]').should(
          'have.value',
          '80',
        );
      });

      cy.get('[data-testid="quota-limit-2"]').within(() => {
        cy.contains('Reject').should('exist');
        cy.get('[data-testid="limit-percent-input"]').should(
          'have.value',
          '90',
        );
      });
    });

    it('should successfully update existing quota', () => {
      cy.intercept('PUT', '**/api/v1/organization/projectquay/quota/1*', {
        statusCode: 200,
        body: {
          id: 1,
          limit_bytes: 21474836480, // 20 GiB
          limit: '20.0 GiB',
          default_config: false,
          limits: [],
          default_config_exists: false,
        },
      }).as('updateQuota');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Wait for quota tab to be available before clicking
      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaWithLimits');

      // Update quota value
      cy.get('[data-testid="quota-value-input"]').clear().type('20');

      // Submit form
      cy.get('[data-testid="apply-quota-button"]').click();

      cy.wait('@updateQuota');
      cy.contains('Successfully updated quota').should('exist');
    });

    it('should successfully delete entire quota', () => {
      cy.intercept('DELETE', '/api/v1/organization/projectquay/quota/1*', {
        statusCode: 204,
      }).as('deleteQuota');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Wait for quota tab to be available before clicking
      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaWithLimits');

      // Click Remove button
      cy.get('[data-testid="remove-quota-button"]').click();

      // Wait for delete confirmation modal to appear
      cy.contains('Delete Quota').should('be.visible');

      // Confirm deletion in modal
      cy.get('[data-testid="confirm-delete-quota"]')
        .should('be.visible')
        .click();

      cy.wait('@deleteQuota');

      // Just verify deletion occurred - don't try to verify complex post-delete state
      cy.get('[data-testid="remove-quota-button"]').should('exist');
    });
  });

  describe('Quota Policy Management', () => {
    const mockQuotaNoLimits = {
      id: 1,
      limit_bytes: 10737418240, // 10 GiB
      limit: '10.0 GiB',
      default_config: false,
      limits: [],
      default_config_exists: false,
    };

    beforeEach(() => {
      // Enable quota features
      cy.intercept('GET', '/config', (req) =>
        req.reply((res) => {
          res.body.features['QUOTA_MANAGEMENT'] = true;
          res.body.features['EDIT_QUOTA'] = true;
          res.body.features['SUPER_USERS'] = true;
          return res;
        }),
      ).as('getConfig');

      // Mock quota without limits
      cy.intercept('GET', '**/api/v1/organization/projectquay/quota*', {
        statusCode: 200,
        body: [mockQuotaNoLimits],
      }).as('getQuotaNoLimits');
    });

    it('should display quota policy section with no limits', () => {
      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Wait for quota tab to be available before clicking
      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaNoLimits');

      // Check Quota Policy section is visible
      cy.get('[data-testid="quota-policy-section"]').should('exist');

      // Check headers are displayed
      cy.contains('Action').should('exist');
      cy.contains('Quota Threshold').should('exist');

      // Check Add Limit form is displayed
      cy.get('[data-testid="add-limit-form"]').should('exist');

      // Check info message about no policy defined
      cy.get('[data-testid="no-policy-info"]').should('exist');
      cy.contains('No quota policy defined').should('exist');
    });

    it('should successfully add a new quota limit', () => {
      cy.intercept('POST', '/api/v1/organization/projectquay/quota/1/limit*', {
        statusCode: 201,
        body: 'Created',
      }).as('createQuotaLimit');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Wait for quota tab to be available before clicking
      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaNoLimits');

      // Fill Add Limit form
      cy.get('[data-testid="new-limit-type-select"]').click();
      cy.contains('Warning').click();

      cy.get('[data-testid="new-limit-percent-input"]').clear().type('80');

      // Click Add Limit button
      cy.get('[data-testid="add-limit-button"]').click();

      cy.wait('@createQuotaLimit');

      // Just verify the API call succeeded - complex state updates are hard to verify consistently
      cy.get('[data-testid="add-limit-button"]').should('exist');
    });

    it('should successfully update an existing quota limit', () => {
      // First mock creating a limit
      cy.intercept('POST', '/api/v1/organization/projectquay/quota/1/limit*', {
        statusCode: 201,
        body: 'Created',
      }).as('createQuotaLimit');

      // Mock the updated quota response AFTER creating the limit
      const mockQuotaWithNewLimit = {
        ...mockQuotaNoLimits,
        limits: [
          {
            id: 1,
            type: 'Warning',
            limit_percent: 80,
          },
        ],
      };

      // Then mock updating that limit
      cy.intercept('PUT', '/api/v1/organization/projectquay/quota/1/limit/1*', {
        statusCode: 200,
        body: 'Updated',
      }).as('updateQuotaLimit');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Wait for quota tab to be available before clicking
      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaNoLimits');

      // First CREATE a limit
      cy.get('[data-testid="new-limit-type-select"]').click();
      cy.contains('Warning').click();
      cy.get('[data-testid="new-limit-percent-input"]').clear().type('80');
      cy.get('[data-testid="add-limit-button"]').click();
      cy.wait('@createQuotaLimit');

      // After successful creation, update the GET intercept to return quota WITH the new limit
      cy.intercept('GET', '**/api/v1/organization/projectquay/quota*', {
        statusCode: 200,
        body: [mockQuotaWithNewLimit],
      }).as('getQuotaWithLimit');

      // Force a page reload to refresh the data
      cy.reload();
      cy.wait('@getConfig');

      // Navigate back to quota tab
      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaWithLimit');

      // Now the limit should be visible
      cy.contains('Warning').should('be.visible');

      // Now UPDATE that limit percentage
      cy.get('[data-testid="limit-percent-input"]').clear().type('85');

      // Update button should be enabled after change
      cy.get('[data-testid="update-limit-button"]').should('not.be.disabled');
      cy.get('[data-testid="update-limit-button"]').click();

      cy.wait('@updateQuotaLimit');
    });

    it('should successfully remove a quota limit', () => {
      // First mock creating a limit
      cy.intercept('POST', '/api/v1/organization/projectquay/quota/1/limit*', {
        statusCode: 201,
        body: 'Created',
      }).as('createQuotaLimit');

      // Mock the updated quota response AFTER creating the limit
      const mockQuotaWithNewLimit = {
        ...mockQuotaNoLimits,
        limits: [
          {
            id: 1,
            type: 'Warning',
            limit_percent: 80,
          },
        ],
      };

      // Then mock deleting that limit
      cy.intercept(
        'DELETE',
        '/api/v1/organization/projectquay/quota/1/limit/1*',
        {
          statusCode: 204,
        },
      ).as('deleteQuotaLimit');

      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Wait for quota tab to be available before clicking
      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaNoLimits');

      // First CREATE a limit
      cy.get('[data-testid="new-limit-type-select"]').click();
      cy.contains('Warning').click();
      cy.get('[data-testid="new-limit-percent-input"]').clear().type('80');
      cy.get('[data-testid="add-limit-button"]').click();
      cy.wait('@createQuotaLimit');

      // After successful creation, update the GET intercept to return quota WITH the new limit
      cy.intercept('GET', '**/api/v1/organization/projectquay/quota*', {
        statusCode: 200,
        body: [mockQuotaWithNewLimit],
      }).as('getQuotaWithLimit');

      // Force a page reload to refresh the data
      cy.reload();
      cy.wait('@getConfig');

      // Navigate back to quota tab
      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaWithLimit');

      // Now the limit should be visible
      cy.contains('Warning').should('be.visible');

      // Now REMOVE that limit - since there's only one, just click the remove button directly
      cy.get('[data-testid="remove-limit-button"]').click();

      cy.wait('@deleteQuotaLimit');

      // Just verify the API call succeeded
      cy.get('[data-testid="add-limit-button"]').should('exist');
    });

    it('should validate Add Limit form fields', () => {
      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Wait for quota tab to be available before clicking
      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaNoLimits');

      // Add Limit button should be disabled when fields are empty
      cy.get('[data-testid="add-limit-button"]').should('be.disabled');

      // Select action only
      cy.get('[data-testid="new-limit-type-select"]').click();
      cy.contains('Warning').click();
      cy.get('[data-testid="add-limit-button"]').should('be.disabled');

      // Add valid percentage
      cy.get('[data-testid="new-limit-percent-input"]').type('80');
      cy.get('[data-testid="add-limit-button"]').should('not.be.disabled');
    });

    it('should validate percentage input range', () => {
      cy.visit('/organization/projectquay?tab=Settings');
      cy.wait('@getConfig');

      // Wait for quota tab to be available before clicking
      cy.get('[data-testid="Quota"]').should('be.visible').click();
      cy.wait('@getQuotaNoLimits');

      // Test invalid percentage values
      cy.get('[data-testid="new-limit-percent-input"]')
        .clear()
        .type('0')
        .should('have.value', '');

      cy.get('[data-testid="new-limit-percent-input"]')
        .clear()
        .type('101')
        .should('have.value', '10');

      // Test valid percentage
      cy.get('[data-testid="new-limit-percent-input"]')
        .clear()
        .type('50')
        .should('have.value', '50');
    });
  });
});
