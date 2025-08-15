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
      cy.get('table thead tr th').last().should('have.text', ''); // Empty header

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
  });
});
