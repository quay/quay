/// <reference types="cypress" />

describe('Superuser Organization Actions', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  describe('Access Control', () => {
    it('should only show actions for non-superusers', () => {
      // Mock regular user (non-superuser)
      cy.fixture('config.json').then((config) => {
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

      // Should not show Actions column for non-superusers
      cy.get('table thead tr th').should('have.length', 7); // No Actions column
    });

    it('should show actions for superusers', () => {
      // Mock superuser
      cy.fixture('config.json').then((config) => {
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

      // Mock individual organization data (like superuser-framework does)
      cy.intercept('GET', '/api/v1/organization/testorg', {
        statusCode: 200,
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          teams: {owners: 'admin'},
        },
      }).as('getTestOrg');

      cy.intercept('GET', '/api/v1/organization/projectquay', {
        statusCode: 200,
        body: {
          name: 'projectquay',
          email: 'projectquay@example.com',
          teams: {},
        },
      }).as('getProjectQuayOrg');

      cy.intercept('GET', '/api/v1/organization/coreos', {
        statusCode: 200,
        body: {
          name: 'coreos',
          email: 'coreos@example.com',
          teams: {owners: 'admin'},
        },
      }).as('getCoreosOrg');

      // Mock robots/members for all organizations
      cy.intercept('GET', '/api/v1/organization/*/robots', {
        statusCode: 200,
        body: {robots: []},
      });

      cy.intercept('GET', '/api/v1/organization/*/members', {
        statusCode: 200,
        body: {members: []},
      });

      // Mock repository data
      cy.intercept('GET', '/api/v1/repository?namespace=*', {
        statusCode: 200,
        body: {repositories: []},
      });

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Should show Actions column for superusers
      cy.get('table thead tr th').should('have.length', 8); // With Actions column
      cy.get('table thead tr th').last().should('have.text', 'Settings'); // Settings header

      // Should show action buttons for organizations
      cy.get('[data-testid="testorg-options-toggle"]').should('exist');
      cy.get('[data-testid="projectquay-options-toggle"]').should('exist');
      cy.get('[data-testid="coreos-options-toggle"]').should('exist');
    });
  });

  describe('Rename Organization', () => {
    beforeEach(() => {
      // Setup superuser access with full mocking like superuser-framework
      cy.fixture('config.json').then((config) => {
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

      // Mock all the detailed organization data
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

      cy.intercept('GET', '/api/v1/organization/coreos', {
        statusCode: 200,
        body: {
          name: 'coreos',
          email: 'coreos@example.com',
          teams: {owners: 'admin'},
        },
      });

      cy.intercept('GET', '/api/v1/organization/*/robots', {
        statusCode: 200,
        body: {robots: []},
      });
      cy.intercept('GET', '/api/v1/organization/*/members', {
        statusCode: 200,
        body: {members: []},
      });
      cy.intercept('GET', '/api/v1/repository?namespace=*', {
        statusCode: 200,
        body: {repositories: []},
      });
    });

    it('should open rename modal and rename organization', () => {
      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Set up API mock after page load
      cy.intercept('PUT', '/api/v1/superuser/organizations/testorg', {
        statusCode: 200,
      }).as('renameOrganization');

      // Click action menu for testorg
      cy.get('[data-testid="testorg-options-toggle"]').click();

      // Click Rename Organization
      cy.contains('Rename Organization').click();

      // Should open rename modal
      cy.get('[role="dialog"]').should('exist');
      cy.contains('Rename Organization').should('exist');
      cy.get('#new-organization-name').should('exist');

      // Fill in new name
      cy.get('#new-organization-name').type('testorg-renamed');

      // Submit form
      cy.get('button').contains('OK').click();

      // Wait for API call
      cy.wait('@renameOrganization').then((interception) => {
        expect(interception.request.body.name).to.equal('testorg-renamed');
      });

      // Modal should close
      cy.get('[role="dialog"]').should('not.exist');
    });

    it('should validate empty organization name', () => {
      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Click action menu for testorg
      cy.get('[data-testid="testorg-options-toggle"]').click();

      // Click Rename Organization
      cy.contains('Rename Organization').click();

      // Should open rename modal
      cy.get('[role="dialog"]').should('exist');

      // OK button should be disabled when field is empty
      cy.get('button').contains('OK').should('be.disabled');

      // Add text, button should be enabled
      cy.get('#new-organization-name').type('new-name');
      cy.get('button').contains('OK').should('not.be.disabled');

      // Clear text, button should be disabled again
      cy.get('#new-organization-name').clear();
      cy.get('button').contains('OK').should('be.disabled');
    });

    it('should show password verification when fresh login is required', () => {
      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');
      cy.wait('@getSuperuserUsers');

      // First attempt returns fresh_login_required error
      cy.intercept('PUT', '/api/v1/superuser/organizations/testorg', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_message: 'Fresh login required',
        },
      }).as('renameRequiresFresh');

      // Click action menu for testorg
      cy.get('[data-testid="testorg-options-toggle"]').click();

      // Click Rename Organization
      cy.contains('Rename Organization').click();

      // Should open rename modal
      cy.get('[role="dialog"]').should('exist');
      cy.contains('Rename Organization').should('exist');

      // Fill in new name
      cy.get('#new-organization-name').type('testorg-renamed');

      // Submit form
      cy.get('button').contains('OK').click();

      // Wait for the fresh login required response
      cy.wait('@renameRequiresFresh');

      // Should show fresh login modal
      cy.contains('Please Verify').should('exist');
      cy.contains(
        'It has been more than a few minutes since you last logged in',
      ).should('exist');
      cy.get('#fresh-password').should('exist');

      // Mock successful password verification
      cy.intercept('POST', '/api/v1/signin/verify', {
        statusCode: 200,
        body: {success: true},
      }).as('verifyPassword');

      // Mock successful rename after verification
      cy.intercept('PUT', '/api/v1/superuser/organizations/testorg', {
        statusCode: 200,
      }).as('renameSuccess');

      // Enter password and verify
      cy.get('#fresh-password').type('password');
      cy.get('button').contains('Verify').click();

      // Wait for verification
      cy.wait('@verifyPassword');

      // Should retry rename and succeed
      cy.wait('@renameSuccess');

      // Fresh login modal should close
      cy.contains('Please Verify').should('not.exist');
    });
  });

  describe('Delete Organization', () => {
    beforeEach(() => {
      // Setup superuser access with full mocking
      cy.fixture('config.json').then((config) => {
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

      // Mock all the detailed organization data
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

      cy.intercept('GET', '/api/v1/organization/coreos', {
        statusCode: 200,
        body: {
          name: 'coreos',
          email: 'coreos@example.com',
          teams: {owners: 'admin'},
        },
      });

      cy.intercept('GET', '/api/v1/organization/*/robots', {
        statusCode: 200,
        body: {robots: []},
      });
      cy.intercept('GET', '/api/v1/organization/*/members', {
        statusCode: 200,
        body: {members: []},
      });
      cy.intercept('GET', '/api/v1/repository?namespace=*', {
        statusCode: 200,
        body: {repositories: []},
      });
    });

    it('should open delete modal and delete organization', () => {
      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Set up API mock after page load
      cy.intercept('DELETE', '/api/v1/superuser/organizations/testorg', {
        statusCode: 204,
      }).as('deleteOrganization');

      // Click action menu for testorg
      cy.get('[data-testid="testorg-options-toggle"]').click();

      // Click Delete Organization
      cy.contains('Delete Organization').click();

      // Should open delete confirmation modal
      cy.get('[role="dialog"]').should('exist');
      cy.contains('Delete Organization').should('exist');
      cy.contains('Are you sure you want to delete this organization').should(
        'exist',
      );

      // Confirm deletion
      cy.get('button').contains('OK').click();

      // Wait for API call
      cy.wait('@deleteOrganization');

      // Modal should close
      cy.get('[role="dialog"]').should('not.exist');
    });

    it('should show password verification when fresh login is required', () => {
      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');
      cy.wait('@getSuperuserUsers');

      // First attempt returns fresh_login_required error
      cy.intercept('DELETE', '/api/v1/superuser/organizations/testorg', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_message: 'Fresh login required',
        },
      }).as('deleteRequiresFresh');

      // Click action menu for testorg
      cy.get('[data-testid="testorg-options-toggle"]').click();

      // Click Delete Organization
      cy.contains('Delete Organization').click();

      // Should open delete confirmation modal
      cy.get('[role="dialog"]').should('exist');
      cy.contains('Delete Organization').should('exist');

      // Confirm deletion
      cy.get('button').contains('OK').click();

      // Wait for the fresh login required response
      cy.wait('@deleteRequiresFresh');

      // Should show fresh login modal
      cy.contains('Please Verify').should('exist');
      cy.contains(
        'It has been more than a few minutes since you last logged in',
      ).should('exist');
      cy.get('#fresh-password').should('exist');

      // Mock successful password verification
      cy.intercept('POST', '/api/v1/signin/verify', {
        statusCode: 200,
        body: {success: true},
      }).as('verifyPassword');

      // Mock successful delete after verification
      cy.intercept('DELETE', '/api/v1/superuser/organizations/testorg', {
        statusCode: 204,
      }).as('deleteSuccess');

      // Enter password and verify
      cy.get('#fresh-password').type('password');
      cy.get('button').contains('Verify').click();

      // Wait for verification
      cy.wait('@verifyPassword');

      // Should retry delete and succeed
      cy.wait('@deleteSuccess');

      // Fresh login modal should close
      cy.contains('Please Verify').should('not.exist');
    });
  });

  describe('Take Ownership', () => {
    beforeEach(() => {
      // Setup superuser access with full mocking
      cy.fixture('config.json').then((config) => {
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

      // Mock all the detailed organization data
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

      cy.intercept('GET', '/api/v1/organization/coreos', {
        statusCode: 200,
        body: {
          name: 'coreos',
          email: 'coreos@example.com',
          teams: {owners: 'admin'},
        },
      });

      cy.intercept('GET', '/api/v1/organization/*/robots', {
        statusCode: 200,
        body: {robots: []},
      });
      cy.intercept('GET', '/api/v1/organization/*/members', {
        statusCode: 200,
        body: {members: []},
      });
      cy.intercept('GET', '/api/v1/repository?namespace=*', {
        statusCode: 200,
        body: {repositories: []},
      });
    });

    it('should open take ownership modal for organization', () => {
      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Set up API mock after page load
      cy.intercept('POST', '/api/v1/superuser/takeownership/testorg', {
        statusCode: 200,
      }).as('takeOwnership');

      // Click action menu for testorg
      cy.get('[data-testid="testorg-options-toggle"]').click();

      // Click Take Ownership
      cy.contains('Take Ownership').click();

      // Should open take ownership modal
      cy.get('[role="dialog"]').should('exist');
      cy.contains('Take Ownership').should('exist');
      cy.contains(
        'Are you sure you want to take ownership of organization',
      ).should('exist');
      cy.contains('testorg').should('exist');

      // Confirm take ownership
      cy.get('button').contains('Take Ownership').click();

      // Wait for API call
      cy.wait('@takeOwnership');
    });

    it('should show password verification when fresh login is required', () => {
      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // First attempt returns fresh_login_required error
      cy.intercept('POST', '/api/v1/superuser/takeownership/testorg', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_message: 'Fresh login required',
        },
      }).as('takeOwnershipRequiresFresh');

      // Click action menu for testorg
      cy.get('[data-testid="testorg-options-toggle"]').click();

      // Click Take Ownership
      cy.contains('Take Ownership').click();

      // Should open take ownership modal
      cy.get('[role="dialog"]').should('exist');
      cy.contains('Take Ownership').should('exist');

      // Confirm take ownership
      cy.get('button').contains('Take Ownership').click();

      // Wait for the fresh login required response
      cy.wait('@takeOwnershipRequiresFresh');

      // Should show fresh login modal instead of error
      cy.contains('Please Verify').should('exist');
      cy.contains(
        'It has been more than a few minutes since you last logged in',
      ).should('exist');
      cy.get('#fresh-password').should('exist');

      // Mock successful password verification
      cy.intercept('POST', '/api/v1/signin/verify', {
        statusCode: 200,
        body: {success: true},
      }).as('verifyPassword');

      // Mock successful take ownership after verification
      cy.intercept('POST', '/api/v1/superuser/takeownership/testorg', {
        statusCode: 200,
      }).as('takeOwnershipSuccess');

      // Enter password and verify
      cy.get('#fresh-password').type('password');
      cy.get('button').contains('Verify').click();

      // Wait for verification
      cy.wait('@verifyPassword');

      // Should retry take ownership and succeed
      cy.wait('@takeOwnershipSuccess');

      // Fresh login modal should close
      cy.contains('Please Verify').should('not.exist');
    });
  });

  describe('Configure Quota - Phase 3', () => {
    beforeEach(() => {
      // Setup superuser access with full mocking + quota features enabled
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        config.features.QUOTA_MANAGEMENT = true;
        config.features.EDIT_QUOTA = true;
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

      // Mock organization data
      cy.intercept('GET', '/api/v1/organization/testorg', {
        statusCode: 200,
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          teams: {owners: 'admin'},
        },
      });

      cy.intercept('GET', '/api/v1/organization/*/robots', {
        statusCode: 200,
        body: {robots: []},
      });
      cy.intercept('GET', '/api/v1/organization/*/members', {
        statusCode: 200,
        body: {members: []},
      });
      cy.intercept('GET', '/api/v1/repository?namespace=*', {
        statusCode: 200,
        body: {repositories: []},
      });

      // Mock quota endpoint (no quota initially)
      cy.intercept('GET', '/api/v1/organization/testorg/quota*', {
        statusCode: 200,
        body: [],
      }).as('getOrgQuota');
    });

    it('should show Configure Quota option for organizations', () => {
      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Click action menu for organization
      cy.get('[data-testid="testorg-options-toggle"]').click();

      // Should see Configure Quota option
      cy.contains('Configure Quota').should('be.visible');
    });

    it('should open Configure Quota modal for organization', () => {
      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Click action menu
      cy.get('[data-testid="testorg-options-toggle"]').click();

      // Click Configure Quota
      cy.contains('Configure Quota').click();

      // Modal should open with correct title
      cy.get('[data-testid="configure-quota-modal"]').should('be.visible');
      cy.contains('Configure Quota for testorg').should('be.visible');
    });

    it('should NOT show Configure Quota when feature flags are disabled', () => {
      // Disable quota features
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        config.features.QUOTA_MANAGEMENT = false;
        config.features.EDIT_QUOTA = false;
        cy.intercept('GET', '/config', config).as('getConfigNoQuota');
      });

      cy.visit('/organization');
      cy.wait('@getConfigNoQuota');
      cy.wait('@getSuperUser');

      // Click action menu for organization
      cy.get('[data-testid="testorg-options-toggle"]').click();

      // Configure Quota should NOT appear
      cy.contains('Configure Quota').should('not.exist');
    });

    it('should show password verification when fresh login is required', () => {
      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrganizations');
      cy.wait('@getSuperuserUsers');

      // Click action menu
      cy.get('[data-testid="testorg-options-toggle"]').click();

      // Click Configure Quota
      cy.contains('Configure Quota').click();

      // Modal should open
      cy.get('[data-testid="configure-quota-modal"]').should('be.visible');

      // Enter quota value
      cy.get('[data-testid="quota-value-input"]').clear().type('100');

      // First attempt returns fresh_login_required error
      cy.intercept('POST', '/api/v1/organization/testorg/quota', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          error_message: 'Fresh login required',
        },
      }).as('createQuotaRequiresFresh');

      // Submit quota
      cy.get('[data-testid="apply-quota-button"]').click();

      // Wait for the fresh login required response
      cy.wait('@createQuotaRequiresFresh');

      // Should show fresh login modal
      cy.contains('Please Verify').should('exist');
      cy.contains(
        'It has been more than a few minutes since you last logged in',
      ).should('exist');
      cy.get('#fresh-password').should('exist');

      // Mock successful password verification
      cy.intercept('POST', '/api/v1/signin/verify', {
        statusCode: 200,
        body: {success: true},
      }).as('verifyPassword');

      // Mock successful quota creation after verification
      cy.intercept('POST', '/api/v1/organization/testorg/quota', {
        statusCode: 201,
        body: {
          id: '123',
          limit_bytes: 107374182400,
          limits: [],
        },
      }).as('createQuotaSuccess');

      // Enter password and verify
      cy.get('#fresh-password').type('password');
      cy.get('button').contains('Verify').click();

      // Wait for verification
      cy.wait('@verifyPassword');

      // Should retry quota creation and succeed
      cy.wait('@createQuotaSuccess');

      // Fresh login modal should close
      cy.contains('Please Verify').should('not.exist');
    });
  });
});
