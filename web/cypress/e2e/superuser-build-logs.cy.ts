/// <reference types="cypress" />

describe('Superuser Build Logs', () => {
  const validBuildUuid = 'abc-123-valid-build-uuid';
  const invalidBuildUuid = 'invalid-uuid-does-not-exist';

  const mockBuildSuccess = {
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

  describe('Access Control', () => {
    it('should show access denied for non-superusers', () => {
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        config.features.BUILD_SUPPORT = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('user.json').then((user) => {
        user.super_user = false;
        cy.intercept('GET', '/api/v1/user/', user).as('getUser');
      });

      cy.visit('/superuser/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getUser');

      cy.contains('Access Denied').should('exist');
      cy.contains('You must be a superuser to access build logs').should(
        'exist',
      );
    });

    it('should allow superusers access', () => {
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        config.features.BUILD_SUPPORT = true;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.visit('/superuser/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      cy.contains('Build Logs').should('exist');
      cy.get('[data-testid="build-uuid-input"]').should('exist');
    });
  });

  describe('Feature Flag - BUILD_SUPPORT', () => {
    it('should show warning when BUILD_SUPPORT is disabled', () => {
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        config.features.BUILD_SUPPORT = false;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.visit('/superuser/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      cy.contains('Build support not enabled').should('exist');
      cy.contains(
        'BUILD_SUPPORT is not enabled in the registry configuration',
      ).should('exist');
    });

    it('should hide Build Logs in sidebar when BUILD_SUPPORT is disabled', () => {
      cy.fixture('config.json').then((config) => {
        config.features.SUPERUSERS_FULL_ACCESS = true;
        config.features.BUILD_SUPPORT = false;
        cy.intercept('GET', '/config', config).as('getConfig');
      });

      cy.fixture('superuser.json').then((user) => {
        cy.intercept('GET', '/api/v1/user/', user).as('getSuperUser');
      });

      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Expand superuser section
      cy.contains('Superuser').click();

      // Build Logs should not be visible
      cy.get('[data-testid="build-logs-nav"]').should('not.exist');
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
        mockBuildSuccess,
      ).as('getBuildLogs');

      cy.visit('/superuser/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Enter build UUID
      cy.get('[data-testid="build-uuid-input"]').type(validBuildUuid);

      // Click Get Logs button
      cy.get('[data-testid="load-build-button"]').click();

      // Wait for API call
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
        mockBuildSuccess,
      ).as('getBuildLogs');

      cy.visit('/superuser/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      cy.get('[data-testid="build-uuid-input"]').type(validBuildUuid);
      cy.get('[data-testid="load-build-button"]').click();
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
        body: mockBuildSuccess,
      }).as('getBuildLogs');

      cy.visit('/superuser/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      cy.get('[data-testid="build-uuid-input"]').type(validBuildUuid);
      cy.get('[data-testid="load-build-button"]').click();

      // Should show loading state
      cy.contains('Loading...').should('exist');
      cy.contains('Loading build logs...').should('exist');

      cy.wait('@getBuildLogs');

      // Loading state should disappear
      cy.contains('Loading...').should('not.exist');
    });

    it('should disable button when input is empty', () => {
      cy.visit('/superuser/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Button should be disabled initially
      cy.get('[data-testid="load-build-button"]').should('be.disabled');

      // Type some text
      cy.get('[data-testid="build-uuid-input"]').type('some-uuid');

      // Button should be enabled
      cy.get('[data-testid="load-build-button"]').should('not.be.disabled');

      // Clear input
      cy.get('[data-testid="build-uuid-input"]').clear();

      // Button should be disabled again
      cy.get('[data-testid="load-build-button"]').should('be.disabled');
    });
  });

  describe('Load Invalid Build UUID', () => {
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

    it('should show error for invalid build UUID', () => {
      cy.intercept('GET', `/api/v1/superuser/${invalidBuildUuid}/build`, {
        statusCode: 404,
        body: {
          error: 'Build not found',
          message: 'No build exists with this UUID',
        },
      }).as('getBuildLogsError');

      cy.visit('/superuser/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      cy.get('[data-testid="build-uuid-input"]').type(invalidBuildUuid);
      cy.get('[data-testid="load-build-button"]').click();

      cy.wait('@getBuildLogsError');

      // Should show error alert
      cy.get('[data-testid="build-error-alert"]').should('exist');
      cy.contains('Cannot find or load build').should('exist');
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
        mockBuildSuccess,
      ).as('getBuildLogs');
    });

    it('should toggle timestamps on and off', () => {
      cy.visit('/superuser/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      cy.get('[data-testid="build-uuid-input"]').type(validBuildUuid);
      cy.get('[data-testid="load-build-button"]').click();
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
      ).as('getBuildNoLogs');

      cy.visit('/superuser/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      cy.get('[data-testid="build-uuid-input"]').type('build-uuid-no-logs');
      cy.get('[data-testid="load-build-button"]').click();
      cy.wait('@getBuildNoLogs');

      // Should show build info
      cy.contains('Build Information').should('exist');

      // Should show no logs message
      cy.contains('No logs available').should('exist');
      cy.contains('This build has no logs to display').should('exist');
    });
  });

  describe('Sidebar Navigation', () => {
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

    it('should navigate to Build Logs via sidebar', () => {
      cy.visit('/organization');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Expand superuser section
      cy.contains('Superuser').click();

      // Click Build Logs
      cy.get('[data-testid="build-logs-nav"]').click();

      // Should navigate to build logs page
      cy.url().should('include', '/superuser/build-logs');
      cy.contains('Build Logs').should('exist');
      cy.get('[data-testid="build-uuid-input"]').should('exist');
    });

    it('should auto-expand Superuser section when on Build Logs page', () => {
      cy.visit('/superuser/build-logs');
      cy.wait('@getConfig');
      cy.wait('@getSuperUser');

      // Superuser section should be expanded
      cy.get('[data-testid="build-logs-nav"]').should('be.visible');
    });
  });
});
