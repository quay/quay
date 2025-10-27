describe('Usage Logs', () => {
  const aggregateLogsResp = {
    aggregated: [
      {
        kind: 'create_application',
        count: 1,
        datetime: new Date(),
      },
      {
        kind: 'org_create',
        count: 1,
        datetime: new Date(),
      },
    ],
  };

  const logsResp = {
    start_time: 'Tue, 20 Feb 2024 17:33:43 -0000',
    end_time: 'Thu, 22 Feb 2024 17:33:43 -0000',
    logs: [
      {
        kind: 'change_repo_visibility',
        metadata: {
          repo: 'testrepo',
          namespace: 'projectquay',
          visibility: 'public',
        },
        ip: '192.168.228.1',
        datetime: 'Wed, 21 Feb 2024 17:33:07 -0000',
        performer: {
          kind: 'user',
          name: 'mkok',
          is_robot: false,
          avatar: {
            name: 'mkok',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
      {
        kind: 'change_repo_visibility',
        metadata: {
          repo: 'testrepo',
          namespace: 'projectquay',
          visibility: 'private',
        },
        ip: '192.168.228.1',
        datetime: 'Wed, 21 Feb 2024 17:33:04 -0000',
        performer: {
          kind: 'user',
          name: 'mkok',
          is_robot: false,
          avatar: {
            name: 'mkok',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
      {
        kind: 'create_repo',
        metadata: {
          repo: 'testrepo',
          namespace: 'projectquay',
        },
        ip: '192.168.228.1',
        datetime: 'Wed, 21 Feb 2024 17:32:57 -0000',
        performer: {
          kind: 'user',
          name: 'mkok',
          is_robot: false,
          avatar: {
            name: 'mkok',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
      {
        kind: 'org_create',
        metadata: {
          email: null,
          namespace: 'projectquay',
        },
        ip: '192.168.228.1',
        datetime: 'Wed, 21 Feb 2024 17:32:46 -0000',
        performer: {
          kind: 'user',
          name: 'mkok',
          is_robot: false,
          avatar: {
            name: 'mkok',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
      {
        kind: 'create_namespace_autoprune_policy',
        metadata: {
          method: 'number_of_tags',
          value: 20,
          tag_pattern: 'v1.*',
          tag_pattern_matches: true,
          namespace: 'org1',
        },
        ip: '192.168.228.1',
        datetime: 'Wed, 21 Feb 2024 17:32:46 -0000',
        performer: {
          kind: 'user',
          name: 'mkok',
          is_robot: false,
          avatar: {
            name: 'mkok',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
      {
        kind: 'create_repository_autoprune_policy',
        metadata: {
          method: 'number_of_tags',
          value: 20,
          tag_pattern: 'v1.*',
          tag_pattern_matches: true,
          namespace: 'org1',
          repo: 'test',
        },
        ip: '192.168.228.1',
        datetime: 'Wed, 21 Feb 2024 17:32:46 -0000',
        performer: {
          kind: 'user',
          name: 'mkok',
          is_robot: false,
          avatar: {
            name: 'mkok',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
    ],
    next_page:
      'gAAAAABl1jP3IfVFJNPZRJSB9YWXx0D8QXLXYmf8-0zZeqwV2dIM5gAsxdfaxGHUdS5FUsrm_8N1RIqm71EoagF1D9uwXh2agg==',
  };

  beforeEach(() => {
    cy.exec('npm run quay:seed');
    cy.request('GET', `${Cypress.env('REACT_QUAY_APP_API_URL')}/csrf_token`)
      .then((response) => response.body.csrf_token)
      .then((token) => {
        cy.loginByCSRF(token);
      });
  });

  it('exports repository logs', () => {
    cy.intercept(
      'POST',
      'api/v1/repository/user1/hello-world/exportlogs?starttime=$endtime=',
    ).as('exportRepositoryLogs');
    cy.visit('/repository/user1/hello-world?tab=logs'); // lowercase l for repository
    cy.contains('Export').click();
    cy.get('[id="export-logs-callback"]').type('example@example.com');
    cy.contains('Confirm').click();
    cy.contains('Logs exported with id').should('be.visible');
  });
  it('exports repository logs failure', () => {
    cy.intercept(
      'POST',
      'api/v1/repository/user1/hello-world/exportlogs?starttime=$endtime=',
    ).as('exportRepositoryLogs');
    cy.visit('/repository/user1/hello-world?tab=logs'); // lowercase l for repository
    cy.contains('Export').click();
    cy.get('[id="export-logs-callback"]').type('blahblah');
    cy.contains('Confirm').should('be.disabled');
  });

  it('shows usage logs graph', () => {
    cy.intercept(
      'GET',
      '/api/v1/organization/projectquay/aggregatelogs?*',
      aggregateLogsResp,
    );
    cy.visit('/organization/projectquay?tab=Logs'); // Capital L for organization
    cy.get('[class=pf-v5-c-chart]')
      .should('be.visible')
      .and((chart) => {
        expect(chart.height()).to.be.greaterThan(1);
      });
    cy.contains('Create Application').should('be.visible');
    cy.contains('Create organization').should('be.visible');
  });

  it('shows usage logs  table', () => {
    cy.intercept('GET', '/api/v1/organization/projectquay/logs?*', logsResp);
    cy.visit('/organization/projectquay?tab=Logs');
    cy.get('table')
      .contains(
        'td',
        'Change visibility for repository projectquay/testrepo to public',
      )
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains(
        'td',
        'Change visibility for repository projectquay/testrepo to private',
      )
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains('td', 'Create Repository projectquay/testrepo')
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains('td', 'Organization projectquay created')
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains(
        'td',
        'Created namespace autoprune policy: "number_of_tags:20, tagPattern:v1.*, tagPatternMatches:true" for namespace: org1',
      )
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains(
        'td',
        'Created repository autoprune policy: "number_of_tags:20, tagPattern:v1.*, tagPatternMatches:true" for repository: org1/test',
      )
      .scrollIntoView()
      .should('be.visible');
  });

  it('toggle chart', () => {
    cy.intercept(
      'GET',
      '/api/v1/organization/projectquay/aggregatelogs?*',
      aggregateLogsResp,
    );
    cy.visit('/organization/projectquay?tab=Logs');

    cy.contains('Hide Chart').click();
    cy.get('[class=pf-v5-c-chart]').should('not.exist');

    cy.contains('Show Chart').click();
    cy.get('[class=pf-v5-c-chart]').should('be.visible');
  });

  it('empty chart', () => {
    cy.visit('/organization/projectquay?tab=Logs');
    cy.contains('No data to display.').should('be.visible');
  });

  it('filter logs', () => {
    cy.intercept('GET', '/api/v1/organization/projectquay/logs?*', logsResp);

    cy.visit('/organization/projectquay?tab=Logs');

    cy.get('[id="log-filter-input"]').type('create');

    cy.get('table')
      .contains('td', 'Create Repository projectquay/testrepo')
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains('td', 'Organization projectquay created')
      .scrollIntoView()
      .should('be.visible');
    cy.get('table')
      .contains(
        'td',
        'Change visibility for repository projectquay/testrepo to private',
      )
      .should('not.exist');
  });
});

describe('Usage Logs - Superuser', () => {
  const superuserLogsResp = {
    start_time: 'Tue, 20 Feb 2024 17:33:43 -0000',
    end_time: 'Thu, 22 Feb 2024 17:33:43 -0000',
    logs: [
      {
        kind: 'account_change_plan',
        metadata: {
          namespace: 'user1',
        },
        ip: '172.31.0.1',
        datetime: 'Wed, 29 Oct 2025 14:01:14 -0000',
        performer: {
          kind: 'user',
          name: 'user1',
          is_robot: false,
          avatar: {
            name: 'user1',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
      {
        kind: 'account_change_plan',
        metadata: {
          namespace: 'user1',
        },
        ip: '172.31.0.1',
        datetime: 'Wed, 29 Oct 2025 13:55:45 -0000',
        performer: {
          kind: 'user',
          name: 'user1',
          is_robot: false,
          avatar: {
            name: 'user1',
            hash: '1b0c76c87a2c2cbc9c36339e055007194d9910eaa8124fda43527a8fb1f3c53a',
            color: '#a1d99b',
            kind: 'user',
          },
        },
      },
    ],
  };

  const superuserAggregateLogsResp = {
    aggregated: [
      {
        kind: 'account_change_plan',
        count: 4,
        datetime: new Date(),
      },
      {
        kind: 'account_change_plan',
        count: 1,
        datetime: new Date(),
      },
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

  it('displays superuser usage logs page', () => {
    cy.intercept(
      'GET',
      '/api/v1/superuser/aggregatelogs?*',
      superuserAggregateLogsResp,
    );
    cy.intercept('GET', '/api/v1/superuser/logs?*', superuserLogsResp);

    cy.visit('/usage-logs');

    // Verify page title
    cy.contains('h1', 'Usage Logs').should('be.visible');

    // Verify chart controls exist
    cy.contains('button', 'Hide Chart').should('be.visible');

    // Verify table exists
    cy.get('[role="grid"]').should('be.visible');

    // Verify namespace column exists (superuser only)
    cy.contains('th', 'Namespace').should('be.visible');
  });

  it('toggles chart visibility on superuser page', () => {
    cy.intercept(
      'GET',
      '/api/v1/superuser/aggregatelogs?*',
      superuserAggregateLogsResp,
    );
    cy.intercept('GET', '/api/v1/superuser/logs?*', superuserLogsResp);

    cy.visit('/usage-logs');

    // Verify chart is visible initially - use class selector to avoid matching header logo
    cy.get('[class=pf-v5-c-chart]').should('exist');

    // Hide chart
    cy.contains('button', 'Hide Chart').click();

    // Verify chart is hidden (not in DOM)
    cy.get('[class=pf-v5-c-chart]').should('not.exist');

    // Verify button text changed
    cy.contains('button', 'Show Chart').should('be.visible');

    // Show chart again
    cy.contains('button', 'Show Chart').click();

    // Verify chart is visible
    cy.get('[class=pf-v5-c-chart]').should('exist');
    cy.contains('button', 'Hide Chart').should('be.visible');
  });

  it('filters superuser logs', () => {
    cy.intercept(
      'GET',
      '/api/v1/superuser/aggregatelogs?*',
      superuserAggregateLogsResp,
    );
    cy.intercept('GET', '/api/v1/superuser/logs?*', superuserLogsResp);

    cy.visit('/usage-logs');

    // Type in filter
    cy.get('[placeholder="Filter logs"]').type('change');

    // Verify filter input has value
    cy.get('[placeholder="Filter logs"]').should('have.value', 'change');
  });

  it('displays table columns for superuser', () => {
    cy.intercept(
      'GET',
      '/api/v1/superuser/aggregatelogs?*',
      superuserAggregateLogsResp,
    );
    cy.intercept('GET', '/api/v1/superuser/logs?*', superuserLogsResp);

    cy.visit('/usage-logs');

    // Verify all expected column headers exist
    cy.contains('th', 'Date & Time').should('be.visible');
    cy.contains('th', 'Description').should('be.visible');
    cy.contains('th', 'Namespace').should('be.visible');
    cy.contains('th', 'Repository').should('be.visible');
    cy.contains('th', 'Performed by').should('be.visible');
    cy.contains('th', 'IP Address').should('be.visible');
  });
});
