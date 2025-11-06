/// <reference types="cypress" />

describe('Superuser Framework', () => {
  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  describe('Feature Flag Behavior', () => {
    it('should hide superuser features when SUPERUSERS_FULL_ACCESS is disabled', () => {
      // Disable superuser features by creating modified config
      cy.fixture('config.json').then((baseConfig) => {
        const modifiedConfig = {...baseConfig};
        modifiedConfig.features = {...baseConfig.features};
        modifiedConfig.features['SUPERUSERS_FULL_ACCESS'] = false;
        modifiedConfig.features['SUPER_USERS'] = false;

        cy.intercept('GET', '/config', modifiedConfig).as(
          'getConfigNoSuperuser',
        );
      });

      // Mock superuser in user object but feature disabled
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'superuser.json',
      }).as('getSuperUser');

      cy.visit('/organization');
      cy.wait('@getConfigNoSuperuser');

      // Verify Superuser parent section does not exist when feature is disabled
      cy.get('[data-testid="superuser-nav"]').should('not.exist');

      // Verify organizations table has only 7 headers (no Actions column)
      cy.get('table thead tr th').should('have.length', 7);
    });

    it('should show superuser features when SUPERUSERS_FULL_ACCESS is enabled', () => {
      // Enable superuser features using config fixture
      cy.intercept('GET', '/config', {
        fixture: 'config.json',
      }).as('getConfigWithSuperuser');

      // Mock superuser in user object
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'superuser.json',
      }).as('getSuperUser');

      // Mock superuser organizations and users APIs
      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        fixture: 'superuser-organizations.json',
      }).as('getSuperuserOrgs');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getSuperuserUsers');

      // Mock organization details that the table will fetch
      cy.intercept('GET', '/api/v1/organization/testorg', {
        statusCode: 200,
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          teams: {owners: 'admin', developers: 'member'},
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

      // Mock robots/members for all organizations in the table
      cy.intercept('GET', '/api/v1/organization/testorg/robots', {
        statusCode: 200,
        body: {robots: []},
      }).as('getTestOrgRobots');

      cy.intercept('GET', '/api/v1/organization/testorg/members', {
        statusCode: 200,
        body: {members: []},
      }).as('getTestOrgMembers');

      cy.intercept('GET', '/api/v1/organization/projectquay/robots', {
        statusCode: 200,
        body: {robots: []},
      }).as('getProjectQuayRobots');

      cy.intercept('GET', '/api/v1/organization/projectquay/members', {
        statusCode: 200,
        body: {members: []},
      }).as('getProjectQuayMembers');

      cy.intercept('GET', '/api/v1/organization/coreos/robots', {
        statusCode: 200,
        body: {robots: []},
      }).as('getCoreosRobots');

      cy.intercept('GET', '/api/v1/organization/coreos/members', {
        statusCode: 200,
        body: {members: []},
      }).as('getCoreosMembers');

      // Mock repository endpoints for all orgs
      cy.intercept('GET', '/api/v1/repository?namespace=testorg', {
        statusCode: 200,
        body: {repositories: []},
      }).as('getTestOrgRepos');

      cy.intercept('GET', '/api/v1/repository?namespace=projectquay', {
        statusCode: 200,
        body: {repositories: []},
      }).as('getProjectQuayRepos');

      cy.intercept('GET', '/api/v1/repository?namespace=coreos', {
        statusCode: 200,
        body: {repositories: []},
      }).as('getCoreosRepos');

      cy.visit('/organization');
      cy.wait('@getConfigWithSuperuser');
      cy.wait('@getSuperUser');

      // Expand Superuser section first
      cy.contains('Superuser').click();

      // Verify superuser navigation items are visible within expanded section
      cy.get('[data-testid="service-keys-nav"]').should('exist');
      cy.get('[data-testid="change-log-nav"]').should('exist');
      cy.get('[data-testid="usage-logs-nav"]').should('exist');
      cy.get('[data-testid="messages-nav"]').should('exist');

      // Wait for all the organizations APIs that trigger table rendering
      cy.wait('@getSuperuserOrgs');
      cy.wait('@getSuperuserUsers');

      // Give React time to re-render the table with Actions column
      cy.get('table').should('exist');

      // Debug: Log what headers we actually see
      cy.get('table thead tr th').then(($headers) => {
        const headerTexts = Array.from($headers).map(
          (el) => el.textContent?.trim(),
        );
        cy.log('Current table headers:', headerTexts.join(', '));
        cy.log('Header count:', $headers.length);
      });

      // Verify we have 8 headers (includes Actions column)
      cy.get('table thead tr th').should('have.length', 8);

      // Verify the last header is "Settings" (Actions column)
      cy.get('table thead tr th').last().should('have.text', 'Settings');
    });
  });

  describe('Navigation Access Control', () => {
    it('should allow superusers to access all superuser pages', () => {
      // Enable superuser features
      cy.intercept('GET', '/config', {
        fixture: 'config.json',
      }).as('getConfig');

      // Mock superuser in user object
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'superuser.json',
      }).as('getSuperUser');

      // Mock API endpoints for each superuser page
      cy.intercept('GET', '/api/v1/superuser/keys', {
        statusCode: 200,
        body: {keys: []},
      }).as('getServiceKeys');

      cy.intercept('GET', '/api/v1/superuser/changelog', {
        statusCode: 200,
        body: {log: 'Sample change log content'},
      }).as('getChangeLog');

      cy.intercept('GET', '/api/v1/superuser/aggregatelogs*', {
        statusCode: 200,
        body: {aggregated: []},
      }).as('getUsageLogsChart');

      cy.intercept('GET', '/api/v1/superuser/logs*', {
        statusCode: 200,
        body: {logs: []},
      }).as('getUsageLogsTable');

      cy.intercept('GET', '/api/v1/messages', {
        statusCode: 200,
        body: [],
      }).as('getMessages');

      // Test Service Keys page
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getServiceKeys');
      cy.contains('Service Keys').should('exist');
      cy.get('h1').should('contain', 'Service Keys');

      // Test Change Log page
      cy.visit('/change-log');
      cy.wait('@getChangeLog');
      cy.contains('Change Log').should('exist');
      cy.get('h1').should('contain', 'Change Log');

      // Test Usage Logs page
      cy.visit('/usage-logs');
      cy.wait('@getUsageLogsChart');
      cy.wait('@getUsageLogsTable');
      cy.contains('Usage Logs').should('exist');
      cy.get('h1').should('contain', 'Usage Logs');

      // Test Messages page
      cy.visit('/messages');
      cy.wait('@getMessages');
      cy.contains('Messages').should('exist');
      cy.get('h1').should('contain', 'Messages');
    });

    it('should redirect non-superusers from superuser pages', () => {
      // Enable superuser features but mock regular user
      cy.intercept('GET', '/config', {
        fixture: 'config.json',
      }).as('getConfig');

      // Mock regular user (non-superuser)
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'user.json',
      }).as('getRegularUser');

      // Mock organizations and repositories for regular user
      cy.intercept('GET', '/api/v1/repository?namespace=*', {
        statusCode: 200,
        body: {repositories: []},
      }).as('getRepositories');

      // Test Service Keys redirect
      cy.visit('/service-keys');
      cy.wait('@getConfig');
      cy.wait('@getRegularUser');
      cy.url().should('include', '/organization');

      // Test Change Log redirect
      cy.visit('/change-log');
      cy.url().should('include', '/organization');

      // Test Usage Logs redirect
      cy.visit('/usage-logs');
      cy.url().should('include', '/repository');

      // Test Messages redirect
      cy.visit('/messages');
      cy.url().should('include', '/organization');
    });
  });

  describe('Organizations Table Superuser Features', () => {
    it('should show Actions column (empty header + action buttons) for superusers', () => {
      // Enable superuser features
      cy.intercept('GET', '/config', {
        fixture: 'config.json',
      }).as('getConfig');

      // Mock superuser
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'superuser.json',
      }).as('getSuperUser');

      // Mock superuser APIs
      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        fixture: 'superuser-organizations.json',
      }).as('getSuperuserOrgs');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getSuperuserUsers');

      // Mock organization details for each org in the table
      cy.intercept('GET', '/api/v1/organization/testorg', {
        statusCode: 200,
        body: {
          name: 'testorg',
          email: 'testorg@example.com',
          teams: {owners: 'admin', developers: 'member'},
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

      // Mock additional APIs that the organizations table needs
      cy.intercept('GET', '/api/v1/repository?namespace=testorg', {
        statusCode: 200,
        body: {repositories: []},
      }).as('getTestOrgRepos');

      cy.intercept('GET', '/api/v1/repository?namespace=projectquay', {
        statusCode: 200,
        body: {repositories: []},
      }).as('getProjectQuayRepos');

      cy.intercept('GET', '/api/v1/repository?namespace=coreos', {
        statusCode: 200,
        body: {repositories: []},
      }).as('getCoreosRepos');

      // Mock robots/members for all organizations in the table
      cy.intercept('GET', '/api/v1/organization/testorg/robots', {
        statusCode: 200,
        body: {robots: []},
      }).as('getTestOrgRobots');

      cy.intercept('GET', '/api/v1/organization/testorg/members', {
        statusCode: 200,
        body: {members: []},
      }).as('getTestOrgMembers');

      cy.intercept('GET', '/api/v1/organization/projectquay/robots', {
        statusCode: 200,
        body: {robots: []},
      }).as('getProjectQuayRobots');

      cy.intercept('GET', '/api/v1/organization/projectquay/members', {
        statusCode: 200,
        body: {members: []},
      }).as('getProjectQuayMembers');

      cy.intercept('GET', '/api/v1/organization/coreos/robots', {
        statusCode: 200,
        body: {robots: []},
      }).as('getCoreosRobots');

      cy.intercept('GET', '/api/v1/organization/coreos/members', {
        statusCode: 200,
        body: {members: []},
      }).as('getCoreosMembers');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getSuperuserOrgs');
      cy.wait('@getSuperuserUsers');

      // Wait for table to exist and render completely
      cy.get('table').should('exist');

      // Debug: Log what headers we actually see
      cy.get('table thead tr th').then(($headers) => {
        const headerTexts = Array.from($headers).map(
          (el) => el.textContent?.trim(),
        );
        cy.log('Current table headers:', headerTexts.join(', '));
        cy.log('Header count:', $headers.length);
      });

      // Verify we have 8 headers (includes Actions column)
      cy.get('table thead tr th').should('have.length', 8);

      // Verify the last header is "Settings" (Actions column)
      cy.get('table thead tr th').last().should('have.text', 'Settings');

      // Verify action buttons exist for organizations
      cy.get('[data-testid="testorg-options-toggle"]').should('exist');
      cy.get('[data-testid="projectquay-options-toggle"]').should('exist');

      // Test opening action menu
      cy.get('[data-testid="testorg-options-toggle"]').click();
      cy.contains('Rename Organization').should('exist');
      cy.contains('Delete Organization').should('exist');
      cy.contains('Take Ownership').should('exist');
    });

    it('should hide Actions column for non-superusers', () => {
      // Disable superuser features for regular user
      cy.fixture('config.json').then((baseConfig) => {
        const modifiedConfig = {...baseConfig};
        modifiedConfig.features = {...baseConfig.features};
        modifiedConfig.features['SUPERUSERS_FULL_ACCESS'] = false;
        modifiedConfig.features['SUPER_USERS'] = false;

        cy.intercept('GET', '/config', modifiedConfig).as('getConfig');
      });

      // Mock regular user
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'user.json',
      }).as('getRegularUser');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getRegularUser');

      // Verify Actions column doesn't exist
      cy.get('table thead th').should('not.contain', 'Actions');

      // Verify no action buttons exist
      cy.get('[data-testid*="-options-toggle"]').should('not.exist');
    });
  });

  describe('Superuser Navigation Visibility', () => {
    it('should show superuser navigation items for superusers', () => {
      // Enable superuser features
      cy.intercept('GET', '/config', {
        fixture: 'config.json',
      }).as('getConfig');

      // Mock superuser
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'superuser.json',
      }).as('getSuperUser');

      // Mock superuser APIs
      cy.intercept('GET', '/api/v1/superuser/organizations/', {
        fixture: 'superuser-organizations.json',
      }).as('getSuperuserOrgs');

      cy.intercept('GET', '/api/v1/superuser/users/', {
        fixture: 'superuser-users.json',
      }).as('getSuperuserUsers');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Verify Superuser parent is visible
      cy.contains('Superuser').should('be.visible');

      // Expand Superuser section
      cy.contains('Superuser').click();

      // Verify all child navigation items are visible
      cy.get('[data-testid="service-keys-nav"]').should('be.visible');
      cy.get('[data-testid="change-log-nav"]').should('be.visible');
      cy.get('[data-testid="usage-logs-nav"]').should('be.visible');
      cy.get('[data-testid="messages-nav"]').should('be.visible');

      // Test navigation links work
      cy.intercept('GET', '/api/v1/superuser/keys', {
        statusCode: 200,
        body: {keys: []},
      }).as('getServiceKeys');

      cy.get('[data-testid="service-keys-nav"]').click();
      cy.wait('@getServiceKeys');
      cy.url().should('include', '/service-keys');
    });

    it('should hide superuser navigation items for non-superusers', () => {
      // Disable superuser features
      cy.fixture('config.json').then((baseConfig) => {
        const modifiedConfig = {...baseConfig};
        modifiedConfig.features = {...baseConfig.features};
        modifiedConfig.features['SUPERUSERS_FULL_ACCESS'] = false;
        modifiedConfig.features['SUPER_USERS'] = false;

        cy.intercept('GET', '/config', modifiedConfig).as('getConfig');
      });

      // Mock regular user
      cy.intercept('GET', '/api/v1/user/', {
        fixture: 'user.json',
      }).as('getRegularUser');

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getRegularUser');

      // Verify Superuser parent section does not exist for non-superusers
      cy.contains('Superuser').should('not.exist');

      // Verify only standard navigation items are visible
      cy.contains('Organizations').should('be.visible');
      cy.contains('Repositories').should('be.visible');
    });
  });
});
