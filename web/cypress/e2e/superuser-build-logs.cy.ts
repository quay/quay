/// <reference types="cypress" />

describe('Superuser Build Logs', () => {
  const validBuildUuid = 'abc-123-valid-build-uuid';

  const mockBuildInfo = {
    id: '12345',
    uuid: validBuildUuid,
    status: 'complete',
    started: '2024-01-15T10:00:00Z',
    completed: '2024-01-15T10:30:00Z',
    repository: {
      namespace: 'testorg',
      name: 'testrepo',
    },
    phase: 'pushing',
  };

  const mockBuildLogs = {
    logs: [
      {
        message: 'Step 1: Building image...',
        timestamp: '2024-01-15T10:00:01Z',
        type: 'info',
      },
      {
        message: 'Step 2: Running tests...',
        timestamp: '2024-01-15T10:15:00Z',
        type: 'info',
      },
      {
        message: 'Step 3: Pushing to registry...',
        timestamp: '2024-01-15T10:25:00Z',
        type: 'info',
      },
    ],
  };

  const mockBuildNoLogs = {
    id: '67890',
    uuid: 'build-uuid-no-logs',
    status: 'failed',
    started: '2024-01-15T09:00:00Z',
    completed: '2024-01-15T09:05:00Z',
    logs: [],
  };

  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  describe('Load Valid Build Logs', () => {
    beforeEach(() => {
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        config.features.BUILD_SUPPORT = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });
    });

    it('should load and display build logs for valid UUID', () => {
      cy.intercept(
        'GET',
        `/api/v1/superuser/${validBuildUuid}/build`,
        mockBuildInfo,
      ).as('getBuildInfo');

      cy.intercept(
        'GET',
        `/api/v1/superuser/${validBuildUuid}/logs`,
        mockBuildLogs,
      ).as('getBuildLogs');

      cy.visit('/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Enter build UUID
      cy.get('[data-testid="build-uuid-input"]').type(validBuildUuid);

      // Click Get Logs button
      cy.get('[data-testid="load-build-button"]').click();

      // Wait for both API calls
      cy.wait('@getBuildInfo');
      cy.wait('@getBuildLogs');

      // Verify build information is displayed
      cy.contains('Build Information').should('exist');
      cy.contains(validBuildUuid).should('exist');
      cy.contains('complete').should('exist');
      cy.contains('testorg/testrepo').should('exist');
      cy.contains('pushing').should('exist');

      // Verify logs are displayed
      cy.contains('Build Logs').should('exist');
      cy.get('[data-testid="build-logs-display"]').should('exist');
      cy.contains('Step 1: Building image...').should('exist');
      cy.contains('Step 2: Running tests...').should('exist');
      cy.contains('Step 3: Pushing to registry...').should('exist');
    });

    it('should show timestamps by default', () => {
      cy.intercept(
        'GET',
        `/api/v1/superuser/${validBuildUuid}/build`,
        mockBuildInfo,
      ).as('getBuildInfo');

      cy.intercept(
        'GET',
        `/api/v1/superuser/${validBuildUuid}/logs`,
        mockBuildLogs,
      ).as('getBuildLogs');

      cy.visit('/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      cy.get('[data-testid="build-uuid-input"]').type(validBuildUuid);
      cy.get('[data-testid="load-build-button"]').click();
      cy.wait('@getBuildInfo');
      cy.wait('@getBuildLogs');

      // Timestamps checkbox should be checked
      cy.get('[data-testid="show-timestamps-checkbox"]').should('be.checked');

      // Timestamps should be visible in logs
      cy.get('[data-testid="build-logs-display"]').should(
        'contain',
        '[2024-01-15T10:00:01Z]',
      );
    });

    it('should show loading state while fetching', () => {
      cy.intercept('GET', `/api/v1/superuser/${validBuildUuid}/build`, {
        delay: 1000,
        body: mockBuildInfo,
      }).as('getBuildInfo');

      cy.intercept('GET', `/api/v1/superuser/${validBuildUuid}/logs`, {
        delay: 1000,
        body: mockBuildLogs,
      }).as('getBuildLogs');

      cy.visit('/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      cy.get('[data-testid="build-uuid-input"]').type(validBuildUuid);
      cy.get('[data-testid="load-build-button"]').click();

      // Should show loading state
      cy.contains('Loading...').should('exist');
      cy.contains('Loading build logs...').should('exist');

      cy.wait('@getBuildInfo');
      cy.wait('@getBuildLogs');

      // Loading state should disappear
      cy.contains('Loading...').should('not.exist');
    });
  });

  describe('Timestamps Toggle', () => {
    beforeEach(() => {
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        config.features.BUILD_SUPPORT = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.intercept(
        'GET',
        `/api/v1/superuser/${validBuildUuid}/build`,
        mockBuildInfo,
      ).as('getBuildInfo');

      cy.intercept(
        'GET',
        `/api/v1/superuser/${validBuildUuid}/logs`,
        mockBuildLogs,
      ).as('getBuildLogs');
    });

    it('should toggle timestamps on and off', () => {
      cy.visit('/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      cy.get('[data-testid="build-uuid-input"]').type(validBuildUuid);
      cy.get('[data-testid="load-build-button"]').click();
      cy.wait('@getBuildInfo');
      cy.wait('@getBuildLogs');

      // Timestamps should be visible initially
      cy.get('[data-testid="build-logs-display"]').should(
        'contain',
        '[2024-01-15T10:00:01Z]',
      );

      // Uncheck timestamps
      cy.get('[data-testid="show-timestamps-checkbox"]').uncheck();

      // Timestamps should be hidden
      cy.get('[data-testid="build-logs-display"]').should(
        'not.contain',
        '[2024-01-15T10:00:01Z]',
      );

      // Messages should still be visible
      cy.contains('Step 1: Building image...').should('exist');

      // Check timestamps again
      cy.get('[data-testid="show-timestamps-checkbox"]').check();

      // Timestamps should be visible again
      cy.get('[data-testid="build-logs-display"]').should(
        'contain',
        '[2024-01-15T10:00:01Z]',
      );
    });
  });

  describe('Empty Logs Handling', () => {
    beforeEach(() => {
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        config.features.BUILD_SUPPORT = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });
    });

    it('should show message when build has no logs', () => {
      cy.intercept(
        'GET',
        `/api/v1/superuser/build-uuid-no-logs/build`,
        mockBuildNoLogs,
      ).as('getBuildInfo');

      cy.intercept('GET', `/api/v1/superuser/build-uuid-no-logs/logs`, {
        logs: [],
      }).as('getBuildLogs');

      cy.visit('/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      cy.get('[data-testid="build-uuid-input"]').type('build-uuid-no-logs');
      cy.get('[data-testid="load-build-button"]').click();
      cy.wait('@getBuildInfo');
      cy.wait('@getBuildLogs');

      // Should show build info
      cy.contains('Build Information').should('exist');

      // Should show no logs message
      cy.contains('No logs available').should('exist');
      cy.contains('This build has no logs to display').should('exist');
    });

    it('should handle object log messages without crashing (PROJQUAY-9714)', () => {
      const buildWithObjectMessages = {
        id: '54321',
        uuid: 'object-messages-uuid',
        status: {phase: 'complete', code: 0},
        started: '2024-01-15T10:00:00Z',
      };

      const logsWithObjects = {
        logs: [
          {
            message: {error: 'Build failed', code: 500},
            timestamp: '10:00:01',
          },
          {message: 'String message', timestamp: '10:00:02'},
        ],
      };

      cy.intercept(
        'GET',
        '/api/v1/superuser/object-messages-uuid/build',
        buildWithObjectMessages,
      ).as('getBuildInfo');

      cy.intercept(
        'GET',
        '/api/v1/superuser/object-messages-uuid/logs',
        logsWithObjects,
      ).as('getBuildLogs');

      cy.visit('/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      cy.get('[data-testid="build-uuid-input"]').type('object-messages-uuid');
      cy.get('[data-testid="load-build-button"]').click();
      cy.wait('@getBuildInfo');
      cy.wait('@getBuildLogs');

      // Object messages should be JSON stringified
      cy.get('[data-testid="build-logs-display"]').should(
        'contain',
        '"error":"Build failed"',
      );

      // String messages should still work
      cy.get('[data-testid="build-logs-display"]').should(
        'contain',
        'String message',
      );

      // Object status should be JSON stringified
      cy.contains('"phase":"complete"').should('exist');

      // Critical: No React error boundary triggered
      cy.contains('This site is temporarily unavailable').should('not.exist');
    });
  });

});
