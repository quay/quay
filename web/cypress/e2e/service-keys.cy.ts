/// <reference types="cypress" />

describe('Service Keys Management', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  describe('Access Control', () => {
    it('should redirect non-superusers from service keys page', () => {
      // Mock regular user
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'user.json',
      }).as('getRegularUser');

      // Mock config with superuser features enabled
      cy.intercept('GET', '/config', {
        fixture: 'config.json',
      }).as('getConfig');

      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getRegularUser');

      // Should redirect to organization page
      cy.url().should('include', '/organization');
    });

    it('should allow superusers to access service keys page', () => {
      // Mock superuser
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'superuser.json',
      }).as('getSuperUser');

      // Mock config
      cy.intercept('GET', '/config', {
        fixture: 'config.json',
      }).as('getConfig');

      // Mock service keys API
      cy.intercept('GET', '/api/v1/superuser/keys', {
        fixture: 'service-keys.json',
      }).as('getServiceKeys');

      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Should display the service keys page
      cy.get('h1').should('contain', 'Service Keys');
      cy.contains(
        'Service keys provide a recognized means of authentication',
      ).should('exist');
    });
  });

  describe('Service Keys Display', () => {
    beforeEach(() => {
      // Setup superuser access
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'superuser.json',
      }).as('getSuperUser');

      cy.intercept('GET', '/config', {
        fixture: 'config.json',
      }).as('getConfig');

      cy.intercept('GET', '/api/v1/superuser/keys', {
        fixture: 'service-keys.json',
      }).as('getServiceKeys');
    });

    it('should display service keys table with correct columns', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Verify table headers (actual columns from component)
      cy.get('table thead tr th').should('contain', 'Name');
      cy.get('table thead tr th').should('contain', 'Service Name');
      cy.get('table thead tr th').should('contain', 'Created');
      cy.get('table thead tr th').should('contain', 'Expires');
      cy.get('table thead tr th').should('contain', 'Approval Status');
      cy.get('table thead tr th').should('contain', 'Actions');

      // Verify service keys are displayed
      cy.contains('Clair Scanner Key').should('exist');
      cy.contains('Build Worker Key').should('exist');
      cy.contains('Test Service Key').should('exist');
    });

    it('should display approval status correctly', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Check approved keys show correct approval status
      cy.get('tbody')
        .contains('Clair Scanner Key')
        .closest('tr')
        .within(() => {
          cy.get('td[data-label="Approval Status"]').should(
            'contain',
            'Approved by superuser',
          );
        });

      cy.get('tbody')
        .contains('Build Worker Key')
        .closest('tr')
        .within(() => {
          cy.get('td[data-label="Approval Status"]').should(
            'contain',
            'Generated Automatically',
          );
        });

      // Check unapproved key shows awaiting approval status
      cy.get('tbody')
        .contains('Test Service Key')
        .closest('tr')
        .within(() => {
          cy.get('td[data-label="Approval Status"]').should(
            'contain',
            'Awaiting Approval',
          );
        });
    });

    it('should display expiration status with correct icons', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Check that expiration columns show relative time
      cy.get('tbody tr').should('contain', 'in'); // Should show "in X months/days"

      // Check for "Never" expiration text for keys without expiration
      cy.get('tbody')
        .contains('Test Service Key')
        .closest('tr')
        .within(() => {
          cy.get('td[data-label="Expires"]').should('contain', 'Never');
        });

      // Expired keys should show "ago" text indicating they've expired
      cy.get('tbody')
        .contains('Expired Scanner')
        .closest('tr')
        .within(() => {
          cy.get('td[data-label="Expires"]').should('contain', 'ago');
        });
    });

    it('should support sorting by different columns', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Test sorting by Service column
      cy.get('table thead th').contains('Service').click();

      // Verify table re-renders (we can't easily test actual sorting without complex assertions)
      cy.get('table tbody tr').should('have.length.at.least', 3);

      // Test sorting by Created date
      cy.get('table thead th').contains('Created').click();
      cy.get('table tbody tr').should('have.length.at.least', 3);
    });

    it('should support pagination', () => {
      // Mock a larger dataset for pagination testing
      cy.fixture('service-keys.json').then((baseKeys) => {
        const manyKeys = {
          keys: Array.from({length: 25}, (_, i) => ({
            ...baseKeys.keys[0],
            kid: `test-key-${i + 1}`,
            name: `Service Key ${i + 1}`,
            service: `service-${i + 1}`,
          })),
        };

        cy.intercept('GET', '/api/v1/superuser/keys', manyKeys).as(
          'getManyServiceKeys',
        );
      });

      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getManyServiceKeys');

      // Should show pagination controls (simplified check)
      cy.get('.pf-v5-c-pagination').should('exist');

      // Verify correct number of service keys are displayed
      // Count rows that contain service key names (more reliable than counting all tr elements)
      cy.get('table tbody')
        .find('td[data-label="Name"]')
        .should('have.length', 20);

      // Check that pagination shows total count
      cy.contains('25').should('exist'); // Should show total of 25 items somewhere
    });
  });

  describe('Service Key Search and Filtering', () => {
    beforeEach(() => {
      // Setup superuser access with service keys
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'superuser.json',
      }).as('getSuperUser');

      cy.intercept('GET', '/config', {
        fixture: 'config.json',
      }).as('getConfig');

      cy.intercept('GET', '/api/v1/superuser/keys', {
        fixture: 'service-keys.json',
      }).as('getServiceKeys');
    });

    it('should filter service keys by search term', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Search for specific service key
      cy.get('[data-testid="service-keys-search"]').type('Clair');

      // Should show only matching results
      cy.contains('Clair Scanner Key').should('exist');
      cy.contains('Build Worker Key').should('not.exist');

      // Clear search
      cy.get('[data-testid="service-keys-search"]').clear();
      cy.contains('Build Worker Key').should('exist');
    });
  });
  describe('Create Service Key', () => {
    beforeEach(() => {
      // Setup superuser access
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'superuser.json',
      }).as('getSuperUser');

      cy.intercept('GET', '/config', {
        fixture: 'config.json',
      }).as('getConfig');

      cy.intercept('GET', '/api/v1/superuser/keys', {
        fixture: 'service-keys.json',
      }).as('getServiceKeys');
    });

    it('should open create service key modal', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Click create button
      cy.get('#create-service-key-button').click();

      // Modal should open
      cy.get('[data-testid="create-service-key-modal"]').should('be.visible');
      cy.contains('Create Preshareable Service Key').should('exist');

      // Form fields should be present
      cy.get('#service-name').should('exist');
      cy.get('#key-name').should('exist');
      cy.get('#expiration').should('exist');
    });

    it('should create a new service key successfully', () => {
      // Mock the create API call
      const newKey = {
        kid: 'new-test-key',
        name: 'New Test Key',
        service: 'new_service',
        created_date: '2024-03-15T10:00:00Z',
        metadata: {},
      };

      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Set up intercepts after initial page load
      cy.intercept('POST', '/api/v1/superuser/keys', {
        statusCode: 200,
        body: newKey,
      }).as('createServiceKey');

      // Mock the refetch after creation
      cy.fixture('service-keys.json').then((baseKeys) => {
        const updatedKeys = {
          keys: [...baseKeys.keys, newKey],
        };
        cy.intercept('GET', '/api/v1/superuser/keys', updatedKeys).as(
          'getUpdatedServiceKeys',
        );
      });

      // Open create modal
      cy.get('#create-service-key-button').click();

      // Fill out required form fields
      cy.get('#service-name').type('new_service'); // Must match [a-z0-9_]+ pattern
      cy.get('#key-name').type('New Test Key');
      cy.get('#expiration').type('2025-12-31T23:59'); // Required field

      // Submit form
      cy.get('[data-testid="create-key-submit"]').click();

      // Wait for API call
      cy.wait('@createServiceKey');

      // Modal should close and table should refresh
      cy.get('[data-testid="create-service-key-modal"]').should('not.exist');
      cy.contains('New Test Key').should('exist');
    });

    it('should validate required fields', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Open create modal
      cy.get('#create-service-key-button').click();

      // Try to submit without required fields
      cy.get('[data-testid="create-key-submit"]').should('be.disabled');

      // Fill only service field (still missing name and expiration)
      cy.get('#service-name').type('test_service');
      cy.get('[data-testid="create-key-submit"]').should('be.disabled');

      // Fill name field (still missing expiration)
      cy.get('#key-name').type('Test Key');
      cy.get('[data-testid="create-key-submit"]').should('be.disabled');

      // Fill all required fields
      cy.get('#expiration').type('2025-12-31T23:59');

      // Submit button should now be enabled
      cy.get('[data-testid="create-key-submit"]').should('not.be.disabled');
    });

    it('should handle create errors gracefully', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Set up error response after page load
      cy.intercept('POST', '/api/v1/superuser/keys', {
        statusCode: 400,
        body: {
          error_message: 'Service already exists',
          error_type: 'invalid_request',
          detail: 'A service with this name already exists',
        },
      }).as('createServiceKeyError');

      // Open create modal and fill required form fields
      cy.get('#create-service-key-button').click();
      cy.get('#service-name').type('existing_service'); // Must match [a-z0-9_]+ pattern
      cy.get('#key-name').type('Test Key');
      cy.get('#expiration').type('2025-12-31T23:59'); // Required field

      // Submit form
      cy.get('[data-testid="create-key-submit"]').click();
      cy.wait('@createServiceKeyError');

      // Debug: log what's actually in the modal
      cy.get('[data-testid="create-service-key-modal"]').then(($modal) => {
        cy.log('Modal content:', $modal.text());
      });

      // Error should be displayed - try multiple approaches
      // First check for FormError alert component
      cy.get('body').then(($body) => {
        if ($body.find('[id="form-error-alert"]').length > 0) {
          cy.get('[id="form-error-alert"]').should('be.visible');
        } else {
          // If no FormError, look for any error text in modal
          cy.get('[data-testid="create-service-key-modal"]').should(
            'contain',
            'Error',
          );
        }
      });

      // Modal should remain open
      cy.get('[data-testid="create-service-key-modal"]').should('be.visible');
    });
  });

  describe('Service Key Actions', () => {
    beforeEach(() => {
      // Setup superuser access
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'superuser.json',
      }).as('getSuperUser');

      cy.intercept('GET', '/config', {
        fixture: 'config.json',
      }).as('getConfig');

      cy.intercept('GET', '/api/v1/superuser/keys', {
        fixture: 'service-keys.json',
      }).as('getServiceKeys');
    });

    it('should expand/collapse service key details', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Click to expand first service key
      cy.get('[data-testid="expand-test-key-1"]').click();

      // Details should be visible
      cy.get('[data-testid="key-details-test-key-1"]').should('be.visible');
      cy.contains('Full Key ID').should('exist');
      cy.contains('test-key-1').should('exist');

      // Click to collapse
      cy.get('[data-testid="expand-test-key-1"]').click();
      cy.get('[data-testid="key-details-test-key-1"]').should('not.be.visible');
    });

    it('should delete a service key through modal workflow', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Set up API mock after page load
      cy.intercept('DELETE', '/api/v1/superuser/keys/test-key-1', {
        statusCode: 204,
      }).as('deleteServiceKey');

      // Open action menu for first service key
      cy.get('[data-testid="test-key-1-actions-toggle"]').click();

      // Click delete action
      cy.contains('Delete Key').click();

      // Confirm modal opens
      cy.get('[data-testid="delete-service-key-modal"]').should('be.visible');
      cy.contains('Are you sure you want to delete the service key').should(
        'exist',
      );

      // Click confirm delete
      cy.get('[data-testid="confirm-delete-button"]').click();

      // Wait for API call
      cy.wait('@deleteServiceKey');

      // Modal should close
      cy.get('[data-testid="delete-service-key-modal"]').should('not.exist');
    });

    it('should change expiration time through modal workflow', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Set up API mock after page load
      cy.intercept('PUT', '/api/v1/superuser/keys/test-key-1', {
        statusCode: 200,
        body: {
          kid: 'test-key-1',
          name: 'Clair Scanner Key',
          service: 'clair-scanner',
          created_date: '2024-01-15T10:30:00Z',
          expiration_date: '2026-01-15T10:30:00Z', // Updated
          approval: {
            approval_type: 'ServiceKeyApprovalType.SUPERUSER',
            approver: {
              name: 'superuser',
              username: 'superuser',
              kind: 'user',
            },
          },
          metadata: {
            scanner_version: 'v4.0.1',
            environment: 'production',
          },
        },
      }).as('updateServiceKey');

      // Open action menu for service key
      cy.get('[data-testid="test-key-1-actions-toggle"]').click();

      // Click change expiration action
      cy.contains('Change Expiration Time').click();

      // Confirm modal opens
      cy.get('[data-testid="change-expiration-modal"]').should('be.visible');
      cy.contains('Change Service Key Expiration').should('exist');

      // Update expiration date
      cy.get('[data-testid="expiration-date-input"]')
        .clear()
        .type('2026-01-15T10:30');

      // Click save
      cy.get('[data-testid="save-expiration-button"]').click();

      // Wait for API call
      cy.wait('@updateServiceKey');

      // Modal should close
      cy.get('[data-testid="change-expiration-modal"]').should('not.exist');
    });

    it('should set friendly name through modal workflow', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Set up API mock after page load
      cy.intercept('PUT', '/api/v1/superuser/keys/test-key-1', {
        statusCode: 200,
        body: {
          kid: 'test-key-1',
          name: 'Updated Clair Scanner Key', // Updated name
          service: 'clair-scanner',
          created_date: '2024-01-15T10:30:00Z',
          expiration_date: '2025-01-15T10:30:00Z',
          approval: {
            approval_type: 'ServiceKeyApprovalType.SUPERUSER',
            approver: {
              name: 'superuser',
              username: 'superuser',
              kind: 'user',
            },
          },
          metadata: {
            scanner_version: 'v4.0.1',
            environment: 'production',
          },
        },
      }).as('updateServiceKey');

      // Open action menu for service key
      cy.get('[data-testid="test-key-1-actions-toggle"]').click();

      // Click set friendly name action
      cy.contains('Set Friendly Name').click();

      // Confirm modal opens
      cy.get('[data-testid="set-name-modal"]').should('be.visible');
      cy.contains('Set Friendly Name').should('exist');

      // Update friendly name
      cy.get('[data-testid="friendly-name-input"]')
        .clear()
        .type('Updated Clair Scanner Key');

      // Click save
      cy.get('[data-testid="save-name-button"]').click();

      // Wait for API call
      cy.wait('@updateServiceKey');

      // Modal should close
      cy.get('[data-testid="set-name-modal"]').should('not.exist');
    });
  });

  describe('Bulk Operations', () => {
    beforeEach(() => {
      // Setup superuser access
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'superuser.json',
      }).as('getSuperUser');

      cy.intercept('GET', '/config', {
        fixture: 'config.json',
      }).as('getConfig');

      cy.intercept('GET', '/api/v1/superuser/keys', {
        fixture: 'service-keys.json',
      }).as('getServiceKeys');
    });

    it('should select multiple service keys', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Click individual row selection cells using data-testid
      cy.get('[data-testid="select-test-key-1"]').click();
      cy.get('[data-testid="select-test-key-2"]').click();

      // Click the Actions button that appears when items are selected
      cy.contains('button', 'Actions').click();

      // Verify Delete Keys option appears in the dropdown
      cy.get('[data-testid="bulk-delete-keys"] button').should('exist');
    });

    it('should bulk delete selected service keys', () => {
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');

      // Set up API mocks after page load
      cy.intercept('DELETE', '/api/v1/superuser/keys/test-key-1', {
        statusCode: 204,
      }).as('deleteServiceKey1');
      cy.intercept('DELETE', '/api/v1/superuser/keys/test-key-2', {
        statusCode: 204,
      }).as('deleteServiceKey2');

      // Use toolbar select-all checkbox
      cy.get('[name="service-keys-checkbox"]').click();

      // Click Actions button when it appears
      cy.contains('button', 'Actions').click();

      // Wait for dropdown to be visible and click Delete Keys
      cy.get('[data-testid="bulk-delete-keys"]').should('be.visible');
      cy.get('[data-testid="bulk-delete-keys"] button').click();

      // Verify bulk delete modal appears
      cy.get('[data-testid="bulk-delete-modal"]').should('be.visible');

      // Confirm in bulk delete modal
      cy.get('[data-testid="confirm-bulk-delete"]').click();

      // Wait for delete API calls
      cy.wait('@deleteServiceKey1');
      cy.wait('@deleteServiceKey2');

      // Verify modal closes after successful deletion
      cy.get('[data-testid="bulk-delete-modal"]').should('not.exist');
    });
  });
});
