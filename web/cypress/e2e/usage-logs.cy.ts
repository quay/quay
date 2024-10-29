describe('Usage Logs Export', () => {
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
    cy.visit('/repository/user1/hello-world');
    cy.contains('Logs').click();
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
    cy.visit('/repository/user1/hello-world');
    cy.contains('Logs').click();
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
    cy.visit('/organization/projectquay');
    cy.contains('Logs').click();
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
    cy.visit('/organization/projectquay');
    cy.contains('Logs').click();
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
    cy.visit('/organization/projectquay');
    cy.contains('Logs').click();

    cy.contains('Hide Chart').click();
    cy.get('[class=pf-v5-c-chart]').should('not.exist');

    cy.contains('Show Chart').click();
    cy.get('[class=pf-v5-c-chart]').should('be.visible');
  });

  it('empty chart', () => {
    cy.visit('/organization/projectquay');
    cy.contains('Logs').click();
    cy.contains('No data to display.').should('be.visible');
  });

  it('filter logs', () => {
    cy.intercept('GET', '/api/v1/organization/projectquay/logs?*', logsResp);

    cy.visit('/organization/projectquay');
    cy.contains('Logs').click();

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
