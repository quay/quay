/// <reference types="cypress" />

describe('Superuser Usage Logs', () => {
  const superuserLogsResp = {
    logs: [
      {
        kind: 'org_create',
        metadata: {namespace: 'testorg1'},
        ip: '192.168.1.1',
        datetime: '2024-01-15T10:30:00Z',
        performer: {name: 'superuser', kind: 'user'},
      },
      {
        kind: 'user_create',
        metadata: {username: 'newuser'},
        ip: '192.168.1.2',
        datetime: '2024-01-14T15:20:00Z',
        performer: {name: 'admin', kind: 'user'},
      },
      {
        kind: 'create_repo',
        metadata: {repo: 'testrepo', namespace: 'testorg2'},
        ip: '192.168.1.3',
        datetime: '2024-01-13T09:15:00Z',
        performer: {name: 'user1', kind: 'user'},
      },
    ],
    next_page: null,
  };

  const superuserAggregateResp = {
    aggregated: [
      {kind: 'org_create', count: 5, datetime: '2024-01-15T00:00:00Z'},
      {kind: 'user_create', count: 12, datetime: '2024-01-15T00:00:00Z'},
      {kind: 'create_repo', count: 8, datetime: '2024-01-15T00:00:00Z'},
    ],
  };

  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  describe('Access Control', () => {
    it('should redirect non-superusers', () => {
      // Mock regular user (non-superuser)
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('user.json').then((user) => {
        user.super_user = false;
        cy.intercept('GET', '/api/v1/user/', user).as('getUser');
      });

      cy.visit('/usage-logs');
      cy.wait('@getConfig');
      cy.wait('@getUser');

      // Should redirect to repository page
      cy.url().should('include', '/repository');
    });

    it('should allow superusers access', () => {
      // Mock superuser
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.intercept('GET', '/api/v1/superuser/logs*', superuserLogsResp).as(
        'getSuperuserLogs',
      );
      cy.intercept(
        'GET',
        '/api/v1/superuser/aggregatelogs*',
        superuserAggregateResp,
      ).as('getSuperuserAggregate');

      cy.visit('/usage-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Should stay on usage logs page
      cy.url().should('include', '/usage-logs');
      cy.contains('Usage Logs').should('exist');
    });
  });

  describe('Superuser Usage Logs Display', () => {
    beforeEach(() => {
      // Setup superuser access
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.intercept('GET', '/api/v1/superuser/logs*', superuserLogsResp).as(
        'getSuperuserLogs',
      );
      cy.intercept(
        'GET',
        '/api/v1/superuser/aggregatelogs*',
        superuserAggregateResp,
      ).as('getSuperuserAggregate');
    });

    it('should display system-wide usage logs', () => {
      cy.visit('/usage-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Should show logs from multiple organizations
      cy.contains('Organization testorg1 created').should('exist');
      cy.contains('Create Repository testorg2/testrepo').should('exist');
      cy.contains('User newuser created').should('exist');
    });

    it('should have date range pickers', () => {
      cy.visit('/usage-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Should have From and To date pickers
      cy.contains('From:').should('exist');
      cy.contains('To:').should('exist');

      // Date pickers should be visible (PatternFly DatePicker uses aria-label)
      cy.get('input[aria-label="Date picker"]').should('have.length', 2);
    });

    it('should toggle chart visibility', () => {
      cy.visit('/usage-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Chart should be visible initially
      cy.get('.pf-v5-c-chart').should('exist');
      cy.contains('Hide Chart').should('exist');

      // Hide chart
      cy.contains('Hide Chart').click();
      cy.get('.pf-v5-c-chart').should('not.exist');
      cy.contains('Show Chart').should('exist');

      // Show chart again
      cy.contains('Show Chart').click();
      cy.get('.pf-v5-c-chart').should('exist');
      cy.contains('Hide Chart').should('exist');
    });

    it('should filter logs', () => {
      cy.visit('/usage-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Filter for create operations
      cy.get('[id="log-filter-input"]').type('create');

      // Should show create operations
      cy.contains('Organization testorg1 created').should('exist');
      cy.contains('Create Repository testorg2/testrepo').should('exist');
      cy.contains('User newuser created').should('exist');
    });
  });

  describe('Date Range Functionality', () => {
    beforeEach(() => {
      // Setup superuser access
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.intercept('GET', '/api/v1/superuser/logs*', superuserLogsResp).as(
        'getSuperuserLogs',
      );
      cy.intercept(
        'GET',
        '/api/v1/superuser/aggregatelogs*',
        superuserAggregateResp,
      ).as('getSuperuserAggregate');
    });

    it('should make API calls with date parameters', () => {
      cy.visit('/usage-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Wait for initial API calls with date parameters
      cy.wait('@getSuperuserLogs').then((interception) => {
        expect(interception.request.url).to.include('starttime=');
        expect(interception.request.url).to.include('endtime=');
      });

      cy.wait('@getSuperuserAggregate').then((interception) => {
        expect(interception.request.url).to.include('starttime=');
        expect(interception.request.url).to.include('endtime=');
      });
    });
  });

  describe('Fresh Login - OIDC Authentication', () => {
    beforeEach(() => {
      // Setup OIDC authentication
      cy.fixture('config.json').then((config) => {
        config.config.AUTHENTICATION_TYPE = 'OIDC';
        config.features.SUPERUSERS_FULL_ACCESS = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });
    });

    it('should redirect to signin with redirect_url when fresh login required for OIDC', () => {
      // Mock API to return fresh_login_required error
      cy.intercept('GET', '/api/v1/superuser/logs*', {
        statusCode: 401,
        body: {
          title: 'fresh_login_required',
          message: 'Fresh login required for this operation',
        },
      }).as('getLogsFreshLoginRequired');

      cy.visit('/usage-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getLogsFreshLoginRequired');

      // Should redirect to signin page with redirect_url parameter
      cy.url().should('include', '/signin');
      cy.url().should('include', 'redirect_url=');
      cy.url().should('include', 'usage-logs');

      // Should NOT show password verification modal
      cy.contains('Please Verify').should('not.exist');
      cy.get('input[type="password"][placeholder="Current Password"]').should(
        'not.exist',
      );
    });

    it('should not show password modal for OIDC authentication', () => {
      cy.intercept('GET', '/api/v1/superuser/logs*', {
        statusCode: 401,
        body: {
          error_type: 'fresh_login_required',
        },
      }).as('getFreshLoginRequired');

      cy.visit('/usage-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');
      cy.wait('@getFreshLoginRequired');

      // Password modal should NOT appear
      cy.contains('Please Verify').should('not.exist');
      cy.get('input[type="password"]#fresh-password').should('not.exist');

      // Should redirect instead
      cy.url().should('include', '/signin');
    });
  });

});
